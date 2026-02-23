"""
ta_trader/signals/strategy.py
체제별 매매 전략 모듈

전략 패턴:
  - TrendFollowingStrategy : 추세장 → MACD/ADX 중심, DI 확인, 크로스 보너스
  - MeanReversionStrategy  : 횡보장 → RSI/BB 중심, 과매수/과매도 반전, 신호 반전 로직
  - BreakoutMomentumStrategy: 변동성 수축 → 스퀴즈 후 돌파 감지, 방향성 MACD 확인
  - AdaptiveDefaultStrategy : 약한 추세 → 기존 가중 평균과 유사, 전환 감시
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional

import pandas as pd

from ta_trader.constants import (
    SCORE_BUY, SCORE_SELL, SCORE_STRONG_BUY, SCORE_STRONG_SELL,
    STRATEGY_TREND_ADX, STRATEGY_TREND_RSI, STRATEGY_TREND_MACD, STRATEGY_TREND_BB,
    STRATEGY_REVERT_ADX, STRATEGY_REVERT_RSI, STRATEGY_REVERT_MACD, STRATEGY_REVERT_BB,
    STRATEGY_BREAKOUT_ADX, STRATEGY_BREAKOUT_RSI, STRATEGY_BREAKOUT_MACD, STRATEGY_BREAKOUT_BB,
    TREND_MACD_CROSS_BONUS, TREND_DI_CONFIRM_BONUS,
    REVERT_BB_BOUNCE_BONUS, REVERT_RSI_REVERSAL_BONUS,
    BREAKOUT_SQUEEZE_BONUS, BREAKOUT_VOLUME_BONUS,
    BB_UPPER_THRESHOLD, BB_LOWER_THRESHOLD,
    RSI_OVERBOUGHT, RSI_OVERSOLD,
)
from ta_trader.models import IndicatorResult, Signal, WeightSet
from ta_trader.signals.regime import RegimeContext


class BaseStrategy(ABC):
    """전략 기본 인터페이스"""

    @property
    @abstractmethod
    def name(self) -> str:
        """전략 이름"""

    @property
    @abstractmethod
    def weights(self) -> WeightSet:
        """전략별 가중치"""

    @abstractmethod
    def score(
        self,
        adx_result: IndicatorResult,
        rsi_result: IndicatorResult,
        macd_result: IndicatorResult,
        bb_result: IndicatorResult,
        regime_ctx: RegimeContext,
        row: Optional[pd.Series] = None,
        prev_row: Optional[pd.Series] = None,
    ) -> float:
        """체제별 보정 점수 산출 (-100 ~ +100)"""

    def score_to_signal(self, score: float) -> Signal:
        """점수를 매매 신호로 변환"""
        if score >= SCORE_STRONG_BUY:
            return Signal.STRONG_BUY
        if score >= SCORE_BUY:
            return Signal.BUY
        if score <= SCORE_STRONG_SELL:
            return Signal.STRONG_SELL
        if score <= SCORE_SELL:
            return Signal.SELL
        return Signal.NEUTRAL

    def _weighted_sum(
        self,
        adx_s: float, rsi_s: float, macd_s: float, bb_s: float,
        w: WeightSet,
    ) -> float:
        """가중 합산 공통 로직"""
        return (adx_s * w.adx + rsi_s * w.rsi + macd_s * w.macd + bb_s * w.bb) / 100.0


class TrendFollowingStrategy(BaseStrategy):
    """
    추세추종 전략 (ADX ≥ 25)

    핵심 원칙:
    - MACD와 ADX의 가중치를 높여 추세 방향에 순행
    - MACD 골든/데드 크로스 발생 시 보너스 점수
    - +DI/-DI 방향 확인으로 추세 방향 일치 시 추가 보너스
    - RSI 과매수/과매도에서 역추세 신호는 약화 처리
    """

    @property
    def name(self) -> str:
        return "추세추종"

    @property
    def weights(self) -> WeightSet:
        return WeightSet(
            STRATEGY_TREND_ADX, STRATEGY_TREND_RSI,
            STRATEGY_TREND_MACD, STRATEGY_TREND_BB,
        )

    def score(
        self,
        adx_result: IndicatorResult,
        rsi_result: IndicatorResult,
        macd_result: IndicatorResult,
        bb_result: IndicatorResult,
        regime_ctx: RegimeContext,
        row: Optional[pd.Series] = None,
        prev_row: Optional[pd.Series] = None,
    ) -> float:
        base = self._weighted_sum(
            adx_result.score, rsi_result.score,
            macd_result.score, bb_result.score,
            self.weights,
        )

        bonus = 0.0

        # MACD 크로스 보너스: 크로스가 발생했으면(description에 "크로스" 포함) 추가 점수
        if "크로스" in macd_result.description:
            bonus += TREND_MACD_CROSS_BONUS if macd_result.score > 0 else -TREND_MACD_CROSS_BONUS

        # +DI/-DI 방향 일치 보너스
        if row is not None:
            di_bullish = float(row["adx_pos"]) > float(row["adx_neg"])
            if di_bullish and macd_result.score > 0:
                bonus += TREND_DI_CONFIRM_BONUS
            elif not di_bullish and macd_result.score < 0:
                bonus -= TREND_DI_CONFIRM_BONUS

        # 추세장에서 RSI 과매수는 "아직 강하다"로 해석 → 역추세 패널티 약화
        if rsi_result.raw_value >= RSI_OVERBOUGHT and base > 0:
            # RSI의 매도 점수를 50% 감쇠
            rsi_dampened = rsi_result.score * 0.5
            base = self._weighted_sum(
                adx_result.score, rsi_dampened,
                macd_result.score, bb_result.score,
                self.weights,
            )

        return max(-100.0, min(100.0, round(base + bonus, 2)))


class MeanReversionStrategy(BaseStrategy):
    """
    평균회귀 전략 (ADX < 20, 횡보장)

    핵심 원칙:
    - RSI와 Bollinger Bands의 가중치를 높여 과매수/과매도 포착
    - BB 하단 터치 + RSI 과매도 동시 발생 시 매수 보너스
    - BB 상단 터치 + RSI 과매수 동시 발생 시 매도 보너스
    - MACD/ADX는 참고용으로만 사용 (낮은 가중치)
    - 추세 방향 신호(MACD)와 반전 신호(RSI/BB)가 충돌하면 반전 우선
    """

    @property
    def name(self) -> str:
        return "평균회귀"

    @property
    def weights(self) -> WeightSet:
        return WeightSet(
            STRATEGY_REVERT_ADX, STRATEGY_REVERT_RSI,
            STRATEGY_REVERT_MACD, STRATEGY_REVERT_BB,
        )

    def score(
        self,
        adx_result: IndicatorResult,
        rsi_result: IndicatorResult,
        macd_result: IndicatorResult,
        bb_result: IndicatorResult,
        regime_ctx: RegimeContext,
        row: Optional[pd.Series] = None,
        prev_row: Optional[pd.Series] = None,
    ) -> float:
        base = self._weighted_sum(
            adx_result.score, rsi_result.score,
            macd_result.score, bb_result.score,
            self.weights,
        )

        bonus = 0.0

        # BB 하단 + RSI 과매도 = 강한 반등 신호 (매수 보너스)
        if bb_result.raw_value <= BB_LOWER_THRESHOLD and rsi_result.raw_value <= RSI_OVERSOLD:
            bonus += REVERT_BB_BOUNCE_BONUS + REVERT_RSI_REVERSAL_BONUS

        # BB 상단 + RSI 과매수 = 강한 반락 신호 (매도 보너스)
        elif bb_result.raw_value >= BB_UPPER_THRESHOLD and rsi_result.raw_value >= RSI_OVERBOUGHT:
            bonus -= REVERT_BB_BOUNCE_BONUS + REVERT_RSI_REVERSAL_BONUS

        # RSI 이전 값 확인 가능하면 반전 감지
        if prev_row is not None:
            prev_rsi = float(prev_row["rsi"])
            curr_rsi = rsi_result.raw_value
            # 과매도 탈출 (RSI가 30 이하에서 30 위로 상승)
            if prev_rsi <= RSI_OVERSOLD < curr_rsi:
                bonus += REVERT_RSI_REVERSAL_BONUS
            # 과매수 탈출 (RSI가 70 이상에서 70 아래로 하락)
            elif prev_rsi >= RSI_OVERBOUGHT > curr_rsi:
                bonus -= REVERT_RSI_REVERSAL_BONUS

        return max(-100.0, min(100.0, round(base + bonus, 2)))


class BreakoutMomentumStrategy(BaseStrategy):
    """
    돌파 모멘텀 전략 (볼린저 밴드 스퀴즈 감지)

    핵심 원칙:
    - BandWidth가 수축(≤4%)된 상태에서 돌파를 대기
    - 상단 돌파(bb_pct > 1.0) + MACD 양전환 → 강한 매수
    - 하단 돌파(bb_pct < 0.0) + MACD 음전환 → 강한 매도
    - 아직 돌파가 발생하지 않았으면 중립 편향
    - ADX가 상승 전환 중이면 돌파 신뢰도 보너스
    """

    @property
    def name(self) -> str:
        return "돌파모멘텀"

    @property
    def weights(self) -> WeightSet:
        return WeightSet(
            STRATEGY_BREAKOUT_ADX, STRATEGY_BREAKOUT_RSI,
            STRATEGY_BREAKOUT_MACD, STRATEGY_BREAKOUT_BB,
        )

    def score(
        self,
        adx_result: IndicatorResult,
        rsi_result: IndicatorResult,
        macd_result: IndicatorResult,
        bb_result: IndicatorResult,
        regime_ctx: RegimeContext,
        row: Optional[pd.Series] = None,
        prev_row: Optional[pd.Series] = None,
    ) -> float:
        base = self._weighted_sum(
            adx_result.score, rsi_result.score,
            macd_result.score, bb_result.score,
            self.weights,
        )

        bonus = 0.0
        bb_pct = bb_result.raw_value

        # 스퀴즈 상태에서 상단 돌파
        if regime_ctx.is_squeeze and bb_pct >= 1.0:
            bonus += BREAKOUT_SQUEEZE_BONUS
            if macd_result.score > 0:
                bonus += BREAKOUT_VOLUME_BONUS  # MACD 방향 확인

        # 스퀴즈 상태에서 하단 돌파
        elif regime_ctx.is_squeeze and bb_pct <= 0.0:
            bonus -= BREAKOUT_SQUEEZE_BONUS
            if macd_result.score < 0:
                bonus -= BREAKOUT_VOLUME_BONUS

        # ADX 상승 전환 감지 (추세 형성 시작)
        if prev_row is not None:
            prev_adx = float(prev_row["adx"])
            curr_adx = float(row["adx"]) if row is not None else adx_result.raw_value
            if curr_adx > prev_adx:
                # ADX 상승 → 돌파 방향으로 보너스 강화
                if base > 0:
                    bonus += BREAKOUT_VOLUME_BONUS * 0.5
                elif base < 0:
                    bonus -= BREAKOUT_VOLUME_BONUS * 0.5

        # 스퀴즈 중 아직 돌파 미발생 → 점수를 중립 방향으로 감쇠
        if regime_ctx.is_squeeze and 0.0 < bb_pct < 1.0:
            base *= 0.6  # 40% 감쇠 → 관망 편향

        return max(-100.0, min(100.0, round(base + bonus, 2)))


class AdaptiveDefaultStrategy(BaseStrategy):
    """
    적응형 기본 전략 (약한 추세, 전환 구간)

    핵심 원칙:
    - 기존 가중 평균 방식과 동일한 기본 점수
    - 추세가 강해지는지 약해지는지 모니터링
    - 보너스/패널티 없이 순수 가중 합산
    """

    @property
    def name(self) -> str:
        return "적응형기본"

    @property
    def weights(self) -> WeightSet:
        return WeightSet(
            STRATEGY_BREAKOUT_ADX, STRATEGY_BREAKOUT_RSI,
            STRATEGY_BREAKOUT_MACD, STRATEGY_BREAKOUT_BB,
        )

    def score(
        self,
        adx_result: IndicatorResult,
        rsi_result: IndicatorResult,
        macd_result: IndicatorResult,
        bb_result: IndicatorResult,
        regime_ctx: RegimeContext,
        row: Optional[pd.Series] = None,
        prev_row: Optional[pd.Series] = None,
    ) -> float:
        base = self._weighted_sum(
            adx_result.score, rsi_result.score,
            macd_result.score, bb_result.score,
            self.weights,
        )
        return max(-100.0, min(100.0, round(base, 2)))


# ── 전략 팩토리 ──────────────────────────────────────────

_STRATEGY_MAP: dict[str, type[BaseStrategy]] = {
    "TREND_FOLLOWING":   TrendFollowingStrategy,
    "MEAN_REVERSION":    MeanReversionStrategy,
    "BREAKOUT_MOMENTUM": BreakoutMomentumStrategy,
    "ADAPTIVE_DEFAULT":  AdaptiveDefaultStrategy,
}


def create_strategy(regime_ctx: RegimeContext) -> BaseStrategy:
    """RegimeContext의 strategy 값에 따라 적합한 전략 인스턴스 반환"""
    cls = _STRATEGY_MAP.get(regime_ctx.strategy.name)
    if cls is None:
        return AdaptiveDefaultStrategy()
    return cls()
