"""
tests/test_indicators.py
지표 계산 및 신호 분석 단위 테스트
"""

from __future__ import annotations

import pandas as pd
import pytest

from ta_trader.indicators.adx import ADXAnalyzer
from ta_trader.indicators.bollinger import BollingerAnalyzer
from ta_trader.indicators.calculator import IndicatorCalculator
from ta_trader.indicators.macd import MACDAnalyzer
from ta_trader.indicators.rsi import RSIAnalyzer
from ta_trader.models.short_models import Signal


class TestIndicatorCalculator:
    def test_all_columns_present(self, sample_ohlcv):
        calc = IndicatorCalculator(sample_ohlcv)
        expected = {"rsi", "macd", "macd_signal", "macd_diff",
                    "bb_upper", "bb_middle", "bb_lower", "bb_pct",
                    "adx", "adx_pos", "adx_neg"}
        assert expected.issubset(set(calc.dataframe.columns))

    def test_no_nan_after_compute(self, sample_ohlcv):
        calc = IndicatorCalculator(sample_ohlcv)
        assert calc.dataframe.isna().sum().sum() == 0

    def test_rsi_range(self, sample_ohlcv):
        calc = IndicatorCalculator(sample_ohlcv)
        rsi = calc.dataframe["rsi"]
        assert (rsi >= 0).all() and (rsi <= 100).all()

    def test_bb_pct_centered(self, sample_ohlcv):
        calc = IndicatorCalculator(sample_ohlcv)
        bb_pct = calc.dataframe["bb_pct"]
        assert bb_pct.mean() == pytest.approx(0.5, abs=0.2)


class TestRSIAnalyzer:
    def _make_row(self, rsi_val: float) -> pd.Series:
        return pd.Series({"rsi": rsi_val})

    def test_oversold(self):
        result = RSIAnalyzer().analyze(self._make_row(25.0))
        assert result.signal == Signal.STRONG_BUY
        assert result.score > 0

    def test_overbought(self):
        result = RSIAnalyzer().analyze(self._make_row(75.0))
        assert result.signal == Signal.STRONG_SELL
        assert result.score < 0

    def test_neutral(self):
        result = RSIAnalyzer().analyze(self._make_row(50.0))
        assert result.signal == Signal.NEUTRAL
        assert result.score == pytest.approx(0.0)


class TestADXAnalyzer:
    def _make_row(self, adx, pos, neg) -> pd.Series:
        return pd.Series({"adx": adx, "adx_pos": pos, "adx_neg": neg})

    def test_strong_uptrend(self):
        result = ADXAnalyzer().analyze(self._make_row(30, 25, 10))
        assert result.signal == Signal.STRONG_BUY

    def test_strong_downtrend(self):
        result = ADXAnalyzer().analyze(self._make_row(30, 10, 25))
        assert result.signal == Signal.STRONG_SELL

    def test_sideways(self):
        result = ADXAnalyzer().analyze(self._make_row(15, 15, 14))
        assert result.signal == Signal.NEUTRAL


class TestBollingerAnalyzer:
    def _make_row(self, bb_pct: float) -> pd.Series:
        return pd.Series({
            "bb_pct": bb_pct, "bb_upper": 65000, "bb_middle": 60000, "bb_lower": 55000,
        })

    def test_upper_breakout(self):
        result = BollingerAnalyzer().analyze(self._make_row(1.05))
        assert result.signal == Signal.STRONG_SELL

    def test_lower_breakout(self):
        result = BollingerAnalyzer().analyze(self._make_row(-0.05))
        assert result.signal == Signal.STRONG_BUY

    def test_middle(self):
        result = BollingerAnalyzer().analyze(self._make_row(0.5))
        assert result.signal == Signal.NEUTRAL
