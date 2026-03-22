"""
ta_trader/indicators/adx.py
ADX 신호 분석 모듈
"""

from __future__ import annotations

import pandas as pd

from ta_trader.constants.short import ADX_STRONG_TREND, ADX_WEAK_TREND
from ta_trader.models import IndicatorResult, Signal


class ADXAnalyzer:
    """ADX (+DI / -DI) 기반 추세 강도 및 방향 분석"""

    def analyze(self, row: pd.Series) -> IndicatorResult:
        """
        Args:
            row: 지표가 계산된 DataFrame 행

        Returns:
            IndicatorResult (name='ADX')
        """
        adx     = float(row["adx"])
        adx_pos = float(row["adx_pos"])
        adx_neg = float(row["adx_neg"])
        di_diff = adx_pos - adx_neg

        score, signal = self._score(adx, di_diff)

        desc = (
            f"ADX={adx:.1f} (+DI={adx_pos:.1f}, -DI={adx_neg:.1f}) "
            f"[{'강한추세' if adx >= ADX_STRONG_TREND else '약한추세' if adx >= ADX_WEAK_TREND else '횡보'}]"
        )
        return IndicatorResult(
            name="ADX",
            raw_value=adx,
            signal=signal,
            score=round(score, 2),
            description=desc,
        )

    @staticmethod
    def _score(adx: float, di_diff: float) -> tuple[float, Signal]:
        direction = 1 if di_diff > 0 else -1

        if adx >= ADX_STRONG_TREND:
            raw_score = min(adx, 60.0)
            signal    = Signal.STRONG_BUY if di_diff > 0 else Signal.STRONG_SELL
        elif adx >= ADX_WEAK_TREND:
            raw_score = adx * 0.8
            signal    = Signal.BUY if di_diff > 0 else Signal.SELL
        else:
            return 0.0, Signal.NEUTRAL

        return raw_score * direction, signal
