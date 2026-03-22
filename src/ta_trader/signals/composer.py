"""
ta_trader/signals/composer.py
체제별 전략 자동 전환 기반 복합 신호 생성

기존 가중치 방식에 더해, 각 시장 체제에 맞는 전략을 자동으로
선택하고 전략별 보정 점수를 산출합니다.

트레이딩 스타일에 따라:
  - 스윙: 기존 ADX 25/20 임계값, 오실레이터 보너스 적극 적용
  - 포지션: ADX 30/22 임계값, 추세 지표 가중치 상향
"""

from __future__ import annotations

from typing import Optional

import pandas as pd

from ta_trader.constants.short import (
    SCORE_BUY, SCORE_SELL, SCORE_STRONG_BUY, SCORE_STRONG_SELL,
)
from ta_trader.models.short import IndicatorResult, MarketRegime, Signal, StrategyType, WeightSet
from ta_trader.signals.regime import RegimeContext, classify_regime, detect_regime, get_weights
from ta_trader.signals.strategy import BaseStrategy, create_strategy
from ta_trader.style_config import StyleConfig


class SignalComposer:
    """
    4개 지표 결과를 받아 시장 체제를 판별하고,
    체제에 맞는 전략을 자동 선택하여 복합 점수를 계산합니다.
    """

    def compose(
        self,
        adx_result: IndicatorResult,
        rsi_result: IndicatorResult,
        macd_result: IndicatorResult,
        bb_result: IndicatorResult,
    ) -> tuple[float, Signal, MarketRegime]:
        """
        레거시 호환 인터페이스 (기존 코드와 동일한 시그니처).
        내부적으로 compose_with_strategy()를 호출하되,
        row/prev_row 없이 기본 가중치만 사용합니다.

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

    def compose_with_strategy(
        self,
        adx_result: IndicatorResult,
        rsi_result: IndicatorResult,
        macd_result: IndicatorResult,
        bb_result: IndicatorResult,
        row: pd.Series,
        prev_row: Optional[pd.Series] = None,
        prev_rows: Optional[pd.DataFrame] = None,
        style_config: Optional[StyleConfig] = None,
    ) -> tuple[float, Signal, RegimeContext]:
        """
        체제 자동 판별 + 전략 자동 선택 + 보정 점수 산출.

        Args:
            adx_result:   ADX 분석 결과
            rsi_result:   RSI 분석 결과
            macd_result:  MACD 분석 결과
            bb_result:    Bollinger Bands 분석 결과
            row:          최신 DataFrame 행 (체제 판별에 필요)
            prev_row:     직전 DataFrame 행 (크로스/반전 감지에 필요)
            prev_rows:    최근 N일 DataFrame (스퀴즈 지속 확인)
            style_config: 트레이딩 스타일 설정 (None이면 기본값)

        Returns:
            (composite_score, final_signal, regime_context)
        """
        # 1. 체제 판별 (스타일별 ADX 임계값 적용)
        adx_strong = style_config.adx_strong_trend if style_config else None
        adx_weak   = style_config.adx_weak_trend if style_config else None
        regime_ctx = detect_regime(row, prev_rows, adx_strong=adx_strong, adx_weak=adx_weak)

        # 2. 전략 자동 선택 (스타일 설정 전파)
        strategy = create_strategy(regime_ctx, style_config)

        # 3. 전략별 보정 점수 산출
        score = strategy.score(
            adx_result, rsi_result, macd_result, bb_result,
            regime_ctx, row, prev_row,
        )

        # 4. 점수 → 신호 변환 (스타일별 임계값 적용)
        signal = strategy.score_to_signal(score)

        return round(score, 2), signal, regime_ctx

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
