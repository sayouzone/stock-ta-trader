"""
ta_trader/risk/manager.py
손절가·목표가·위험보상비율 산출
"""

from __future__ import annotations

import pandas as pd

from ta_trader.constants import (
    ATR_STOP_LOSS_MULTIPLIER, ATR_TAKE_PROFIT_MULTIPLIER,
    DEFAULT_STOP_LOSS_PCT, DEFAULT_TAKE_PROFIT_PCT,
)
from ta_trader.models import RiskLevels, Signal


class RiskManager:
    """Bollinger Bands 기반 ATR 근사로 손절/익절 수준을 계산합니다."""

    def calculate(self, price: float, row: pd.Series, signal: Signal) -> RiskLevels:
        """
        Args:
            price:  현재가
            row:    지표가 계산된 DataFrame 행
            signal: 최종 매매 신호

        Returns:
            RiskLevels (stop_loss, take_profit, risk_reward_ratio)
        """
        atr_proxy = (float(row["bb_upper"]) - float(row["bb_lower"])) / 4.0

        if signal.is_bullish:
            stop_loss   = max(float(row["bb_lower"]), price - atr_proxy * ATR_STOP_LOSS_MULTIPLIER)
            take_profit = min(float(row["bb_upper"]), price + atr_proxy * ATR_TAKE_PROFIT_MULTIPLIER)
        elif signal.is_bearish:
            stop_loss   = min(float(row["bb_upper"]), price + atr_proxy * ATR_STOP_LOSS_MULTIPLIER)
            take_profit = max(float(row["bb_lower"]), price - atr_proxy * ATR_TAKE_PROFIT_MULTIPLIER)
        else:
            stop_loss   = price * (1 - DEFAULT_STOP_LOSS_PCT)
            take_profit = price * (1 + DEFAULT_TAKE_PROFIT_PCT)

        risk   = abs(price - stop_loss)
        reward = abs(take_profit - price)
        rr     = round(reward / risk, 2) if risk > 1e-6 else 0.0

        return RiskLevels(
            stop_loss         = round(stop_loss, 2),
            take_profit       = round(take_profit, 2),
            risk_reward_ratio = rr,
        )
