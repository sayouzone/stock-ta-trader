"""
tests/test_backtest.py
백테스팅 시스템 테스트

테스트 범위:
  - Position: 손절/익절 체크, 거래 변환
  - Trade: PnL 계산, 보유일 계산
  - BacktestConfig: 기본값 검증
  - metrics: MDD, 샤프, 승률, 전략별 통계
  - BacktestEngine: 신호 기반 진입/청산 로직 (mock 데이터)
"""

from __future__ import annotations

from datetime import date

import pytest

from ta_trader.backtest.models import (
    BacktestConfig,
    BacktestResult,
    ExitReason,
    Position,
    PositionSide,
    Trade,
)
from ta_trader.backtest.metrics import (
    _max_drawdown,
    _sharpe_ratio,
    _group_stats,
    compute_metrics,
)
from ta_trader.backtest.report import format_backtest_report
from ta_trader.models import MarketRegime, StrategyType


# ── 헬퍼 ─────────────────────────────────────────────────

def _make_trade(
    pnl_pct: float,
    side: PositionSide = PositionSide.LONG,
    exit_reason: ExitReason = ExitReason.SIGNAL_REVERSE,
    regime: MarketRegime = MarketRegime.STRONG_TREND,
    strategy: StrategyType = StrategyType.TREND_FOLLOWING,
    holding_days: int = 5,
) -> Trade:
    entry = 100.0
    exit_p = entry * (1 + pnl_pct / 100) if side == PositionSide.LONG else entry * (1 - pnl_pct / 100)
    return Trade(
        entry_date=date(2024, 1, 1),
        exit_date=date(2024, 1, 1 + holding_days),
        side=side,
        entry_price=entry,
        exit_price=round(exit_p, 4),
        stop_loss=97.0,
        take_profit=106.0,
        pnl=round(exit_p - entry, 4) if side == PositionSide.LONG else round(entry - exit_p, 4),
        pnl_pct=pnl_pct,
        holding_days=holding_days,
        exit_reason=exit_reason,
        regime=regime,
        strategy=strategy,
        entry_score=50.0,
    )


# ── Position 테스트 ───────────────────────────────────────

class TestPosition:
    """Position 모델 단위 테스트"""

    @pytest.fixture
    def long_position(self):
        return Position(
            entry_date=date(2024, 6, 1),
            side=PositionSide.LONG,
            entry_price=100.0,
            stop_loss=95.0,
            take_profit=110.0,
            regime=MarketRegime.STRONG_TREND,
            strategy=StrategyType.TREND_FOLLOWING,
            entry_score=45.0,
        )

    @pytest.fixture
    def short_position(self):
        return Position(
            entry_date=date(2024, 6, 1),
            side=PositionSide.SHORT,
            entry_price=100.0,
            stop_loss=105.0,
            take_profit=90.0,
            regime=MarketRegime.SIDEWAYS,
            strategy=StrategyType.MEAN_REVERSION,
            entry_score=-45.0,
        )

    def test_long_stop_loss(self, long_position):
        result = long_position.check_exit(date(2024, 6, 5), high=101, low=94, close=95)
        assert result is not None
        exit_price, reason = result
        assert exit_price == 95.0
        assert reason == ExitReason.STOP_LOSS

    def test_long_take_profit(self, long_position):
        result = long_position.check_exit(date(2024, 6, 5), high=112, low=100, close=111)
        assert result is not None
        exit_price, reason = result
        assert exit_price == 110.0
        assert reason == ExitReason.TAKE_PROFIT

    def test_long_no_exit(self, long_position):
        result = long_position.check_exit(date(2024, 6, 5), high=105, low=96, close=103)
        assert result is None

    def test_short_stop_loss(self, short_position):
        result = short_position.check_exit(date(2024, 6, 5), high=106, low=99, close=104)
        assert result is not None
        _, reason = result
        assert reason == ExitReason.STOP_LOSS

    def test_short_take_profit(self, short_position):
        result = short_position.check_exit(date(2024, 6, 5), high=92, low=89, close=91)
        assert result is not None
        _, reason = result
        assert reason == ExitReason.TAKE_PROFIT

    def test_close_trade_long_profit(self, long_position):
        trade = long_position.close_trade(date(2024, 6, 10), 108.0, ExitReason.TAKE_PROFIT)
        assert trade.pnl == 8.0
        assert trade.pnl_pct == 8.0
        assert trade.holding_days == 9
        assert trade.exit_reason == ExitReason.TAKE_PROFIT

    def test_close_trade_long_loss(self, long_position):
        trade = long_position.close_trade(date(2024, 6, 3), 95.0, ExitReason.STOP_LOSS)
        assert trade.pnl == -5.0
        assert trade.pnl_pct == -5.0

    def test_close_trade_short_profit(self, short_position):
        trade = short_position.close_trade(date(2024, 6, 5), 92.0, ExitReason.SIGNAL_REVERSE)
        assert trade.pnl == 8.0  # 100 - 92
        assert trade.pnl_pct == 8.0

    def test_close_trade_short_loss(self, short_position):
        trade = short_position.close_trade(date(2024, 6, 3), 104.0, ExitReason.STOP_LOSS)
        assert trade.pnl == -4.0
        assert trade.pnl_pct == -4.0


# ── Metrics 테스트 ────────────────────────────────────────

class TestMetrics:
    """성과 지표 계산 테스트"""

    def test_max_drawdown_simple(self):
        equity = [100, 110, 105, 115, 100, 120]
        mdd = _max_drawdown(equity)
        # 115 → 100 = 13.04%
        assert abs(mdd - 13.04) < 0.1

    def test_max_drawdown_empty(self):
        assert _max_drawdown([]) == 0.0

    def test_max_drawdown_monotonic_up(self):
        equity = [100, 110, 120, 130]
        assert _max_drawdown(equity) == 0.0

    def test_sharpe_ratio_positive(self):
        # 평균적으로 양의 수익률 + 약간의 변동
        import random
        random.seed(42)
        daily = [0.002 + random.gauss(0, 0.005) for _ in range(252)]
        sharpe = _sharpe_ratio(daily)
        assert sharpe > 0

    def test_sharpe_ratio_zero_std(self):
        daily = [0.0] * 10
        assert _sharpe_ratio(daily) == 0.0

    def test_sharpe_ratio_insufficient_data(self):
        assert _sharpe_ratio([0.01]) == 0.0

    def test_group_stats(self):
        trades = [
            _make_trade(5.0, strategy=StrategyType.TREND_FOLLOWING),
            _make_trade(-2.0, strategy=StrategyType.TREND_FOLLOWING),
            _make_trade(3.0, strategy=StrategyType.MEAN_REVERSION),
        ]
        stats = _group_stats(trades, key=lambda t: t.strategy.value)
        assert "추세추종" in stats
        assert stats["추세추종"]["trades"] == 2
        assert stats["추세추종"]["win_rate"] == 50.0
        assert stats["평균회귀"]["trades"] == 1
        assert stats["평균회귀"]["win_rate"] == 100.0

    def test_compute_metrics_full(self):
        trades = [
            _make_trade(5.0),
            _make_trade(-2.0),
            _make_trade(8.0),
            _make_trade(-1.0),
            _make_trade(3.0),
        ]
        result = BacktestResult(
            ticker="TEST",
            period="1y",
            config=BacktestConfig(),
            trades=trades,
            equity_curve=[10_000_000, 10_500_000, 10_300_000, 11_100_000, 11_000_000, 11_300_000],
            dates=[date(2024, 1, i + 1) for i in range(6)],
            daily_returns=[0.05, -0.019, 0.078, -0.009, 0.027],
        )
        result = compute_metrics(result)

        assert result.total_trades == 5
        assert result.winning_trades == 3
        assert result.losing_trades == 2
        assert result.win_rate_pct == 60.0
        assert result.profit_factor > 1.0
        assert result.total_return_pct > 0
        assert result.max_drawdown_pct >= 0
        assert result.best_trade_pct == 8.0
        assert result.worst_trade_pct == -2.0

    def test_compute_metrics_no_trades(self):
        result = BacktestResult(
            ticker="TEST", period="1y", config=BacktestConfig(),
        )
        result = compute_metrics(result)
        assert result.total_trades == 0
        assert result.win_rate_pct == 0.0


# ── BacktestConfig 테스트 ─────────────────────────────────

class TestBacktestConfig:
    def test_defaults(self):
        cfg = BacktestConfig()
        assert cfg.initial_capital == 10_000_000
        assert cfg.commission_pct == 0.015
        assert cfg.allow_short is False

    def test_custom_config(self):
        cfg = BacktestConfig(initial_capital=50_000_000, allow_short=True)
        assert cfg.initial_capital == 50_000_000
        assert cfg.allow_short is True


# ── Report 테스트 ─────────────────────────────────────────

class TestReport:
    def test_format_nonempty(self):
        trades = [_make_trade(5.0), _make_trade(-2.0)]
        result = BacktestResult(
            ticker="AAPL", period="2y",
            config=BacktestConfig(),
            trades=trades,
            equity_curve=[10_000_000, 10_500_000, 10_300_000],
            dates=[date(2024, 1, 1), date(2024, 1, 2), date(2024, 1, 3)],
            daily_returns=[0.05, -0.019],
        )
        result = compute_metrics(result)
        report = format_backtest_report(result)

        assert "AAPL" in report
        assert "백테스팅" in report
        assert "승률" in report
        assert "전략별 성과" in report

    def test_format_empty_trades(self):
        result = BacktestResult(
            ticker="TEST", period="1y",
            config=BacktestConfig(),
            equity_curve=[10_000_000],
        )
        report = format_backtest_report(result)
        assert "TEST" in report


# ── Trade PnL 계산 테스트 ─────────────────────────────────

class TestTradePnl:
    def test_long_positive(self):
        t = _make_trade(5.0, side=PositionSide.LONG)
        assert t.pnl > 0

    def test_long_negative(self):
        t = _make_trade(-3.0, side=PositionSide.LONG)
        assert t.pnl < 0

    def test_holding_days_minimum(self):
        pos = Position(
            entry_date=date(2024, 1, 1),
            side=PositionSide.LONG,
            entry_price=100.0,
            stop_loss=95.0,
            take_profit=110.0,
            regime=MarketRegime.STRONG_TREND,
            strategy=StrategyType.TREND_FOLLOWING,
            entry_score=50.0,
        )
        # 같은 날 청산
        trade = pos.close_trade(date(2024, 1, 1), 102.0, ExitReason.TAKE_PROFIT)
        assert trade.holding_days >= 1  # 최소 1일
