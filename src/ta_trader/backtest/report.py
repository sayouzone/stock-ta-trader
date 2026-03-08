"""
ta_trader/backtest/report.py
백테스팅 결과 터미널 보고서 포매터
"""

from __future__ import annotations

from ta_trader.models.backtest_models import BacktestResult, ExitReason


def format_backtest_report(result: BacktestResult) -> str:
    """BacktestResult를 구조화된 터미널 보고서로 변환"""
    bar = "═" * 68
    thin = "─" * 68

    lines = [
        f"\n{bar}",
        f"  📈 백테스팅 결과:  {result.ticker}  |  기간: {result.period}",
        f"{bar}",
        "",
        f"  ── 성과 요약 ─────────────────────────────────────────",
        f"  초기 자본        : {result.config.initial_capital:>14,.0f} 원",
        f"  최종 자본        : {result.equity_curve[-1]:>14,.0f} 원" if result.equity_curve else "",
        f"  총 수익률        : {result.total_return_pct:>+10.2f} %",
        f"  연환산 수익률    : {result.annual_return_pct:>+10.2f} %",
        f"  최대 낙폭 (MDD)  : {result.max_drawdown_pct:>10.2f} %",
        f"  샤프 비율        : {result.sharpe_ratio:>10.2f}",
        "",
        f"  ── 거래 통계 ─────────────────────────────────────────",
        f"  총 거래 수       : {result.total_trades:>10d} 회",
        f"  승리 / 패배      : {result.winning_trades:>5d} / {result.losing_trades:>d}",
        f"  승률             : {result.win_rate_pct:>10.1f} %",
        f"  손익비 (PF)      : {result.profit_factor:>10.2f}",
        f"  평균 보유 기간   : {result.avg_holding_days:>10.1f} 일",
        "",
        f"  ── 수익률 분포 ───────────────────────────────────────",
        f"  평균 수익 (승리) : {result.avg_win_pct:>+10.2f} %",
        f"  평균 손실 (패배) : {result.avg_loss_pct:>+10.2f} %",
        f"  최고 거래        : {result.best_trade_pct:>+10.2f} %",
        f"  최악 거래        : {result.worst_trade_pct:>+10.2f} %",
    ]

    # ── 전략별 성과 ───────────────────────────────────────
    if result.strategy_stats:
        lines.append("")
        lines.append(f"  ── 전략별 성과 ───────────────────────────────────────")
        lines.append(f"  {'전략':10s} {'거래수':>6s} {'승률':>8s} {'평균손익':>10s} {'누적손익':>10s}")
        lines.append(f"  {thin[2:]}")
        for name, st in sorted(result.strategy_stats.items()):
            lines.append(
                f"  {name:10s} {st['trades']:>6d} {st['win_rate']:>7.1f}% "
                f"{st['avg_pnl_pct']:>+9.2f}% {st['total_pnl_pct']:>+9.2f}%"
            )

    # ── 체제별 성과 ───────────────────────────────────────
    if result.regime_stats:
        lines.append("")
        lines.append(f"  ── 체제별 성과 ───────────────────────────────────────")
        lines.append(f"  {'체제':10s} {'거래수':>6s} {'승률':>8s} {'평균손익':>10s} {'누적손익':>10s}")
        lines.append(f"  {thin[2:]}")
        for name, st in sorted(result.regime_stats.items()):
            lines.append(
                f"  {name:10s} {st['trades']:>6d} {st['win_rate']:>7.1f}% "
                f"{st['avg_pnl_pct']:>+9.2f}% {st['total_pnl_pct']:>+9.2f}%"
            )

    # ── 청산 사유별 집계 ──────────────────────────────────
    if result.trades:
        lines.append("")
        lines.append(f"  ── 청산 사유 ─────────────────────────────────────────")
        reason_counts: dict[str, int] = {}
        for t in result.trades:
            reason_counts[t.exit_reason.value] = reason_counts.get(t.exit_reason.value, 0) + 1
        for reason, count in sorted(reason_counts.items(), key=lambda x: -x[1]):
            pct = count / len(result.trades) * 100
            bar_vis = "█" * int(pct / 5)
            lines.append(f"  {reason:8s} : {count:>4d} ({pct:5.1f}%) {bar_vis}")

    # ── 최근 거래 내역 (최대 10건) ────────────────────────
    if result.trades:
        recent = result.trades[-10:]
        lines.append("")
        lines.append(f"  ── 최근 거래 (최대 10건) ─────────────────────────────")
        lines.append(
            f"  {'진입일':>10s}  {'청산일':>10s}  {'방향':4s} "
            f"{'진입가':>10s} {'청산가':>10s} {'손익%':>8s} {'사유':6s} {'전략':8s}"
        )
        lines.append(f"  {thin[2:]}")
        for t in recent:
            lines.append(
                f"  {t.entry_date!s:>10s}  {t.exit_date!s:>10s}  {t.side.value:4s} "
                f"{t.entry_price:>10.2f} {t.exit_price:>10.2f} {t.pnl_pct:>+7.2f}% "
                f"{t.exit_reason.value:6s} {t.strategy.value:8s}"
            )

    # ── 설정 정보 ─────────────────────────────────────────
    lines.append("")
    lines.append(f"  ── 설정 ──────────────────────────────────────────────")
    cfg = result.config
    lines.append(
        f"  수수료: {cfg.commission_pct}% | 슬리피지: {cfg.slippage_pct}% | "
        f"포지션: {cfg.position_size_pct}% | 공매도: {'허용' if cfg.allow_short else '불가'} | "
        f"진입 임계: ±{cfg.min_score_entry}"
    )

    lines.append(f"{bar}\n")

    return "\n".join(lines)
