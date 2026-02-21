"""
ta_trader/signals/composer.py
개별 지표 점수를 가중 합산하여 복합 신호 생성
"""

from __future__ import annotations

from ta_trader.constants import (
    SCORE_BUY, SCORE_SELL, SCORE_STRONG_BUY, SCORE_STRONG_SELL,
)
from ta_trader.models import IndicatorResult, MarketRegime, Signal, WeightSet
from ta_trader.signals.regime import classify_regime, get_weights


class SignalComposer:
    """
    4개 지표 결과를 받아 시장 국면에 맞는 가중치로 복합 점수를 계산합니다.
    """

    def compose(
        self,
        adx_result: IndicatorResult,
        rsi_result: IndicatorResult,
        macd_result: IndicatorResult,
        bb_result: IndicatorResult,
    ) -> tuple[float, Signal, MarketRegime]:
        """
        Returns:
            (composite_score, final_signal, market_regime)
        """
        regime  = classify_regime(adx_result.raw_value)
        weights = get_weights(regime)

        score = self._weighted_score(
            adx_result.score, rsi_result.score,
            macd_result.score, bb_result.score,
            weights,
        )
        signal = self._score_to_signal(score)
        return round(score, 2), signal, regime

    @staticmethod
    def _weighted_score(
        adx_s: float, rsi_s: float, macd_s: float, bb_s: float,
        w: WeightSet,
    ) -> float:
        return (adx_s * w.adx + rsi_s * w.rsi + macd_s * w.macd + bb_s * w.bb) / 100.0

    @staticmethod
    def _score_to_signal(score: float) -> Signal:
        if score >= SCORE_STRONG_BUY:
            return Signal.STRONG_BUY
        if score >= SCORE_BUY:
            return Signal.BUY
        if score <= SCORE_STRONG_SELL:
            return Signal.STRONG_SELL
        if score <= SCORE_SELL:
            return Signal.SELL
        return Signal.NEUTRAL
