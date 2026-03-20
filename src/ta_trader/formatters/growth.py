"""
ta_trader/growth/formatter.py
GrowthAnalysisResult 터미널 출력 포매터

recommend/report.py와 동일한 레이아웃:
  1. 요약 테이블 (순위·등급·종목·현재가·점수·스테이지 점수)
  2. 매수 추천 종목 상세 (적극매수 / 매수 / 조건부매수)
  3. 관망 종목 (간략)
  4. 부적합 종목 (간략)
  5. 면책 조항
"""

from __future__ import annotations

from ta_trader.models.base import StageResult, StageStatus
from ta_trader.models.growth import (
    GrowthGrade, GrowthAnalysisResult, 
)
from ta_trader.utils.formatter import _wrap


# ── 복수 종목 보고서 (growth-screen용) ────────────────────

def format_growth_report(results: list[GrowthAnalysisResult]) -> str:
    """복수 GrowthAnalysisResult recommend 형식 보고서로 변환"""
    if not results:
        return "분석 결과가 없습니다."

    bar  = "═" * 72
    thin = "─" * 72
    report_date = results[0].date if results else ""

    lines = [
        f"\n{bar}",
        f"  🚀 성장 투자 (Growth Investing) 종목 추천 보고서  |  {report_date}",
        f"{bar}",
    ]

    # ── 요약 테이블 ──────────────────────────────────────
    lines.append("")
    lines.append(
        f"  {'순위':>4s}  {'등급':7s}  {'종목':8s}  {'현재가':>10s}  "
        f"{'점수':>6s}  {'S1':>5s} {'S3':>5s} {'S4':>5s} {'S5':>5s} {'S6':>5s}  {'종목명':>10s}"
    )
    lines.append(f"  {thin[2:]}")

    for rank, r in enumerate(results, 1):
        s_cols = ""
        for sn in [1, 3, 4, 5, 6]:
            s = r.get_stage(sn)
            if s:
                s_cols += f" {s.score:>2.0f}/{s.max_score:<2.0f}"
            else:
                s_cols += "   - "

        lines.append(
            f"  {rank:>4d}  {r.grade.emoji} {r.grade.value:5s}  "
            f"{r.ticker:8s}  {r.current_price:>10,.2f}  "
            f"{r.total_score:>5.1f} {s_cols:24s} {r.name:>10s}"
        )

    # ── 등급별 분류 ──────────────────────────────────────
    buy_picks = [r for r in results if r.grade in (
        GrowthGrade.STRONG_BUY, GrowthGrade.BUY, GrowthGrade.CONDITIONAL,
    )]
    watch_list = [r for r in results if r.grade == GrowthGrade.WATCH]
    avoid_list = [r for r in results if r.grade == GrowthGrade.UNFIT]

    # ── 매수 추천 종목 상세 ──────────────────────────────
    if buy_picks:
        lines.append(f"\n{bar}")
        lines.append(f"  🟢 매수 추천 종목 ({len(buy_picks)}건)")
        lines.append(f"{bar}")
        for rank, r in enumerate(buy_picks, 1):
            lines.extend(_format_single_growth(r, rank, brief=False))

    # ── 관망 종목 ────────────────────────────────────────
    if watch_list:
        lines.append(f"\n{bar}")
        lines.append(f"  ⚪ 관망 종목 ({len(watch_list)}건)")
        lines.append(f"{bar}")
        for rank, r in enumerate(watch_list, len(buy_picks) + 1):
            lines.extend(_format_single_growth(r, rank, brief=True))

    # ── 부적합 종목 ──────────────────────────────────────
    if avoid_list:
        lines.append(f"\n{bar}")
        lines.append(f"  🔴 부적합 종목 ({len(avoid_list)}건)")
        lines.append(f"{bar}")
        for rank, r in enumerate(avoid_list, len(buy_picks) + len(watch_list) + 1):
            lines.extend(_format_single_growth(r, rank, brief=True))

    # ── 면책 조항 ────────────────────────────────────────
    lines.append(f"\n{thin}")
    lines.append("  ⚠ 본 분석은 기술적·펀더멘털 정량 지표에 기반한 참고용이며 투자 조언이 아닙니다.")
    lines.append("  촉매(2단계)는 수동 확인이 필요하며, 실제 투자는 본인의 판단과 책임 하에 이루어져야 합니다.")
    lines.append(f"{bar}\n")

    return "\n".join(lines)


# ── 단일 종목 상세 보고서 (growth 명령용) ─────────────────

def format_growth_result(result: GrowthAnalysisResult) -> str:
    """단일 GrowthAnalysisResult를 recommend 형식 상세 보고서로 변환"""
    bar  = "═" * 72

    lines = [
        f"\n{bar}",
        f"  🚀 Growth 분석 보고서  |  {result.date}",
        f"{bar}",
    ]

    # 요약 테이블 (1종목)
    lines.append("")
    lines.append(
        f"  {'등급':7s}  {'종목':8s}  {'현재가':>10s}  "
        f"{'점수':>6s}  {'S1':>5s} {'S3':>5s} {'S4':>5s} {'S5':>5s} {'S6':>5s}"
    )
    lines.append(f"  {'─' * 70}")

    s_cols = ""
    for sn in [1, 3, 4, 5, 6]:
        s = result.get_stage(sn)
        if s:
            s_cols += f" {s.score:>2.0f}/{s.max_score:<2.0f}"
        else:
            s_cols += "   - "

    lines.append(
        f"  {result.grade.emoji} {result.grade.value:5s}  "
        f"{result.ticker:8s}  {result.current_price:>10,.2f}  "
        f"{result.total_score:>5.1f} {s_cols}"
    )

    # 상세 (brief=False)
    lines.extend(_format_single_growth(result, rank=1, brief=False))

    # 면책 조항
    lines.append(f"\n{'─' * 72}")
    lines.append("  ⚠ 본 분석은 기술적·펀더멘털 정량 지표에 기반한 참고용이며 투자 조언이 아닙니다.")
    lines.append("  촉매(2단계)는 수동 확인이 필요하며, 실제 투자는 본인의 판단과 책임 하에 이루어져야 합니다.")
    lines.append(f"{bar}\n")

    return "\n".join(lines)


# ── 단일 종목 내부 포매터 ────────────────────────────────

def _format_single_growth(
    r: GrowthAnalysisResult, rank: int, brief: bool = False,
) -> list[str]:
    """단일 종목 결과를 recommend/_format_single_recommendation 스타일로 포매팅"""
    lines = [
        "",
        f"  ┌{'─' * 66}┐",
        f"  │  {r.grade.emoji}  #{rank}  {r.ticker} ({r.name})  —  "
        f"{r.grade.stars} {r.grade.value}  ({r.total_score:.1f}/100점)",
        f"  │  현재가: {r.current_price:,.2f}",
        f"  └{'─' * 66}┘",
    ]

    # 가격 위치 정보
    pos_parts = []
    if r.high_52w:
        pct = (r.high_52w - r.current_price) / r.high_52w
        pos_parts.append(f"52주 고가: {r.high_52w:,.2f}(-{pct:.1%})")
    if r.low_52w:
        pct = (r.current_price - r.low_52w) / r.low_52w
        pos_parts.append(f"52주 저가: {r.low_52w:,.2f}(+{pct:.1%})")
    if r.sma_200:
        pos_parts.append(f"SMA200: {r.sma_200:,.2f}")
    if pos_parts:
        lines.append(f"    📍 {' | '.join(pos_parts)}")

    # ── 6단계를 긍정/부정/리스크로 분류 ──────────────────
    bullish, bearish, risk_items = _classify_stage_checks(r)

    # 긍정 요인
    if bullish:
        lines.append(f"    ✅ 긍정 요인 ({len(bullish)}건)")
        for cat, summary, detail in bullish:
            lines.append(f"       • [{cat}] {summary}")
            if not brief:
                for line in _wrap(detail, width=60):
                    lines.append(f"         {line}")

    # 부정 요인
    if bearish:
        lines.append(f"    ❌ 부정 요인 ({len(bearish)}건)")
        for cat, summary, detail in bearish:
            lines.append(f"       • [{cat}] {summary}")
            if not brief:
                for line in _wrap(detail, width=60):
                    lines.append(f"         {line}")

    # 리스크/참고 요인
    if risk_items:
        lines.append(f"    ⚠  리스크 ({len(risk_items)}건)")
        for cat, summary, detail in risk_items:
            lines.append(f"       • [{cat}] {summary}")
            if not brief:
                for line in _wrap(detail, width=60):
                    lines.append(f"         {line}")

    if not brief:
        # 펀더멘털 요약
        if r.fundamentals and r.fundamentals.has_data:
            f = r.fundamentals
            fund_parts = []
            if f.sector:
                fund_parts.append(f"{f.sector}>{f.industry}")
            if f.eps_growth is not None:
                fund_parts.append(f"EPS성장 {f.eps_growth:.1%}")
            if f.revenue_growth is not None:
                fund_parts.append(f"매출성장 {f.revenue_growth:.1%}")
            if f.profit_margin is not None:
                fund_parts.append(f"이익률 {f.profit_margin:.1%}")
            if f.market_cap:
                fund_parts.append(f"시총 ${f.market_cap/1e9:.1f}B")
            if f.forward_pe:
                fund_parts.append(f"FwdPE {f.forward_pe:.1f}")
            if f.peg_ratio:
                fund_parts.append(f"PEG {f.peg_ratio:.2f}")
            if fund_parts:
                lines.append(f"    📊 펀더멘털: {' | '.join(fund_parts)}")

        # 촉매 (2단계) — 수동 확인 안내
        s2 = r.get_stage(2)
        if s2:
            for c in s2.checks:
                if c.description:
                    lines.append(f"    👤 촉매(수동): {c.description}")

        # 스테이지 판별 (3단계)
        s3 = r.get_stage(3)
        if s3 and s3.description:
            lines.append(f"    📌 스테이지: {s3.description}")

        # 손절/익절 정보
        if r.stop_loss and r.take_profit:
            lines.append(
                f"    💰 손절: {r.stop_loss:,.2f}  |  "
                f"익절: {r.take_profit:,.2f}  |  "
                f"RR=1:{r.risk_reward}"
            )

        # 행동 제안
        if r.action:
            lines.append(f"    🎯 행동 제안")
            for line in _wrap(r.action, width=60):
                lines.append(f"       {line}")

    return lines


# ── 6단계 체크 항목을 긍정/부정/리스크로 분류 ────────────

_STAGE_CATEGORY = {
    1: "이익",
    2: "촉매",
    3: "스테이지",
    4: "기술적",
    5: "리스크",
    6: "건강도",
}


def _classify_stage_checks(
    r: GrowthAnalysisResult,
) -> tuple[
    list[tuple[str, str, str]],
    list[tuple[str, str, str]],
    list[tuple[str, str, str]],
]:
    """
    6단계의 CheckItem들을 긍정/부정/리스크 3개 리스트로 분류.
    각 항목: (카테고리, 요약, 상세설명)
    """
    bullish: list[tuple[str, str, str]] = []
    bearish: list[tuple[str, str, str]] = []
    risks:   list[tuple[str, str, str]] = []

    for stage in r.stages:
        # 2단계(촉매)는 별도 표시
        if stage.stage_num == 2:
            continue

        cat = _STAGE_CATEGORY.get(stage.stage_num, f"S{stage.stage_num}")

        for check in stage.checks:
            item = (cat, check.name, check.description)

            if check.passed:
                # 5단계(리스크) 항목은 통과해도 리스크 카테고리에 표시
                if stage.stage_num == 5:
                    risks.append(item)
                else:
                    bullish.append(item)
            else:
                if "데이터 없음" in check.description or "부족" in check.description:
                    risks.append(item)
                else:
                    bearish.append(item)

    return bullish, bearish, risks
