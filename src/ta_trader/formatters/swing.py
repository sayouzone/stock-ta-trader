"""
ta_trader/formatters/swing.py
스윙 트레이딩 6단계 분석 결과 포매터
"""

from __future__ import annotations

from ta_trader.models.swing import (
    SwingAnalysisResult, SwingSignal,
    MarketEnvironment, ScreeningGrade,
)


# ── 신호 이모지 ───────────────────────────────────────────

_SIGNAL_EMOJI = {
    SwingSignal.STRONG_ENTRY: "🟢🟢",
    SwingSignal.ENTRY: "🟢",
    SwingSignal.HOLD: "🟡",
    SwingSignal.PARTIAL_EXIT: "🟠",
    SwingSignal.EXIT: "🔴",
    SwingSignal.STRONG_EXIT: "🔴🔴",
}

_ENV_EMOJI = {
    MarketEnvironment.BULLISH_TREND: "📈",
    MarketEnvironment.BULLISH_WEAK: "📊",
    MarketEnvironment.BEARISH_TREND: "📉",
    MarketEnvironment.SIDEWAYS: "➡️",
    MarketEnvironment.HIGH_VOLATILITY: "⚡",
}

_GRADE_EMOJI = {
    ScreeningGrade.A_PLUS: "⭐",
    ScreeningGrade.A: "✅",
    ScreeningGrade.B: "🔵",
    ScreeningGrade.C: "⚪",
    ScreeningGrade.F: "❌",
}


# ── 포매팅 함수 ───────────────────────────────────────────

def format_swing_result(result: SwingAnalysisResult) -> str:
    """스윙 트레이딩 6단계 분석 결과를 터미널용 문자열로 변환"""
    W = 70
    lines: list[str] = []

    # 헤더
    lines.append("━" * W)
    lines.append(f"  🔄 스윙 트레이딩 분석: {result.name} ({result.ticker})")
    lines.append(f"  📅 {result.date}  |  💰 현재가: {result.current_price:,.0f}")
    lines.append("━" * W)

    # ── 1단계: 시장 환경 ──
    env = result.market_env
    e_emoji = _ENV_EMOJI.get(env.environment, "")
    lines.append(f"\n{'─'*W}")
    lines.append(f"  📊 1단계: 시장 환경 판단  [{env.score:.0f}/100점]")
    lines.append(f"{'─'*W}")
    lines.append(f"  {e_emoji} 환경: {env.environment.value}")
    lines.append(f"     {env.detail}")

    fav = "✅ 유리" if env.is_favorable else "⚠️  불리"
    lines.append(f"  → 스윙 매매 환경: {fav}")

    # ── 2단계: 종목 스크리닝 ──
    scr = result.screening
    g_emoji = _GRADE_EMOJI.get(scr.grade, "")
    lines.append(f"\n{'─'*W}")
    lines.append(f"  🔍 2단계: 종목 스크리닝  [{scr.score:.0f}/100점]")
    lines.append(f"{'─'*W}")
    lines.append(f"  {g_emoji} 등급: {scr.grade.value}  ({scr.checks_passed}/{scr.checks_total} 통과)")
    lines.append(f"     {scr.detail}")

    # ── 3단계: 진입 타이밍 ──
    ent = result.entry
    lines.append(f"\n{'─'*W}")
    lines.append(f"  🎯 3단계: 진입 타이밍  [{ent.score:.0f}/100점]")
    lines.append(f"{'─'*W}")
    for sig in ent.signals:
        mark = "✅" if sig.triggered else "  "
        score_str = f"+{sig.score:.0f}" if sig.score > 0 else f"{sig.score:.0f}"
        lines.append(f"  {mark} {sig.name:<18} {score_str:>5}점  {sig.description}")
    lines.append(f"  → 진입 신호: {_SIGNAL_EMOJI.get(ent.signal, '')} {ent.signal.value} ({ent.detail})")

    # ── 4단계: 포지션 사이징 ──
    pos = result.position
    lines.append(f"\n{'─'*W}")
    lines.append(f"  💼 4단계: 포지션 사이징  [{pos.score:.0f}/100점]")
    lines.append(f"{'─'*W}")
    lines.append(f"  진입가:   {pos.entry_price:>12,.0f}")
    lines.append(f"  손절가:   {pos.stop_loss:>12,.0f}  (ATR×{POSITION_ATR_SL_MULT})")
    lines.append(f"  익절가:   {pos.take_profit:>12,.0f}  (ATR×{POSITION_ATR_TP_MULT})")
    lines.append(f"  R배수:    1:{pos.risk_reward_ratio}  {'✅ 적합' if pos.is_acceptable else '⚠️  부적합'}")
    lines.append(f"  매수수량: {pos.position_size:>8,}주  ({pos.position_value:,.0f}원)")
    lines.append(f"  비중:     {pos.portfolio_pct:>8.1f}%  (자본금: {pos.capital:,.0f}원)")
    lines.append(f"  최대손실: {pos.max_loss:>12,.0f}원  (자본의 {pos.max_loss/pos.capital*100:.1f}%)")
    if pos.fibo_target_161 > 0:
        lines.append(f"  피보목표: 161.8%={pos.fibo_target_161:,.0f}  261.8%={pos.fibo_target_261:,.0f}")

    # ── 5단계: 익절/청산 전략 ──
    ext = result.exit_strategy
    lines.append(f"\n{'─'*W}")
    lines.append(f"  🚪 5단계: 익절/청산 전략  [청산압력 {ext.score:.0f}/100]")
    lines.append(f"{'─'*W}")
    lines.append(f"  트레일링 스톱:  {ext.trailing_stop:>10,.0f}")
    lines.append(f"  1차 부분익절:   {ext.partial_exit_price:>10,.0f}  (50% 매도)")
    lines.append(f"  전량 청산가:    {ext.full_exit_price:>10,.0f}")
    lines.append(f"     {ext.detail}")
    if ext.should_partial_exit:
        lines.append(f"  ⚠️  현재 부분 익절 권장")
    if ext.should_full_exit:
        lines.append(f"  🚨 현재 전량 청산 권장")

    # ── 종합 ──
    lines.append(f"\n{'━'*W}")
    sig_emoji = _SIGNAL_EMOJI.get(result.overall_signal, "")
    lines.append(f"  {sig_emoji} 종합 신호: {result.overall_signal.value}  ({result.overall_score:.1f}/100)")
    lines.append(f"{'━'*W}")
    lines.append(f"  {result.summary}")
    if result.is_actionable:
        lines.append(f"  ✅ 매수 실행 가능 조건 충족")
    else:
        lines.append(f"  ⏸️  매수 실행 조건 미충족 - 관망 권장")
    lines.append("━" * W)

    return "\n".join(lines)


# 상수 참조 (detail 표시용)
from ta_trader.swing.constants import (
    POSITION_ATR_SL_MULTIPLIER as POSITION_ATR_SL_MULT,
    POSITION_ATR_TP_MULTIPLIER as POSITION_ATR_TP_MULT,
)


def format_swing_report(results: list[SwingAnalysisResult]) -> str:
    """복수 종목 스윙 분석 요약 보고서"""
    if not results:
        return "분석 결과 없음"

    W = 90
    lines: list[str] = []
    lines.append("━" * W)
    lines.append(f"  🔄 스윙 트레이딩 스크리닝 보고서  ({len(results)}종목)")
    lines.append("━" * W)

    # 요약 테이블 헤더
    header = (
        f"{'종목':<12} {'가격':>10} {'시장':^8} {'등급':^4} "
        f"{'진입':^8} {'점수':>5} {'손절':>10} {'익절':>10} "
        f"{'RR':>5} {'수량':>6} {'종합':^8} {'점수':>5}"
    )
    lines.append(header)
    lines.append("─" * W)

    # 점수 내림차순 정렬
    sorted_results = sorted(results, key=lambda r: r.overall_score, reverse=True)

    for r in sorted_results:
        sig_emoji = _SIGNAL_EMOJI.get(r.overall_signal, "")
        ent_emoji = _SIGNAL_EMOJI.get(r.entry.signal, "")
        name = r.name[:10] if len(r.name) > 10 else r.name
        line = (
            f"{name:<12} {r.current_price:>10,.0f} "
            f"{r.market_env.environment.value:^8} {r.screening.grade.value:^4} "
            f"{ent_emoji}{r.entry.signal.value:^6} {r.entry.score:>5.0f} "
            f"{r.position.stop_loss:>10,.0f} {r.position.take_profit:>10,.0f} "
            f"{r.position.risk_reward_ratio:>5.1f} {r.position.position_size:>6,} "
            f"{sig_emoji}{r.overall_signal.value:^6} {r.overall_score:>5.1f}"
        )
        lines.append(line)

    lines.append("─" * W)

    # 매수 가능 종목 하이라이트
    actionable = [r for r in sorted_results if r.is_actionable]
    if actionable:
        lines.append(f"\n  ✅ 매수 실행 가능 종목: {len(actionable)}개")
        for r in actionable:
            lines.append(f"     → {r.name} ({r.ticker}) 점수={r.overall_score:.1f}")
    else:
        lines.append(f"\n  ⏸️  현재 매수 실행 가능 종목 없음")

    lines.append("━" * W)
    return "\n".join(lines)
