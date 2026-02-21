"""
ta_trader/indicators/macd.py
MACD 신호 분석 모듈
"""

from __future__ import annotations

from typing import Optional

import pandas as pd

from ta_trader.models import IndicatorResult, Signal


class MACDAnalyzer:
    """MACD 히스토그램 및 크로스오버 기반 신호 분석"""

    def analyze(self, row: pd.Series, prev_row: Optional[pd.Series]) -> IndicatorResult:
        macd      = float(row["macd"])
        macd_sig  = float(row["macd_signal"])
        macd_diff = float(row["macd_diff"])

        crossover = self._detect_crossover(macd_diff, prev_row)
        score, signal = self._score(macd, macd_diff, crossover)

        cross_str = " [크로스 발생!]" if crossover else ""
        desc = f"MACD={macd:.3f} Signal={macd_sig:.3f} Hist={macd_diff:.3f}{cross_str}"

        return IndicatorResult(
            name="MACD",
            raw_value=macd_diff,
            signal=signal,
            score=round(score, 2),
            description=desc,
        )

    @staticmethod
    def _detect_crossover(macd_diff: float, prev_row: Optional[pd.Series]) -> bool:
        if prev_row is None:
            return False
        prev_diff = float(prev_row["macd_diff"])
        return (prev_diff <= 0 < macd_diff) or (prev_diff >= 0 > macd_diff)

    @staticmethod
    def _score(macd: float, macd_diff: float, crossover: bool) -> tuple[float, Signal]:
        base = min(abs(macd_diff) / max(abs(macd), 1e-6) * 50 + (30 if crossover else 0), 100)

        if macd_diff > 0:
            return base, Signal.STRONG_BUY if crossover else Signal.BUY
        if macd_diff < 0:
            return -base, Signal.STRONG_SELL if crossover else Signal.SELL
        return 0.0, Signal.NEUTRAL
