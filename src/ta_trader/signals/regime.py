"""
ta_trader/signals/regime.py
시장 국면 분류 및 전략 자동 선택

체제 판별 로직:
  1. ADX로 추세 강도 1차 판별
  2. Bollinger BandWidth로 변동성 상태 2차 판별
  3. 두 축의 조합으로 4가지 국면 분류 → 전략 자동 선택

  ┌──────────────────┬──────────────────┬──────────────────┐
  │                  │ BW 수축(≤4%)     │ BW 확대(≥10%)    │
  ├──────────────────┼──────────────────┼──────────────────┤
  │ ADX ≥ 25 (추세)  │ 추세추종         │ 추세추종          │
  │ ADX 20~25 (약)   │ 돌파모멘텀(대기)  │ 적응형기본        │
  │ ADX < 20 (횡보)  │ 돌파모멘텀(대기)  │ 평균회귀          │
  └──────────────────┴──────────────────┴──────────────────┘
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from ta_trader.constants import (
    ADX_STRONG_TREND, ADX_WEAK_TREND,
    BB_BANDWIDTH_SQUEEZE, BB_BANDWIDTH_EXPAND,
    WEIGHT_ADX_DEFAULT, WEIGHT_RSI_DEFAULT, WEIGHT_MACD_DEFAULT, WEIGHT_BB_DEFAULT,
    WEIGHT_ADX_TREND,   WEIGHT_RSI_TREND,   WEIGHT_MACD_TREND,   WEIGHT_BB_TREND,
    WEIGHT_ADX_SIDEWAYS, WEIGHT_RSI_SIDEWAYS, WEIGHT_MACD_SIDEWAYS, WEIGHT_BB_SIDEWAYS,
)
from ta_trader.models.short_models import MarketRegime, StrategyType, WeightSet


@dataclass
class RegimeContext:
    """체제 판별 결과와 부가 정보를 묶는 컨텍스트"""
    regime:        MarketRegime
    strategy:      StrategyType
    adx_value:     float
    bb_width:      float
    is_squeeze:    bool       # BandWidth 수축 상태 여부
    is_expanding:  bool       # BandWidth 확대 상태 여부
    detail:        str        # 사람이 읽을 수 있는 판별 근거

    @property
    def weights(self) -> WeightSet:
        """레거시 호환: 기존 가중치 체계도 함께 반환"""
        return get_weights(self.regime)


def classify_regime(adx_value: float) -> MarketRegime:
    """ADX 값으로 시장 국면 분류"""
    if adx_value >= ADX_STRONG_TREND:
        return MarketRegime.STRONG_TREND
    if adx_value >= ADX_WEAK_TREND:
        return MarketRegime.WEAK_TREND
    return MarketRegime.SIDEWAYS


def detect_regime(
    row: pd.Series,
    prev_rows: pd.DataFrame | None = None,
    adx_strong: float | None = None,
    adx_weak: float | None = None,
) -> RegimeContext:
    """
    ADX + Bollinger BandWidth 결합으로 시장 체제를 판별하고
    최적 전략을 자동 선택합니다.

    Args:
        row:        최신 지표 데이터 행
        prev_rows:  최근 N일 데이터 (스퀴즈 지속 여부 확인용, 없으면 단일 행 기준)
        adx_strong: 강한 추세 임계값 (스타일별 오버라이드, None이면 기본값)
        adx_weak:   약한 추세 임계값 (스타일별 오버라이드, None이면 기본값)

    Returns:
        RegimeContext: 체제, 전략, 부가 정보 포함
    """
    adx      = float(row["adx"])
    adx_pos  = float(row["adx_pos"])
    adx_neg  = float(row["adx_neg"])
    bb_width = float(row["bb_width"])

    is_squeeze   = bb_width <= BB_BANDWIDTH_SQUEEZE
    is_expanding = bb_width >= BB_BANDWIDTH_EXPAND

    strong_thr = adx_strong if adx_strong is not None else ADX_STRONG_TREND
    weak_thr   = adx_weak if adx_weak is not None else ADX_WEAK_TREND

    # 스퀴즈 지속 기간 확인 (prev_rows가 있으면)
    squeeze_days = 0
    if prev_rows is not None and "bb_width" in prev_rows.columns:
        recent_bw = prev_rows["bb_width"].tail(10)
        squeeze_days = int((recent_bw <= BB_BANDWIDTH_SQUEEZE).sum())

    regime, strategy, detail = _classify_matrix(
        adx, adx_pos, adx_neg, bb_width,
        is_squeeze, is_expanding, squeeze_days,
        strong_thr, weak_thr,
    )

    return RegimeContext(
        regime=regime,
        strategy=strategy,
        adx_value=adx,
        bb_width=bb_width,
        is_squeeze=is_squeeze,
        is_expanding=is_expanding,
        detail=detail,
    )


def _classify_matrix(
    adx: float,
    adx_pos: float,
    adx_neg: float,
    bb_width: float,
    is_squeeze: bool,
    is_expanding: bool,
    squeeze_days: int,
    strong_thr: float = ADX_STRONG_TREND,
    weak_thr: float = ADX_WEAK_TREND,
) -> tuple[MarketRegime, StrategyType, str]:
    """체제 판별 매트릭스 핵심 로직"""
    di_direction = "상승" if adx_pos > adx_neg else "하락"

    # 1. 강한 추세 (ADX >= strong_thr) → 추세추종
    if adx >= strong_thr:
        detail = (
            f"추세추종 전략: ADX={adx:.1f}(강한추세) "
            f"+DI={'우위' if adx_pos > adx_neg else '열위'} "
            f"→ {di_direction} 추세 방향 MACD 크로스 확인 후 진입"
        )
        return MarketRegime.STRONG_TREND, StrategyType.TREND_FOLLOWING, detail

    # 2. 횡보 + 변동성 수축 → 돌파 대기
    if adx < weak_thr and is_squeeze:
        days_note = f" ({squeeze_days}일 지속)" if squeeze_days > 0 else ""
        detail = (
            f"돌파모멘텀 전략: ADX={adx:.1f}(횡보) + "
            f"BW={bb_width:.1f}%(스퀴즈{days_note}) "
            f"→ 볼린저 밴드 돌파 + 거래량 확인 후 진입"
        )
        return MarketRegime.VOLATILE, StrategyType.BREAKOUT_MOMENTUM, detail

    # 3. 약한 추세 + 변동성 수축 → 돌파 대기
    if adx < strong_thr and is_squeeze:
        detail = (
            f"돌파모멘텀 전략: ADX={adx:.1f}(약한추세) + "
            f"BW={bb_width:.1f}%(스퀴즈) → 추세 형성 확인 후 방향 진입"
        )
        return MarketRegime.VOLATILE, StrategyType.BREAKOUT_MOMENTUM, detail

    # 4. 횡보 + 변동성 확대 → 평균회귀
    if adx < weak_thr and is_expanding:
        detail = (
            f"평균회귀 전략: ADX={adx:.1f}(횡보) + "
            f"BW={bb_width:.1f}%(변동성확대) "
            f"→ BB 상/하단 터치 + RSI 과매수/과매도 역추세 진입"
        )
        return MarketRegime.SIDEWAYS, StrategyType.MEAN_REVERSION, detail

    # 5. 횡보 일반 → 평균회귀
    if adx < weak_thr:
        detail = (
            f"평균회귀 전략: ADX={adx:.1f}(횡보) BW={bb_width:.1f}% "
            f"→ BB/RSI 과매수·과매도 구간 역추세 진입"
        )
        return MarketRegime.SIDEWAYS, StrategyType.MEAN_REVERSION, detail

    # 6. 약한 추세 → 적응형 기본
    detail = (
        f"적응형 기본 전략: ADX={adx:.1f}(약한추세) BW={bb_width:.1f}% "
        f"→ 가중 평균 기반, 추세 강화 시 추세추종 전환 대기"
    )
    return MarketRegime.WEAK_TREND, StrategyType.ADAPTIVE_DEFAULT, detail


def get_weights(regime: MarketRegime) -> WeightSet:
    """시장 국면에 맞는 가중치 반환"""
    if regime == MarketRegime.STRONG_TREND:
        return WeightSet(WEIGHT_ADX_TREND, WEIGHT_RSI_TREND, WEIGHT_MACD_TREND, WEIGHT_BB_TREND)
    if regime == MarketRegime.SIDEWAYS:
        return WeightSet(WEIGHT_ADX_SIDEWAYS, WEIGHT_RSI_SIDEWAYS, WEIGHT_MACD_SIDEWAYS, WEIGHT_BB_SIDEWAYS)
    return WeightSet(WEIGHT_ADX_DEFAULT, WEIGHT_RSI_DEFAULT, WEIGHT_MACD_DEFAULT, WEIGHT_BB_DEFAULT)
