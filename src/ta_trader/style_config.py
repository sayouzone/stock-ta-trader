"""
ta_trader/style_config.py
트레이딩 스타일별 파라미터 해석기

스윙 트레이딩과 포지션 트레이딩의 핵심 차이:
  ┌───────────────┬──────────────────────┬──────────────────────┐
  │ 구분          │ 스윙 (2일~2주)        │ 포지션 (수주~수개월)  │
  ├───────────────┼──────────────────────┼──────────────────────┤
  │ 핵심 지표     │ RSI/BB/스토캐스틱     │ ADX/MACD/이평선      │
  │ 차트 주기     │ 일봉 + 4시간봉        │ 주봉 + 일봉          │
  │ 손절 기준     │ 1.5~2x 일봉 ATR      │ 2.5~3x 주봉 ATR     │
  │ 점수 임계값   │ 높음 (빈번한 매매)    │ 낮음 (보수적 진입)   │
  │ 추세 판별     │ ADX ≥ 25             │ ADX ≥ 30            │
  │ 전략 비중     │ 오실레이터 중심       │ 추세 지표 중심       │
  └───────────────┴──────────────────────┴──────────────────────┘
"""

from __future__ import annotations

from dataclasses import dataclass

from ta_trader.constants import (
    # 스윙 상수
    SWING_ATR_SL_MULTIPLIER, SWING_ATR_TP_MULTIPLIER,
    SWING_DEFAULT_SL_PCT, SWING_DEFAULT_TP_PCT,
    SWING_SCORE_STRONG_BUY, SWING_SCORE_BUY,
    SWING_SCORE_SELL, SWING_SCORE_STRONG_SELL,
    SWING_TREND_ADX, SWING_TREND_RSI, SWING_TREND_MACD, SWING_TREND_BB,
    SWING_REVERT_ADX, SWING_REVERT_RSI, SWING_REVERT_MACD, SWING_REVERT_BB,
    SWING_BREAKOUT_ADX, SWING_BREAKOUT_RSI, SWING_BREAKOUT_MACD, SWING_BREAKOUT_BB,
    SWING_MACD_CROSS_BONUS, SWING_DI_CONFIRM_BONUS,
    SWING_BB_BOUNCE_BONUS, SWING_RSI_REVERSAL_BONUS,
    SWING_SQUEEZE_BONUS, SWING_VOLUME_BONUS,
    ADX_STRONG_TREND, ADX_WEAK_TREND,
    # 포지션 상수
    POSITION_ATR_SL_MULTIPLIER, POSITION_ATR_TP_MULTIPLIER,
    POSITION_DEFAULT_SL_PCT, POSITION_DEFAULT_TP_PCT,
    POSITION_SCORE_STRONG_BUY, POSITION_SCORE_BUY,
    POSITION_SCORE_SELL, POSITION_SCORE_STRONG_SELL,
    POSITION_TREND_ADX, POSITION_TREND_RSI, POSITION_TREND_MACD, POSITION_TREND_BB,
    POSITION_REVERT_ADX, POSITION_REVERT_RSI, POSITION_REVERT_MACD, POSITION_REVERT_BB,
    POSITION_BREAKOUT_ADX, POSITION_BREAKOUT_RSI, POSITION_BREAKOUT_MACD, POSITION_BREAKOUT_BB,
    POSITION_MACD_CROSS_BONUS, POSITION_DI_CONFIRM_BONUS,
    POSITION_BB_BOUNCE_BONUS, POSITION_RSI_REVERSAL_BONUS,
    POSITION_SQUEEZE_BONUS, POSITION_VOLUME_BONUS,
    POSITION_ADX_STRONG_TREND, POSITION_ADX_WEAK_TREND,
)
from ta_trader.models import TradingStyle, WeightSet


@dataclass(frozen=True)
class StyleConfig:
    """특정 트레이딩 스타일에 대한 전체 파라미터 세트"""
    style: TradingStyle

    # 리스크 관리
    atr_sl_multiplier: float
    atr_tp_multiplier: float
    default_sl_pct: float
    default_tp_pct: float

    # 점수 → 신호 임계값
    score_strong_buy: float
    score_buy: float
    score_sell: float
    score_strong_sell: float

    # ADX 레짐 임계값
    adx_strong_trend: float
    adx_weak_trend: float

    # 전략별 가중치
    trend_weights: WeightSet
    revert_weights: WeightSet
    breakout_weights: WeightSet

    # 보너스 점수
    macd_cross_bonus: float
    di_confirm_bonus: float
    bb_bounce_bonus: float
    rsi_reversal_bonus: float
    squeeze_bonus: float
    volume_bonus: float


def get_style_config(style: TradingStyle) -> StyleConfig:
    """트레이딩 스타일에 맞는 전체 파라미터 세트를 반환"""
    if style == TradingStyle.POSITION:
        return StyleConfig(
            style=style,
            atr_sl_multiplier=POSITION_ATR_SL_MULTIPLIER,
            atr_tp_multiplier=POSITION_ATR_TP_MULTIPLIER,
            default_sl_pct=POSITION_DEFAULT_SL_PCT,
            default_tp_pct=POSITION_DEFAULT_TP_PCT,
            score_strong_buy=POSITION_SCORE_STRONG_BUY,
            score_buy=POSITION_SCORE_BUY,
            score_sell=POSITION_SCORE_SELL,
            score_strong_sell=POSITION_SCORE_STRONG_SELL,
            adx_strong_trend=POSITION_ADX_STRONG_TREND,
            adx_weak_trend=POSITION_ADX_WEAK_TREND,
            trend_weights=WeightSet(
                POSITION_TREND_ADX, POSITION_TREND_RSI,
                POSITION_TREND_MACD, POSITION_TREND_BB,
            ),
            revert_weights=WeightSet(
                POSITION_REVERT_ADX, POSITION_REVERT_RSI,
                POSITION_REVERT_MACD, POSITION_REVERT_BB,
            ),
            breakout_weights=WeightSet(
                POSITION_BREAKOUT_ADX, POSITION_BREAKOUT_RSI,
                POSITION_BREAKOUT_MACD, POSITION_BREAKOUT_BB,
            ),
            macd_cross_bonus=POSITION_MACD_CROSS_BONUS,
            di_confirm_bonus=POSITION_DI_CONFIRM_BONUS,
            bb_bounce_bonus=POSITION_BB_BOUNCE_BONUS,
            rsi_reversal_bonus=POSITION_RSI_REVERSAL_BONUS,
            squeeze_bonus=POSITION_SQUEEZE_BONUS,
            volume_bonus=POSITION_VOLUME_BONUS,
        )

    # 기본값: 스윙 트레이딩
    return StyleConfig(
        style=style,
        atr_sl_multiplier=SWING_ATR_SL_MULTIPLIER,
        atr_tp_multiplier=SWING_ATR_TP_MULTIPLIER,
        default_sl_pct=SWING_DEFAULT_SL_PCT,
        default_tp_pct=SWING_DEFAULT_TP_PCT,
        score_strong_buy=SWING_SCORE_STRONG_BUY,
        score_buy=SWING_SCORE_BUY,
        score_sell=SWING_SCORE_SELL,
        score_strong_sell=SWING_SCORE_STRONG_SELL,
        adx_strong_trend=ADX_STRONG_TREND,
        adx_weak_trend=ADX_WEAK_TREND,
        trend_weights=WeightSet(
            SWING_TREND_ADX, SWING_TREND_RSI,
            SWING_TREND_MACD, SWING_TREND_BB,
        ),
        revert_weights=WeightSet(
            SWING_REVERT_ADX, SWING_REVERT_RSI,
            SWING_REVERT_MACD, SWING_REVERT_BB,
        ),
        breakout_weights=WeightSet(
            SWING_BREAKOUT_ADX, SWING_BREAKOUT_RSI,
            SWING_BREAKOUT_MACD, SWING_BREAKOUT_BB,
        ),
        macd_cross_bonus=SWING_MACD_CROSS_BONUS,
        di_confirm_bonus=SWING_DI_CONFIRM_BONUS,
        bb_bounce_bonus=SWING_BB_BOUNCE_BONUS,
        rsi_reversal_bonus=SWING_RSI_REVERSAL_BONUS,
        squeeze_bonus=SWING_SQUEEZE_BONUS,
        volume_bonus=SWING_VOLUME_BONUS,
    )
