"""
ta_trader/formatter/agent.py
에이전트 파이프라인 결과 터미널 포매터
"""

from __future__ import annotations

from ta_trader.models import OrderSide
from ta_trader.models.agent import (
    ExecutionResult, OrderStatus,
    PipelineResult, RiskApproval, TradeSignal, VetoReason,
)
from ta_trader.utils.formatter import _confidence_bar, _wrap


def format_pipeline_result(result: PipelineResult) -> str:
    """PipelineResult를 구조화된 터미널 출력으로 변환"""
    bar = "═" * 72
    thin = "─" * 72

    lines = [f"\n{bar}"]

    # ── 헤더 ─────────────────────────────────────────────
    ts = result.trade_signal
    md = result.market_data

    if ts:
        lines.append(
            f"  📊  {ts.ticker} ({ts.name})  |  {ts.date}  |  "
            f"스타일: {ts.trading_style.value}"
        )
        lines.append(bar)
    else:
        lines.append(f"  📊  {result.ticker}  |  {result.date}")
        lines.append(bar)

    # ── Stage 1: Data Agent 결과 ─────────────────────────
    if md:
        lines.append(f"\n  🔍 [Stage 1] 데이터 분석 에이전트")
        lines.append(f"  {thin[2:]}")
        lines.append(f"  현재가       : {md.current_price:,.2f}")
        lines.append(f"  데이터 행수  : {md.data_rows:,}")
        lines.append(f"  데이터 품질  : {md.data_quality_score:.1%}")

        if md.regime_context:
            rc = md.regime_context
            lines.append(f"  시장 국면    : {rc.regime.value}")
            lines.append(f"  ADX          : {rc.adx_value:.1f}")
            lines.append(f"  BandWidth    : {rc.bb_width:.1f}%")
            lines.append(f"  스퀴즈 상태  : {'예' if rc.is_squeeze else '아니오'}")

        lines.append(f"\n  ── 기술적 지표 ──────────────────────────────────")
        for ind in md.indicator_results:
            lines.append(
                f"  [{ind.name:17s}] {ind.signal.value:6s}"
                f"  점수: {ind.score:+6.1f}  │  {ind.description}"
            )

    # ── Stage 2: Strategy Agent 결과 ─────────────────────
    if ts:
        lines.append(f"\n  🧠 [Stage 2] 전략 의사결정 에이전트")
        lines.append(f"  {thin[2:]}")
        lines.append(f"  매매 방향    : ★  {ts.signal.value}  ★  ({ts.side.value})")
        lines.append(f"  복합 점수    : {ts.composite_score:+.2f}  (-100 ~ +100)")
        lines.append(f"  적용 전략    : {ts.strategy_type.value}")
        lines.append(f"  예비 손절가  : {ts.suggested_stop_loss:,.2f}")
        lines.append(f"  예비 익절가  : {ts.suggested_take_profit:,.2f}")
        lines.append(f"  예비 R/R     : 1:{ts.suggested_rr_ratio}")

        if ts.regime_detail:
            lines.append(f"\n  🔄 체제 판별: {ts.regime_detail}")

    # ── Stage 3: Risk Agent 결과 ─────────────────────────
    ra = result.risk_approval
    if ra:
        emoji = "✅" if ra.approved else "🚫"
        lines.append(f"\n  {emoji} [Stage 3] 리스크 관리 에이전트")
        lines.append(f"  {thin[2:]}")

        if ra.approved and ra.veto_reason == VetoReason.APPROVED:
            lines.append(f"  판정         : ✅ 승인")
        else:
            lines.append(f"  판정         : 🚫 거부 ({ra.veto_reason.value})")

        if ra.position_size:
            ps = ra.position_size
            lines.append(f"  매매 수량    : {ps.shares:,}주")
            lines.append(f"  투자 금액    : {ps.position_value:,.0f}원 ({ps.position_pct:.1f}%)")
            lines.append(f"  거래 리스크  : {ps.risk_per_trade:,.0f}원 ({ps.risk_pct:.2f}%)")
            lines.append(f"  사이징 방법  : {ps.sizing_method}")

        if ra.final_stop_loss > 0:
            lines.append(f"  확정 손절가  : {ra.final_stop_loss:,.2f}")
            lines.append(f"  확정 익절가  : {ra.final_take_profit:,.2f}")
            lines.append(f"  확정 R/R     : 1:{ra.final_rr_ratio}")

        if ra.risk_score > 0:
            lines.append(f"  리스크 점수  : {ra.risk_score:.0f}/100")
            lines.append(f"  최대 손실    : {ra.max_loss_amount:,.0f}원")

        if ra.risk_commentary:
            lines.append(f"\n  📝 {ra.risk_commentary}")

    # ── Stage 4: Execution Agent 결과 ────────────────────
    ex = result.execution_result
    if ex:
        status_emoji = "✅" if ex.status == OrderStatus.FILLED else "❌"
        lines.append(f"\n  {status_emoji} [Stage 4] 체결 실행 에이전트")
        lines.append(f"  {thin[2:]}")
        lines.append(f"  주문 상태    : {ex.status.value}")

        if ex.filled_quantity > 0:
            lines.append(f"  체결 수량    : {ex.filled_quantity:,}주")
            lines.append(f"  체결 가격    : {ex.filled_price:,.2f}")
            lines.append(f"  슬리피지     : {ex.actual_slippage_pct:+.4f}%")
            lines.append(f"  수수료       : {ex.commission:,.2f}원")

        if ex.execution_log:
            lines.append(f"\n  📋 실행 로그:")
            for log_line in ex.execution_log:
                lines.append(f"     {log_line}")

    # ── LLM 분석 ─────────────────────────────────────────
    if ts and ts.llm_analysis:
        from ta_trader.utils.formatter import make_llm_analysis
        from ta_trader.models import TradingDecision
        # 임시 TradingDecision 생성하여 기존 포매터 활용
        decision = result.to_trading_decision()
        if decision:
            lines.append(make_llm_analysis(decision))

    # ── 요약 ─────────────────────────────────────────────
    if ts:
        lines.append(f"\n  📌 파이프라인 요약:")
        lines.append(f"     {ts.signal_rationale}")

    lines.append(f"\n  ⏱ 파이프라인 소요 시간: {result.pipeline_duration_ms:.0f}ms")
    lines.append(f"{bar}\n")

    return "\n".join(lines)


def format_screening_results(results: list[PipelineResult]) -> str:
    """복수 종목 스크리닝 결과 요약"""
    bar = "═" * 90
    thin = "─" * 90

    lines = [
        f"\n{bar}",
        f"  📋 에이전트 스크리닝 결과  |  총 {len(results)}종목",
        f"{bar}",
        "",
        f"  {'순위':>4s}  {'종목':8s}  {'현재가':>10s}  {'점수':>7s}  {'신호':6s}  "
        f"{'승인':4s}  {'수량':>6s}  {'리스크':>10s}  {'R/R':>7s}  {'종목명':>12s}",
        f"  {thin[2:]}",
    ]

    for i, r in enumerate(results, 1):
        ts = r.trade_signal
        ra = r.risk_approval

        if not ts:
            continue

        approved = "✅" if r.is_approved else "🚫"
        shares = f"{ra.position_size.shares:,}" if ra and ra.position_size else "-"
        risk = (
            f"{ra.position_size.risk_per_trade:,.0f}"
            if ra and ra.position_size else "-"
        )

        lines.append(
            f"  {i:>4d}  {ts.ticker:8s}  {ts.current_price:>10,.2f}  "
            f"{ts.composite_score:>+7.2f}  {ts.signal.value:6s}  "
            f"{approved:4s}  {shares:>6s}  {risk:>10s}  "
            f"1:{ts.suggested_rr_ratio:>5.2f}  {ts.name:>12s}"
        )

    # 승인/거부 요약
    approved_count = sum(1 for r in results if r.is_approved)
    buy_count = sum(
        1 for r in results
        if r.trade_signal and r.trade_signal.side == OrderSide.BUY and r.is_approved
    )

    lines.append(f"\n  {thin[2:]}")
    lines.append(
        f"  승인: {approved_count}/{len(results)}  |  "
        f"매수 추천: {buy_count}종목"
    )
    lines.append(f"\n  ⚠ 본 분석은 기술적 지표 기반 참고용이며 투자 조언이 아닙니다.")
    lines.append(f"{bar}\n")

    return "\n".join(lines)
