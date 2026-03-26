"""
Scheduler Service: 정기 분석 및 모니터링 작업 관리.
APScheduler를 사용하여 크론 기반 작업을 실행합니다.
"""

from typing import Any

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from ta_trader.config import get_settings
from ta_trader.services.agent_service import agent_service
from ta_trader.services.notification import AlertPayload, NotificationService
from ta_trader.utils.logger import get_logger

logger = get_logger(__name__)


class SchedulerService:
    """정기 분석/알림 스케줄러."""

    def __init__(self, notification_service: NotificationService) -> None:
        self._scheduler = AsyncIOScheduler()
        self._notification = notification_service
        self._settings = get_settings()

    def start(self) -> None:
        if not self._settings.scheduler_enabled:
            logger.info("Scheduler disabled by config")
            return

        # 장 전 스크리닝 (월-금 08:00)
        self._scheduler.add_job(
            self._pre_market_scan,
            CronTrigger.from_crontab(self._settings.market_pre_scan_cron),
            id="pre_market_scan",
            name="Pre-market screening",
            replace_existing=True,
        )

        # 장 후 포트폴리오 리뷰 (월-금 16:00)
        self._scheduler.add_job(
            self._post_market_review,
            CronTrigger.from_crontab(self._settings.market_post_review_cron),
            id="post_market_review",
            name="Post-market review",
            replace_existing=True,
        )

        self._scheduler.start()
        logger.info("Scheduler started with %d jobs", len(self._scheduler.get_jobs()))

    def stop(self) -> None:
        self._scheduler.shutdown(wait=False)
        logger.info("Scheduler stopped")

    async def _pre_market_scan(self) -> None:
        """장 전 시장 스크리닝 → 유망 종목 알림."""
        logger.info("Running pre-market scan...")
        try:
            results = await agent_service.run_screening(market="KRX", top_n=5)
            if not results:
                return

            # 상위 종목 알림
            summary = self._format_screening_results(results)
            await self._notification.send_alert(AlertPayload(
                ticker="MARKET",
                title="장 전 스크리닝 결과",
                message=summary,
                priority=3,
            ))
        except Exception as e:
            logger.error("Pre-market scan failed: %s", e)

    async def _post_market_review(self) -> None:
        """장 후 포트폴리오 리뷰 → 종합 리포트 알림."""
        logger.info("Running post-market review...")
        try:
            recommendations = await agent_service.get_recommendations()
            if not recommendations:
                return

            summary = self._format_recommendations(recommendations)
            await self._notification.send_alert(AlertPayload(
                ticker="PORTFOLIO",
                title="장 마감 포트폴리오 리뷰",
                message=summary,
                priority=2,
            ))
        except Exception as e:
            logger.error("Post-market review failed: %s", e)

    def _format_screening_results(self, results: list[Any]) -> str:
        lines = ["오늘의 유망 종목:"]
        for i, r in enumerate(results[:5], 1):
            ticker = getattr(r, "ticker", "N/A")
            score = getattr(r, "score", 0)
            lines.append(f"{i}. `{ticker}` — 점수: {score:.1f}")
        return "\n".join(lines)

    def _format_recommendations(self, results: list[Any]) -> str:
        lines = ["오늘의 추천:"]
        for i, r in enumerate(results[:5], 1):
            ticker = getattr(r, "ticker", "N/A")
            score = getattr(r, "score", 0)
            lines.append(f"{i}. `{ticker}` — 점수: {score:.1f}")
        return "\n".join(lines)
