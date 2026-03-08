"""
ta_trader/backtest/metrics.py
백테스팅 성과 지표 계산

지표 목록:
  - 총 수익률 / 연환산 수익률 (CAGR)
  - 최대 낙폭 (Maximum Drawdown)
  - 샤프 비율 (Sharpe Ratio, 무위험 수익률 3.5%)
  - 승률 / 손익비 (Profit Factor)
  - 평균 보유 기간
  - 전략별·체제별 분해 성과
"""

from __future__ import annotations

import math
from collections import defaultdict

from ta_trader.models.backtest_models import BacktestResult, Trade

# 연간 거래일 수 (한국 시장 기준)
TRADING_DAYS_PER_YEAR: int = 252
# 무위험 수익률 (한국 국채 3년 기준 근사)
RISK_FREE_RATE: float = 0.035


def compute_metrics(result: BacktestResult) -> BacktestResult:
    """
    BacktestResult에 모든 성과 지표를 계산하여 채워넣습니다.
    result를 in-place로 갱신하고 반환합니다.
    """
    trades = result.trades
    equity = result.equity_curve
    config = result.config

    # ── 기본 집계 ─────────────────────────────────────────
    result.total_trades = len(trades)
    if not trades:
        return result

    winners = [t for t in trades if t.pnl > 0]
    losers  = [t for t in trades if t.pnl <= 0]

    result.winning_trades = len(winners)
    result.losing_trades  = len(losers)
    result.win_rate_pct   = round(len(winners) / len(trades) * 100, 2)

    # ── 수익률 ────────────────────────────────────────────
    if len(equity) >= 2:
        result.total_return_pct = round(
            (equity[-1] / equity[0] - 1) * 100, 2
        )
        n_days = len(equity)
        if n_days > 1 and equity[0] > 0:
            years = n_days / TRADING_DAYS_PER_YEAR
            if years > 0:
                ratio = equity[-1] / equity[0]
                if ratio > 0:
                    result.annual_return_pct = round(
                        (ratio ** (1 / years) - 1) * 100, 2
                    )

    # ── 최대 낙폭 (MDD) ──────────────────────────────────
    result.max_drawdown_pct = round(_max_drawdown(equity), 2)

    # ── 샤프 비율 ─────────────────────────────────────────
    result.sharpe_ratio = round(_sharpe_ratio(result.daily_returns), 2)

    # ── 손익비 (Profit Factor) ────────────────────────────
    gross_profit = sum(t.pnl for t in winners)
    gross_loss   = abs(sum(t.pnl for t in losers))
    result.profit_factor = round(
        gross_profit / gross_loss if gross_loss > 0 else float("inf"), 2
    )

    # ── 거래 통계 ─────────────────────────────────────────
    result.avg_holding_days = round(
        sum(t.holding_days for t in trades) / len(trades), 1
    )
    result.avg_win_pct = round(
        sum(t.pnl_pct for t in winners) / len(winners), 2
    ) if winners else 0.0
    result.avg_loss_pct = round(
        sum(t.pnl_pct for t in losers) / len(losers), 2
    ) if losers else 0.0

    pnl_pcts = [t.pnl_pct for t in trades]
    result.best_trade_pct  = round(max(pnl_pcts), 2)
    result.worst_trade_pct = round(min(pnl_pcts), 2)

    # ── 전략별·체제별 분해 ────────────────────────────────
    result.strategy_stats = _group_stats(trades, key=lambda t: t.strategy.value)
    result.regime_stats   = _group_stats(trades, key=lambda t: t.regime.value)

    return result


def _max_drawdown(equity: list[float]) -> float:
    """최대 낙폭 (%) 계산"""
    if not equity:
        return 0.0
    peak = equity[0]
    max_dd = 0.0
    for val in equity:
        if val > peak:
            peak = val
        dd = (peak - val) / peak * 100 if peak > 0 else 0.0
        if dd > max_dd:
            max_dd = dd
    return max_dd


def _sharpe_ratio(daily_returns: list[float]) -> float:
    """
    연환산 샤프 비율 계산.
    daily_returns: 일별 수익률 리스트 (0.01 = 1%)
    """
    if len(daily_returns) < 2:
        return 0.0

    avg = sum(daily_returns) / len(daily_returns)
    var = sum((r - avg) ** 2 for r in daily_returns) / (len(daily_returns) - 1)
    std = math.sqrt(var) if var > 0 else 0.0

    if std == 0:
        return 0.0

    daily_rf = RISK_FREE_RATE / TRADING_DAYS_PER_YEAR
    excess = avg - daily_rf
    return (excess / std) * math.sqrt(TRADING_DAYS_PER_YEAR)


def _group_stats(trades: list[Trade], key) -> dict:
    """그룹별 승률·평균수익률·거래수 집계"""
    groups: dict[str, list[Trade]] = defaultdict(list)
    for t in trades:
        groups[key(t)].append(t)

    stats = {}
    for name, group in groups.items():
        wins = [t for t in group if t.pnl > 0]
        stats[name] = {
            "trades":     len(group),
            "win_rate":   round(len(wins) / len(group) * 100, 1) if group else 0.0,
            "avg_pnl_pct": round(sum(t.pnl_pct for t in group) / len(group), 2),
            "total_pnl_pct": round(sum(t.pnl_pct for t in group), 2),
        }
    return stats
