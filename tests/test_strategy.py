"""
tests/test_strategy.py
체제 판별 + 전략 자동 전환 테스트
"""

from __future__ import annotations

import pandas as pd
import pytest

from ta_trader.models.short import (
    IndicatorResult, MarketRegime, Signal, StrategyType
)
from ta_trader.signals.regime import RegimeContext, classify_regime, detect_regime
from ta_trader.signals.strategy import (
    AdaptiveDefaultStrategy,
    BreakoutMomentumStrategy,
    MeanReversionStrategy,
    TrendFollowingStrategy,
    create_strategy,
)
from ta_trader.signals.composer import SignalComposer


# ── 체제 판별 테스트 ──────────────────────────────────────

class TestRegimeDetection:
    """detect_regime() 매트릭스 검증"""

    def test_strong_trend(self):
        row = pd.Series({"adx": 30.0, "adx_pos": 25.0, "adx_neg": 10.0, "bb_width": 8.0})
        ctx = detect_regime(row)
        assert ctx.regime == MarketRegime.STRONG_TREND
        assert ctx.strategy == StrategyType.TREND_FOLLOWING

    def test_sideways_squeeze_breakout(self):
        row = pd.Series({"adx": 15.0, "adx_pos": 14.0, "adx_neg": 16.0, "bb_width": 3.0})
        ctx = detect_regime(row)
        assert ctx.regime == MarketRegime.VOLATILE
        assert ctx.strategy == StrategyType.BREAKOUT_MOMENTUM
        assert ctx.is_squeeze is True

    def test_weak_trend_squeeze(self):
        row = pd.Series({"adx": 22.0, "adx_pos": 20.0, "adx_neg": 18.0, "bb_width": 3.5})
        ctx = detect_regime(row)
        assert ctx.regime == MarketRegime.VOLATILE
        assert ctx.strategy == StrategyType.BREAKOUT_MOMENTUM

    def test_sideways_expanding_mean_reversion(self):
        row = pd.Series({"adx": 18.0, "adx_pos": 15.0, "adx_neg": 17.0, "bb_width": 12.0})
        ctx = detect_regime(row)
        assert ctx.regime == MarketRegime.SIDEWAYS
        assert ctx.strategy == StrategyType.MEAN_REVERSION
        assert ctx.is_expanding is True

    def test_sideways_normal(self):
        row = pd.Series({"adx": 16.0, "adx_pos": 15.0, "adx_neg": 14.0, "bb_width": 6.0})
        ctx = detect_regime(row)
        assert ctx.regime == MarketRegime.SIDEWAYS
        assert ctx.strategy == StrategyType.MEAN_REVERSION

    def test_weak_trend_adaptive(self):
        row = pd.Series({"adx": 22.0, "adx_pos": 20.0, "adx_neg": 18.0, "bb_width": 7.0})
        ctx = detect_regime(row)
        assert ctx.regime == MarketRegime.WEAK_TREND
        assert ctx.strategy == StrategyType.ADAPTIVE_DEFAULT

    def test_squeeze_days_with_prev_rows(self):
        """스퀴즈 지속 기간이 prev_rows로부터 계산되는지 확인"""
        row = pd.Series({"adx": 15.0, "adx_pos": 14.0, "adx_neg": 16.0, "bb_width": 3.0})
        prev = pd.DataFrame({"bb_width": [3.0, 3.5, 2.8, 5.0, 3.2, 4.1, 6.0, 3.0, 2.5, 3.1]})
        ctx = detect_regime(row, prev)
        assert ctx.is_squeeze is True
        assert ctx.regime == MarketRegime.VOLATILE

    def test_classify_regime_legacy(self):
        """레거시 classify_regime() 하위 호환"""
        assert classify_regime(30.0) == MarketRegime.STRONG_TREND
        assert classify_regime(22.0) == MarketRegime.WEAK_TREND
        assert classify_regime(15.0) == MarketRegime.SIDEWAYS


# ── 전략 팩토리 테스트 ────────────────────────────────────

class TestStrategyFactory:
    """create_strategy() 팩토리 검증"""

    @pytest.fixture
    def _make_ctx(self):
        def _inner(regime, strategy, adx=25.0, bw=6.0):
            return RegimeContext(
                regime=regime, strategy=strategy,
                adx_value=adx, bb_width=bw,
                is_squeeze=bw <= 4.0, is_expanding=bw >= 10.0,
                detail="test",
            )
        return _inner

    def test_trend_following(self, _make_ctx):
        ctx = _make_ctx(MarketRegime.STRONG_TREND, StrategyType.TREND_FOLLOWING)
        assert isinstance(create_strategy(ctx), TrendFollowingStrategy)

    def test_mean_reversion(self, _make_ctx):
        ctx = _make_ctx(MarketRegime.SIDEWAYS, StrategyType.MEAN_REVERSION)
        assert isinstance(create_strategy(ctx), MeanReversionStrategy)

    def test_breakout(self, _make_ctx):
        ctx = _make_ctx(MarketRegime.VOLATILE, StrategyType.BREAKOUT_MOMENTUM, bw=3.0)
        assert isinstance(create_strategy(ctx), BreakoutMomentumStrategy)

    def test_adaptive(self, _make_ctx):
        ctx = _make_ctx(MarketRegime.WEAK_TREND, StrategyType.ADAPTIVE_DEFAULT)
        assert isinstance(create_strategy(ctx), AdaptiveDefaultStrategy)


# ── 전략별 점수 산출 테스트 ───────────────────────────────

class TestStrategyScoring:
    """동일 입력에 대해 전략별로 다른 점수를 산출하는지 검증"""

    @pytest.fixture
    def indicators(self):
        return (
            IndicatorResult("ADX", 35.0, Signal.BUY, 40.0, "ADX=35"),
            IndicatorResult("RSI", 45.0, Signal.NEUTRAL, 0.0, "RSI=45"),
            IndicatorResult("MACD", 0.5, Signal.BUY, 50.0, "MACD [크로스 발생!]"),
            IndicatorResult("BB", 0.3, Signal.NEUTRAL, 10.0, "BB%=30%"),
        )

    def test_trend_gives_highest_for_macd_cross(self, indicators):
        """추세추종은 MACD 크로스 보너스로 가장 높은 점수"""
        adx_r, rsi_r, macd_r, bb_r = indicators
        ctx = RegimeContext(
            MarketRegime.STRONG_TREND, StrategyType.TREND_FOLLOWING,
            35.0, 8.0, False, False, "",
        )
        strat = TrendFollowingStrategy()
        score = strat.score(adx_r, rsi_r, macd_r, bb_r, ctx)
        assert score > 30.0  # MACD 크로스 보너스가 점수를 올려야 함

    def test_mean_reversion_bb_rsi_bonus(self):
        """평균회귀는 BB 하단 + RSI 과매도에서 매수 보너스"""
        adx_r = IndicatorResult("ADX", 15.0, Signal.NEUTRAL, 0.0, "")
        rsi_r = IndicatorResult("RSI", 25.0, Signal.STRONG_BUY, 80.0, "RSI=25")
        macd_r = IndicatorResult("MACD", -0.1, Signal.SELL, -20.0, "")
        bb_r = IndicatorResult("BB", 0.1, Signal.BUY, 60.0, "BB%=10%")

        ctx = RegimeContext(
            MarketRegime.SIDEWAYS, StrategyType.MEAN_REVERSION,
            15.0, 12.0, False, True, "",
        )
        strat = MeanReversionStrategy()
        score = strat.score(adx_r, rsi_r, macd_r, bb_r, ctx)
        assert score > 40.0  # BB+RSI 보너스가 합산되어야 함

    def test_breakout_squeeze_dampening(self):
        """돌파모멘텀은 스퀴즈 중 미돌파 시 점수 감쇠"""
        adx_r = IndicatorResult("ADX", 18.0, Signal.NEUTRAL, 0.0, "")
        rsi_r = IndicatorResult("RSI", 50.0, Signal.NEUTRAL, 0.0, "")
        macd_r = IndicatorResult("MACD", 0.1, Signal.BUY, 30.0, "")
        bb_r = IndicatorResult("BB", 0.5, Signal.NEUTRAL, 0.0, "")

        ctx = RegimeContext(
            MarketRegime.VOLATILE, StrategyType.BREAKOUT_MOMENTUM,
            18.0, 3.0, True, False, "",
        )
        strat = BreakoutMomentumStrategy()
        score = strat.score(adx_r, rsi_r, macd_r, bb_r, ctx)
        # 스퀴즈 중 미돌파 → 60% 감쇠 → 점수가 낮아야 함
        assert abs(score) < 15.0

    def test_scores_bounded(self, indicators):
        """모든 전략의 점수가 -100~+100 범위 내"""
        adx_r, rsi_r, macd_r, bb_r = indicators
        for StratCls in [TrendFollowingStrategy, MeanReversionStrategy,
                         BreakoutMomentumStrategy, AdaptiveDefaultStrategy]:
            strat = StratCls()
            ctx = RegimeContext(
                MarketRegime.STRONG_TREND, StrategyType.TREND_FOLLOWING,
                35.0, 8.0, False, False, "",
            )
            sc = strat.score(adx_r, rsi_r, macd_r, bb_r, ctx)
            assert -100.0 <= sc <= 100.0, f"{StratCls.__name__} score {sc} out of range"


# ── SignalComposer 통합 테스트 ────────────────────────────

class TestSignalComposerWithStrategy:
    """compose_with_strategy() 통합 검증"""

    def test_compose_with_strategy_returns_regime_context(self):
        row = pd.Series({
            "adx": 30.0, "adx_pos": 25.0, "adx_neg": 10.0,
            "bb_width": 8.0, "rsi": 50.0,
            "Close": 100.0, "bb_upper": 105.0, "bb_middle": 100.0,
            "bb_lower": 95.0, "bb_pct": 0.5,
            "macd": 0.5, "macd_signal": 0.3, "macd_diff": 0.2,
        })
        adx_r = IndicatorResult("ADX", 30.0, Signal.BUY, 30.0, "")
        rsi_r = IndicatorResult("RSI", 50.0, Signal.NEUTRAL, 0.0, "")
        macd_r = IndicatorResult("MACD", 0.2, Signal.BUY, 30.0, "")
        bb_r = IndicatorResult("BB", 0.5, Signal.NEUTRAL, 0.0, "")

        composer = SignalComposer()
        score, signal, ctx = composer.compose_with_strategy(
            adx_r, rsi_r, macd_r, bb_r, row=row,
        )
        assert isinstance(ctx, RegimeContext)
        assert ctx.regime == MarketRegime.STRONG_TREND
        assert isinstance(score, float)
        assert isinstance(signal, Signal)

    def test_legacy_compose_still_works(self):
        """기존 compose() 인터페이스가 깨지지 않는지 확인"""
        adx_r = IndicatorResult("ADX", 30.0, Signal.BUY, 30.0, "")
        rsi_r = IndicatorResult("RSI", 50.0, Signal.NEUTRAL, 0.0, "")
        macd_r = IndicatorResult("MACD", 0.2, Signal.BUY, 30.0, "")
        bb_r = IndicatorResult("BB", 0.5, Signal.NEUTRAL, 0.0, "")

        composer = SignalComposer()
        score, signal, regime = composer.compose(adx_r, rsi_r, macd_r, bb_r)
        assert isinstance(regime, MarketRegime)
        assert isinstance(score, float)
        assert isinstance(signal, Signal)
