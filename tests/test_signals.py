"""
tests/test_signals.py
복합 신호 및 시장 국면 단위 테스트
"""

from __future__ import annotations

import pytest

from ta_trader.models.short_models import IndicatorResult, MarketRegime, Signal
from ta_trader.signals.composer import SignalComposer
from ta_trader.signals.regime import classify_regime, get_weights


def _make_result(score: float) -> IndicatorResult:
    return IndicatorResult("test", 0.0, Signal.NEUTRAL, score, "")


class TestRegimeClassifier:
    def test_strong_trend(self):
        assert classify_regime(30.0) == MarketRegime.STRONG_TREND

    def test_weak_trend(self):
        assert classify_regime(22.0) == MarketRegime.WEAK_TREND

    def test_sideways(self):
        assert classify_regime(10.0) == MarketRegime.SIDEWAYS


class TestWeightSet:
    def test_default_weights_sum_100(self):
        w = get_weights(MarketRegime.WEAK_TREND)
        assert w.adx + w.rsi + w.macd + w.bb == 100

    def test_trend_weights_sum_100(self):
        w = get_weights(MarketRegime.STRONG_TREND)
        assert w.adx + w.rsi + w.macd + w.bb == 100


class TestSignalComposer:
    def _compose(self, adx_s, rsi_s, macd_s, bb_s, adx_raw=30):
        adx  = IndicatorResult("ADX", adx_raw, Signal.NEUTRAL, adx_s, "")
        rsi  = _make_result(rsi_s)
        macd = _make_result(macd_s)
        bb   = _make_result(bb_s)
        return SignalComposer().compose(adx, rsi, macd, bb)

    def test_all_bullish_gives_strong_buy(self):
        score, signal, _ = self._compose(80, 80, 80, 80, adx_raw=30)
        assert signal == Signal.STRONG_BUY
        assert score > 60

    def test_all_bearish_gives_strong_sell(self):
        score, signal, _ = self._compose(-80, -80, -80, -80, adx_raw=30)
        assert signal == Signal.STRONG_SELL
        assert score < -60

    def test_mixed_signals_neutral(self):
        score, signal, _ = self._compose(50, -50, 50, -50, adx_raw=15)
        assert signal == Signal.NEUTRAL
