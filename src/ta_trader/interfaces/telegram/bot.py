# ta_trader/interfaces/telegram/_bot.py
"""
Telegram Bot 인터페이스.
스마트폰에서 /analyze, /recommend, /screen 등의 명령으로 에이전트를 제어합니다.
"""

import asyncio
from typing import Any

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from ta_trader.config import get_settings
from ta_trader.core.orchestrator import AnalysisType
from ta_trader.services.agent_service import AgentService, JobStatus, agent_service
from ta_trader.services.notification import AlertPayload, NotificationService
from ta_trader.utils.logger import get_logger

logger = get_logger(__name__)


class TradingBot:
    """Stock TA Trader 텔레그램 봇."""

    def __init__(
        self,
        agent_svc: AgentService,
        notification_svc: NotificationService | None = None,
    ) -> None:
        self._agent = agent_svc
        self._notification = notification_svc
        self._settings = get_settings()

    def _is_authorized(self, user_id: int) -> bool:
        allowed = self._settings.telegram_allowed_user_ids
        return not allowed or user_id in allowed

    # ── Command Handlers ─────────────────────────────────

    async def cmd_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """시작 메시지 및 도움말."""
        if not self._is_authorized(update.effective_user.id):
            await update.message.reply_text("⛔ 인가되지 않은 사용자입니다.")
            return

        help_text = (
            "📈 *Stock TA Trader Bot*\n\n"
            "사용 가능한 명령어:\n"
            "───────────────\n"
            "/analyze `종목코드` — 스윙 분석\n"
            "/growth `종목코드` — 성장 모멘텀 분석\n"
            "/full `종목코드` — 종합 분석\n"
            "/screen — 시장 스크리닝\n"
            "/recommend — 추천 종목\n"
            "/watchlist — 관심 종목 목록\n"
            "/status `job_id` — 작업 상태 확인\n"
            "/help — 도움말"
        )
        await update.message.reply_text(help_text, parse_mode="Markdown")

    async def cmd_analyze(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """스윙 분석 실행."""
        await self._run_analysis(update, context, AnalysisType.SWING)

    async def cmd_growth(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """성장 모멘텀 분석 실행."""
        await self._run_analysis(update, context, AnalysisType.GROWTH_MOMENTUM)

    async def cmd_full(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """종합 분석 실행."""
        await self._run_analysis(update, context, AnalysisType.FULL)

    async def _run_analysis(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        analysis_type: AnalysisType,
    ) -> None:
        if not self._is_authorized(update.effective_user.id):
            return

        if not context.args:
            await update.message.reply_text(
                "사용법: `/analyze 005930` 또는 `/analyze AAPL`",
                parse_mode="Markdown",
            )
            return

        ticker = context.args[0].upper()
        await update.message.reply_text(
            f"🔄 `{ticker}` {analysis_type.value} 분석을 시작합니다...",
            parse_mode="Markdown",
        )

        try:
            job = await self._agent.submit_analysis(ticker, analysis_type)

            # 이미 캐시된 결과가 있으면 즉시 반환
            if job.status == JobStatus.COMPLETED:
                await self._send_result(update, job)
                return

            # 백그라운드 실행 중 → 폴링
            await update.message.reply_text(
                f"⏳ 작업 ID: `{job.job_id}`\n분석 중... 완료되면 알려드립니다.",
                parse_mode="Markdown",
            )
            await self._poll_and_notify(update, job.job_id)

        except Exception as e:
            logger.error("Analysis command failed: %s", e)
            await update.message.reply_text(f"❌ 오류 발생: {e}")

    async def _poll_and_notify(self, update: Update, job_id: str) -> None:
        """작업 완료를 폴링하고 결과를 전송."""
        for _ in range(60):  # 최대 5분 대기
            await asyncio.sleep(5)
            job = self._agent.get_job(job_id)
            if job is None:
                return
            if job.status == JobStatus.COMPLETED:
                await self._send_result(update, job)
                return
            if job.status == JobStatus.FAILED:
                await update.message.reply_text(
                    f"❌ 분석 실패: {job.error}",
                    parse_mode="Markdown",
                )
                return

        await update.message.reply_text("⏰ 분석 시간 초과. `/status` 명령으로 확인해주세요.")

    async def _send_result(self, update: Update, job: Any) -> None:
        """분석 결과를 포맷하여 전송."""
        result = job.result
        score = getattr(result, "score", 0) if result else 0
        recommendation = getattr(result, "recommendation", {}) if result else {}

        # 점수 기반 이모지
        if score >= 80:
            emoji = "🟢"
        elif score >= 60:
            emoji = "🟡"
        elif score >= 40:
            emoji = "🟠"
        else:
            emoji = "🔴"

        text = (
            f"{emoji} *{job.ticker} 분석 결과*\n"
            f"───────────────\n"
            f"분석 유형: `{job.analysis_type.value}`\n"
            f"종합 점수: *{score:.1f}점*\n"
        )

        if recommendation:
            if action := recommendation.get("action"):
                text += f"추천 액션: `{action}`\n"
            if reason := recommendation.get("reason"):
                text += f"사유: {reason}\n"
            if entry := recommendation.get("entry_price"):
                text += f"진입가: {entry:,.0f}원\n"
            if stop_loss := recommendation.get("stop_loss"):
                text += f"손절가: {stop_loss:,.0f}원\n"
            if target := recommendation.get("target_price"):
                text += f"목표가: {target:,.0f}원\n"

        # 상세 보기 인라인 버튼
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton(
                    "📊 상세 분석",
                    callback_data=f"detail:{job.job_id}",
                ),
                InlineKeyboardButton(
                    "🔄 재분석",
                    callback_data=f"rerun:{job.ticker}:{job.analysis_type.value}",
                ),
            ]
        ])

        await update.message.reply_text(
            text, parse_mode="Markdown", reply_markup=keyboard
        )

    async def cmd_screen(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """시장 스크리닝."""
        if not self._is_authorized(update.effective_user.id):
            return

        market = context.args[0].upper() if context.args else "KRX"
        await update.message.reply_text(f"🔍 {market} 시장 스크리닝 중...")

        try:
            results = await self._agent.run_screening(market=market, top_n=10)
            if not results:
                await update.message.reply_text("스크리닝 결과가 없습니다.")
                return

            lines = [f"📋 *{market} 스크리닝 결과*\n───────────────"]
            for i, r in enumerate(results[:10], 1):
                ticker = getattr(r, "ticker", "N/A")
                score = getattr(r, "score", 0)
                lines.append(f"{i}. `{ticker}` — 점수: {score:.1f}")

            await update.message.reply_text(
                "\n".join(lines), parse_mode="Markdown"
            )
        except Exception as e:
            await update.message.reply_text(f"❌ 스크리닝 실패: {e}")

    async def cmd_recommend(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """추천 종목 조회."""
        if not self._is_authorized(update.effective_user.id):
            return

        await update.message.reply_text("💡 추천 종목 조회 중...")

        try:
            results = await self._agent.get_recommendations()
            if not results:
                await update.message.reply_text("현재 추천 종목이 없습니다.")
                return

            lines = ["💡 *추천 종목*\n───────────────"]
            for i, r in enumerate(results[:10], 1):
                ticker = getattr(r, "ticker", "N/A")
                score = getattr(r, "score", 0)
                lines.append(f"{i}. `{ticker}` — 점수: {score:.1f}")

            await update.message.reply_text(
                "\n".join(lines), parse_mode="Markdown"
            )
        except Exception as e:
            await update.message.reply_text(f"❌ 추천 조회 실패: {e}")

    async def cmd_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """작업 상태 확인."""
        if not self._is_authorized(update.effective_user.id):
            return

        if not context.args:
            await update.message.reply_text("사용법: `/status <job_id>`", parse_mode="Markdown")
            return

        job_id = context.args[0]
        job = self._agent.get_job(job_id)
        if job is None:
            await update.message.reply_text(f"작업 `{job_id}`을(를) 찾을 수 없습니다.")
            return

        status_emoji = {
            JobStatus.PENDING: "⏳",
            JobStatus.RUNNING: "🔄",
            JobStatus.COMPLETED: "✅",
            JobStatus.FAILED: "❌",
        }
        emoji = status_emoji.get(job.status, "❓")
        await update.message.reply_text(
            f"{emoji} 작업 `{job.job_id}`\n"
            f"종목: `{job.ticker}`\n"
            f"상태: {job.status.value}\n"
            f"생성: {job.created_at:%Y-%m-%d %H:%M}",
            parse_mode="Markdown",
        )

    # ── Callback Query Handler ───────────────────────────

    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """인라인 버튼 콜백 처리."""
        query = update.callback_query
        await query.answer()

        data = query.data
        if data.startswith("detail:"):
            job_id = data.split(":")[1]
            job = self._agent.get_job(job_id)
            if job and job.result:
                import json
                detail = json.dumps(
                    getattr(job.result, "agents_results", {}),
                    default=str,
                    ensure_ascii=False,
                    indent=2,
                )
                # 텔레그램 메시지 길이 제한 대응
                if len(detail) > 4000:
                    detail = detail[:4000] + "\n... (truncated)"
                await query.edit_message_text(
                    f"```json\n{detail}\n```",
                    parse_mode="Markdown",
                )
            else:
                await query.edit_message_text("상세 데이터를 찾을 수 없습니다.")

        elif data.startswith("rerun:"):
            parts = data.split(":")
            ticker = parts[1]
            analysis_type = AnalysisType(parts[2])
            await query.edit_message_text(f"🔄 `{ticker}` 재분석을 시작합니다...", parse_mode="Markdown")
            job = await self._agent.submit_analysis(ticker, analysis_type)
            await query.edit_message_text(
                f"⏳ 재분석 작업 ID: `{job.job_id}`",
                parse_mode="Markdown",
            )


def create_telegram_bot(
    agent_svc: AgentService | None = None,
    notification_svc: NotificationService | None = None,
) -> Application:
    """텔레그램 봇 Application 생성."""
    settings = get_settings()
    token = settings.telegram_bot_token.get_secret_value()
    if not token:
        raise ValueError("TELEGRAM_BOT_TOKEN is not set")

    bot = TradingBot(
        agent_svc=agent_svc or agent_service,
        notification_svc=notification_svc,
    )

    app = Application.builder().token(token).build()

    # 명령어 등록
    app.add_handler(CommandHandler("start", bot.cmd_start))
    app.add_handler(CommandHandler("help", bot.cmd_start))
    app.add_handler(CommandHandler("analyze", bot.cmd_analyze))
    app.add_handler(CommandHandler("growth", bot.cmd_growth))
    app.add_handler(CommandHandler("full", bot.cmd_full))
    app.add_handler(CommandHandler("screen", bot.cmd_screen))
    app.add_handler(CommandHandler("recommend", bot.cmd_recommend))
    app.add_handler(CommandHandler("status", bot.cmd_status))
    app.add_handler(CallbackQueryHandler(bot.handle_callback))

    return app
