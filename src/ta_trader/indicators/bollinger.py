"""
ta_trader/indicators/bollinger.py
Bollinger Bands 신호 분석 모듈
"""

from __future__ import annotations

import pandas as pd

from ta_trader.constants import BB_LOWER_THRESHOLD, BB_UPPER_THRESHOLD
from ta_trader.models import IndicatorResult, Signal


class BollingerAnalyzer:
    """Bollinger Bands %B 기반 과매수/과매도 신호 분석"""

    def analyze(self, row: pd.Series) -> IndicatorResult:
        bb_pct    = float(row["bb_pct"])
        bb_upper  = float(row["bb_upper"])
        bb_middle = float(row["bb_middle"])
        bb_lower  = float(row["bb_lower"])

        score, signal = self._score(bb_pct)
        band_width = (bb_upper - bb_lower) / bb_middle * 100

        desc = (
            f"BB%={bb_pct*100:.1f}% "
            f"(상단={bb_upper:.2f} 중간={bb_middle:.2f} 하단={bb_lower:.2f}) "
            f"밴드폭={band_width:.1f}%"
        )
        return IndicatorResult(
            name="Bollinger Bands",
            raw_value=bb_pct,
            signal=signal,
            score=round(score, 2),
            description=desc,
        )

    @staticmethod
    def _score(bb_pct: float) -> tuple[float, Signal]:
        if bb_pct >= 1.0:
            return -90.0, Signal.STRONG_SELL
        if bb_pct >= BB_UPPER_THRESHOLD:
            ratio = (bb_pct - BB_UPPER_THRESHOLD) / (1.0 - BB_UPPER_THRESHOLD)
            return -ratio * 60.0, Signal.SELL
        if bb_pct <= 0.0:
            return 90.0, Signal.STRONG_BUY
        if bb_pct <= BB_LOWER_THRESHOLD:
            ratio = (BB_LOWER_THRESHOLD - bb_pct) / BB_LOWER_THRESHOLD
            return ratio * 60.0, Signal.BUY
        return 0.0, Signal.NEUTRAL
