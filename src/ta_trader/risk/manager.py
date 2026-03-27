"""
ta_trader/risk/manager.py
손절가·목표가·위험보상비율 산출

트레이딩 스타일별 차이:
  - 스윙: 1.5x ATR 손절, 3.0x ATR 익절 (타이트)
  - 포지션: 2.5x ATR 손절, 5.0x ATR 익절 (넓은 R배수)
"""

from __future__ import annotations

from typing import Optional

import pandas as pd

from ta_trader.constants.short import (
    ATR_STOP_LOSS_MULTIPLIER, ATR_TAKE_PROFIT_MULTIPLIER,
    DEFAULT_STOP_LOSS_PCT, DEFAULT_TAKE_PROFIT_PCT,
)
from ta_trader.models import RiskLevels, Signal
from ta_trader.config.style_config import StyleConfig


class RiskManager:
    """Bollinger Bands 기반 ATR 근사로 손절/익절 수준을 계산합니다."""

    def __init__(self, style_config: StyleConfig | None = None) -> None:
        self._style_config = style_config

    def calculate(self, price: float, row: pd.Series, signal: Signal) -> RiskLevels:
        """
        Args:
            price:  현재가
            row:    지표가 계산된 DataFrame 행
            signal: 최종 매매 신호

        Returns:
            RiskLevels (stop_loss, take_profit, risk_reward_ratio)
        """
        sc = self._style_config
        sl_mult = sc.atr_sl_multiplier if sc else ATR_STOP_LOSS_MULTIPLIER
        tp_mult = sc.atr_tp_multiplier if sc else ATR_TAKE_PROFIT_MULTIPLIER
        default_sl = sc.default_sl_pct if sc else DEFAULT_STOP_LOSS_PCT
        default_tp = sc.default_tp_pct if sc else DEFAULT_TAKE_PROFIT_PCT

        atr_proxy = (float(row["bb_upper"]) - float(row["bb_lower"])) / 4.0

        if signal.is_bullish:
            stop_loss   = max(float(row["bb_lower"]), price - atr_proxy * sl_mult)
            take_profit = min(float(row["bb_upper"]), price + atr_proxy * tp_mult)
        elif signal.is_bearish:
            stop_loss   = min(float(row["bb_upper"]), price + atr_proxy * sl_mult)
            take_profit = max(float(row["bb_lower"]), price - atr_proxy * tp_mult)
        else:
            stop_loss   = price * (1 - default_sl)
            take_profit = price * (1 + default_tp)

        risk   = abs(price - stop_loss)
        reward = abs(take_profit - price)
        rr     = round(reward / risk, 2) if risk > 1e-6 else 0.0

        return RiskLevels(
            stop_loss         = round(stop_loss, 2),
            take_profit       = round(take_profit, 2),
            risk_reward_ratio = rr,
        )
