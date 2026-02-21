"""
ta_trader/signals/regime.py
시장 국면 분류 및 국면별 가중치 결정
"""

from __future__ import annotations

from ta_trader.constants import (
    ADX_STRONG_TREND, ADX_WEAK_TREND,
    WEIGHT_ADX_DEFAULT, WEIGHT_RSI_DEFAULT, WEIGHT_MACD_DEFAULT, WEIGHT_BB_DEFAULT,
    WEIGHT_ADX_TREND,   WEIGHT_RSI_TREND,   WEIGHT_MACD_TREND,   WEIGHT_BB_TREND,
    WEIGHT_ADX_SIDEWAYS, WEIGHT_RSI_SIDEWAYS, WEIGHT_MACD_SIDEWAYS, WEIGHT_BB_SIDEWAYS,
)
from ta_trader.models import MarketRegime, WeightSet


def classify_regime(adx_value: float) -> MarketRegime:
    """ADX 값으로 시장 국면 분류"""
    if adx_value >= ADX_STRONG_TREND:
        return MarketRegime.STRONG_TREND
    if adx_value >= ADX_WEAK_TREND:
        return MarketRegime.WEAK_TREND
    return MarketRegime.SIDEWAYS


def get_weights(regime: MarketRegime) -> WeightSet:
    """시장 국면에 맞는 가중치 반환"""
    if regime == MarketRegime.STRONG_TREND:
        return WeightSet(WEIGHT_ADX_TREND, WEIGHT_RSI_TREND, WEIGHT_MACD_TREND, WEIGHT_BB_TREND)
    if regime == MarketRegime.SIDEWAYS:
        return WeightSet(WEIGHT_ADX_SIDEWAYS, WEIGHT_RSI_SIDEWAYS, WEIGHT_MACD_SIDEWAYS, WEIGHT_BB_SIDEWAYS)
    return WeightSet(WEIGHT_ADX_DEFAULT, WEIGHT_RSI_DEFAULT, WEIGHT_MACD_DEFAULT, WEIGHT_BB_DEFAULT)
