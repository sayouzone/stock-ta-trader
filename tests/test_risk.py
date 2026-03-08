"""
tests/test_risk.py
리스크 관리 단위 테스트
"""

from __future__ import annotations

import pandas as pd
import pytest

from ta_trader.models.short_models import Signal
from ta_trader.risk.manager import RiskManager


def _make_row(price: float = 60000) -> pd.Series:
    spread = price * 0.05
    return pd.Series({
        "bb_upper":  price + spread,
        "bb_middle": price,
        "bb_lower":  price - spread,
    })


class TestRiskManager:
    def test_bullish_stop_below_price(self):
        row    = _make_row(60000)
        levels = RiskManager().calculate(60000, row, Signal.STRONG_BUY)
        assert levels.stop_loss < 60000

    def test_bullish_target_above_price(self):
        row    = _make_row(60000)
        levels = RiskManager().calculate(60000, row, Signal.STRONG_BUY)
        assert levels.take_profit > 60000

    def test_risk_reward_positive(self):
        row    = _make_row(60000)
        levels = RiskManager().calculate(60000, row, Signal.BUY)
        assert levels.risk_reward_ratio > 0

    def test_neutral_uses_default_pct(self):
        row    = _make_row(60000)
        levels = RiskManager().calculate(60000, row, Signal.NEUTRAL)
        assert levels.stop_loss   == pytest.approx(60000 * 0.97, rel=0.01)
        assert levels.take_profit == pytest.approx(60000 * 1.05, rel=0.01)
