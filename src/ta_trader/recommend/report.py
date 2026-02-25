"""
ta_trader/recommend/report.py
종목 추천 보고서 터미널 포매터
"""

from __future__ import annotations

from ta_trader.recommend.models import (
    Grade, Rationale, Recommendation, RecommendationReport,
)
from ta_trader.utils.formatter import _wrap


def format_recommendation_report(report: RecommendationReport) -> str:
    """RecommendationReport를 구조화된 터미널 보고서로 변환"""
    bar  = "═" * 72
    thin = "─" * 72

    lines = [
        f"\n{bar}",
        f"  📋 종목 추천 보고서  |  {report.date}",
        f"{bar}",
    ]

    # ── 요약 테이블 ───────────────────────────────────────
    lines.append("")
    lines.append(f"  {'순위':>4s}  {'등급':7s}  {'종목':8s}  {'현재가':>10s}  {'점수':>7s}  {'전략':8s}  {'신뢰도':8s}  {'종목명':>10s}")
    lines.append(f"  {thin[2:]}")

    for rec in report.recommendations:
        dec = rec.decision
        conf_bar = "●" * round(rec.confidence * 5) + "○" * (5 - round(rec.confidence * 5))
        lines.append(
            f"  {rec.rank:>4d}  {rec.grade.emoji} {rec.grade.value:5s}  "
            f"{dec.ticker:8s}  {dec.current_price:>10,.2f}  {dec.composite_score:>+7.2f}  "
            f"{dec.strategy_type.value:8s}  {conf_bar:8s} {dec.name:>10s}"
        )

    # ── 매수 추천 종목 상세 ───────────────────────────────
    if report.buy_picks:
        lines.append(f"\n{bar}")
        lines.append(f"  🟢 매수 추천 종목 ({len(report.buy_picks)}건)")
        lines.append(f"{bar}")

        for rec in report.buy_picks:
            lines.extend(_format_single_recommendation(rec))

    # ── 관망 종목 ─────────────────────────────────────────
    if report.watch_list:
        lines.append(f"\n{bar}")
        lines.append(f"  ⚪ 관망 종목 ({len(report.watch_list)}건)")
        lines.append(f"{bar}")

        for rec in report.watch_list:
            lines.extend(_format_single_recommendation(rec, brief=True))

    # ── 비추천 종목 ───────────────────────────────────────
    if report.avoid_list:
        lines.append(f"\n{bar}")
        lines.append(f"  🔴 매수 비추천 종목 ({len(report.avoid_list)}건)")
        lines.append(f"{bar}")

        for rec in report.avoid_list:
            lines.extend(_format_single_recommendation(rec, brief=True))

    # ── 면책 조항 ─────────────────────────────────────────
    lines.append(f"\n{thin}")
    lines.append("  ⚠ 본 추천은 기술적 분석에 기반한 참고용이며 투자 조언이 아닙니다.")
    lines.append("  실제 투자 결정은 반드시 본인의 판단과 책임 하에 이루어져야 합니다.")
    lines.append(f"{bar}\n")

    return "\n".join(lines)


def _format_single_recommendation(
    rec: Recommendation, brief: bool = False,
) -> list[str]:
    """단일 종목 추천 결과 포매팅"""
    dec  = rec.decision
    thin = "─" * 68

    lines = [
        "",
        f"  ┌{'─'*66}┐",
        f"  │  {rec.grade.emoji}  #{rec.rank}  {dec.ticker} ({dec.name})  —  "
        f"{rec.grade.value}  (신뢰도 {rec.confidence:.0%})",
        f"  │  현재가: {dec.current_price:,.2f}  |  점수: {dec.composite_score:+.2f}  |  "
        f"체제: {dec.market_regime.value}  |  전략: {dec.strategy_type.value}",
        f"  └{'─'*66}┘",
    ]

    # 긍정 요인
    if rec.bullish_factors:
        lines.append(f"    ✅ 긍정 요인 ({len(rec.bullish_factors)}건)")
        for r in rec.bullish_factors:
            lines.append(f"       • [{r.category}] {r.summary}")
            if not brief:
                for line in _wrap(r.detail, width=60):
                    lines.append(f"         {line}")

    # 부정 요인
    if rec.bearish_factors:
        lines.append(f"    ❌ 부정 요인 ({len(rec.bearish_factors)}건)")
        for r in rec.bearish_factors:
            lines.append(f"       • [{r.category}] {r.summary}")
            if not brief:
                for line in _wrap(r.detail, width=60):
                    lines.append(f"         {line}")

    # 리스크 요인
    if rec.risk_factors:
        lines.append(f"    ⚠  리스크 ({len(rec.risk_factors)}건)")
        for r in rec.risk_factors:
            lines.append(f"       • [{r.category}] {r.summary}")
            if not brief:
                for line in _wrap(r.detail, width=60):
                    lines.append(f"         {line}")

    # 진입 조건 + 행동 제안
    if not brief:
        if rec.entry_condition:
            lines.append(f"    📌 진입 조건")
            for cond in rec.entry_condition.split(" | "):
                if cond.strip():
                    lines.append(f"       → {cond.strip()}")

        if rec.action_plan:
            lines.append(f"    🎯 행동 제안")
            for line in _wrap(rec.action_plan, width=60):
                lines.append(f"       {line}")

        # 손절/익절 정보
        if dec.risk:
            lines.append(
                f"    💰 손절: {dec.stop_loss:,.2f}  |  "
                f"익절: {dec.take_profit:,.2f}  |  "
                f"RR=1:{dec.risk_reward_ratio}"
            )

    return lines
