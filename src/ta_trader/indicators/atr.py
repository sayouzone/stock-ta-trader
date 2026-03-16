"""
ta_trader/indicators/atr.py
ATR (Average True Range) 지표 분석 모듈

스윙 트레이딩에서 핵심 역할:
  - 손절폭 결정: 진입가 - (ATR × 배수)
  - 트레일링 스톱: 종가 - (ATR × 배수)
  - 포지션 사이징: 자본 × 리스크% / (ATR × 배수)
  - 변동성 필터: ATR이 극단적이면 진입 보류
"""

from __future__ import annotations

import pandas as pd
import numpy as np

from ta_trader.models.short import IndicatorResult, Signal


# ── ATR 계산 ──────────────────────────────────────────────

def compute_atr(df: pd.DataFrame, window: int = 14) -> pd.Series:
    """
    True Range → ATR (지수이동평균 방식) 계산.

    Args:
        df: OHLCV DataFrame (High, Low, Close 필수)
        window: ATR 기간 (기본 14)

    Returns:
        ATR Series (인덱스 동일)
    """
    high = df["High"]
    low = df["Low"]
    prev_close = df["Close"].shift(1)

    tr1 = high - low
    tr2 = (high - prev_close).abs()
    tr3 = (low - prev_close).abs()

    true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = true_range.ewm(span=window, adjust=False).mean()
    return atr


def compute_atr_pct(df: pd.DataFrame, window: int = 14) -> pd.Series:
    """ATR을 종가 대비 %로 환산"""
    atr = compute_atr(df, window)
    return (atr / df["Close"]) * 100


# ── ATR 분석기 ────────────────────────────────────────────

class ATRAnalyzer:
    """
    ATR 기반 변동성 상태 분석.

    ATR%가 높으면 변동성 과다 → 포지션 축소 또는 진입 보류
    ATR%가 낮으면 변동성 수축 → 스퀴즈 돌파 대기
    """

    # ATR% 임계값
    HIGH_VOLATILITY_PCT: float = 4.0   # ATR% ≥ 4% → 고변동
    LOW_VOLATILITY_PCT: float = 1.0    # ATR% ≤ 1% → 저변동

    def analyze(self, row: pd.Series) -> IndicatorResult:
        atr = float(row["atr"])
        atr_pct = float(row["atr_pct"])

        if atr_pct >= self.HIGH_VOLATILITY_PCT:
            zone = "고변동"
            signal = Signal.NEUTRAL   # 진입 주의
            score = -20.0             # 감점 (리스크 증가)
        elif atr_pct <= self.LOW_VOLATILITY_PCT:
            zone = "저변동"
            signal = Signal.NEUTRAL   # 스퀴즈 대기
            score = 10.0              # 약간 가점 (돌파 기대)
        else:
            zone = "정상"
            signal = Signal.NEUTRAL
            score = 0.0

        return IndicatorResult(
            name="ATR",
            raw_value=atr,
            signal=signal,
            score=round(score, 2),
            description=(
                f"ATR={atr:.2f} ({atr_pct:.2f}%) [{zone}]"
            ),
        )


# ── ATR 기반 손절/트레일링 스톱 계산 ─────────────────────

def calc_atr_stop_loss(
    entry_price: float,
    atr: float,
    multiplier: float = 1.5,
    is_long: bool = True,
) -> float:
    """ATR 기반 손절가 계산"""
    if is_long:
        return round(entry_price - atr * multiplier, 2)
    return round(entry_price + atr * multiplier, 2)


def calc_atr_take_profit(
    entry_price: float,
    atr: float,
    multiplier: float = 3.0,
    is_long: bool = True,
) -> float:
    """ATR 기반 목표가 계산"""
    if is_long:
        return round(entry_price + atr * multiplier, 2)
    return round(entry_price - atr * multiplier, 2)


def calc_trailing_stop(
    current_price: float,
    atr: float,
    multiplier: float = 2.0,
    is_long: bool = True,
) -> float:
    """ATR 기반 트레일링 스톱 계산"""
    if is_long:
        return round(current_price - atr * multiplier, 2)
    return round(current_price + atr * multiplier, 2)
