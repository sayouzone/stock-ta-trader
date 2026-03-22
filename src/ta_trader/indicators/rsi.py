"""
ta_trader/indicators/rsi.py
RSI 신호 분석 모듈
"""

from __future__ import annotations

import pandas as pd

from ta_trader.constants.short import (
    RSI_LOWER_NEUTRAL, RSI_OVERBOUGHT, RSI_OVERSOLD, RSI_UPPER_NEUTRAL,
)
from ta_trader.models import IndicatorResult, Signal


class RSIAnalyzer:
    """RSI 기반 과매수/과매도 신호 분석"""

    def analyze(self, row: pd.Series) -> IndicatorResult:
        rsi = float(row["rsi"])
        score, signal = self._score(rsi)

        zone = (
            "과매수" if rsi >= RSI_OVERBOUGHT
            else "과매도" if rsi <= RSI_OVERSOLD
            else "중립구간"
        )
        return IndicatorResult(
            name="RSI",
            raw_value=rsi,
            signal=signal,
            score=round(score, 2),
            description=f"RSI={rsi:.1f} [{zone}]",
        )

    @staticmethod
    def _score(rsi: float) -> tuple[float, Signal]:
        if rsi >= RSI_OVERBOUGHT:
            return -80.0, Signal.STRONG_SELL
        if rsi >= RSI_UPPER_NEUTRAL:
            ratio = (rsi - RSI_UPPER_NEUTRAL) / (RSI_OVERBOUGHT - RSI_UPPER_NEUTRAL)
            return -ratio * 60.0, Signal.SELL
        if rsi <= RSI_OVERSOLD:
            return 80.0, Signal.STRONG_BUY
        if rsi <= RSI_LOWER_NEUTRAL:
            ratio = (RSI_LOWER_NEUTRAL - rsi) / (RSI_LOWER_NEUTRAL - RSI_OVERSOLD)
            return ratio * 60.0, Signal.BUY
        return 0.0, Signal.NEUTRAL
