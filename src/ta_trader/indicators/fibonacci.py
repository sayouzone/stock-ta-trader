"""
ta_trader/indicators/fibonacci.py
피보나치 되돌림/확장 분석 모듈

스윙 트레이딩 활용:
  - 되돌림 (Retracement): 이전 상승파의 38.2%~61.8% 구간에서 반등 진입
  - 확장 (Extension): 161.8%, 261.8% 수준을 목표가로 설정
  - 지지/저항 레벨로 활용하여 손절/익절 수준 보조
"""

from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd
import numpy as np


# ── 피보나치 레벨 ─────────────────────────────────────────

FIBO_RETRACEMENT_LEVELS: list[float] = [0.0, 0.236, 0.382, 0.5, 0.618, 0.786, 1.0]
FIBO_EXTENSION_LEVELS: list[float] = [1.0, 1.272, 1.618, 2.0, 2.618]


@dataclass
class FibonacciLevels:
    """피보나치 되돌림/확장 레벨"""
    swing_high: float
    swing_low: float
    direction: str  # "up" or "down"

    # 되돌림 레벨 (이전 추세의 조정 구간)
    retracement: dict[float, float] = field(default_factory=dict)

    # 확장 레벨 (목표가)
    extension: dict[float, float] = field(default_factory=dict)

    @property
    def swing_range(self) -> float:
        return abs(self.swing_high - self.swing_low)

    @property
    def key_support(self) -> float:
        """핵심 지지 구간: 38.2% 되돌림"""
        return self.retracement.get(0.382, self.swing_low)

    @property
    def golden_zone_low(self) -> float:
        """골든존 하단: 61.8% 되돌림"""
        return self.retracement.get(0.618, self.swing_low)

    @property
    def golden_zone_high(self) -> float:
        """골든존 상단: 38.2% 되돌림"""
        return self.retracement.get(0.382, self.swing_high)

    @property
    def target_161(self) -> float:
        """1차 목표가: 161.8% 확장"""
        return self.extension.get(1.618, self.swing_high)

    @property
    def target_261(self) -> float:
        """2차 목표가: 261.8% 확장"""
        return self.extension.get(2.618, self.swing_high)


# ── 피보나치 계산 ─────────────────────────────────────────

def compute_fibonacci_levels(
    swing_high: float,
    swing_low: float,
    direction: str = "up",
) -> FibonacciLevels:
    """
    피보나치 되돌림/확장 레벨을 계산합니다.

    Args:
        swing_high:  최근 파동의 고점
        swing_low:   최근 파동의 저점
        direction:   "up"(상승파 후 되돌림) / "down"(하락파 후 되돌림)

    Returns:
        FibonacciLevels
    """
    diff = swing_high - swing_low

    retracement = {}
    extension = {}

    if direction == "up":
        # 상승 후 되돌림: 고점에서 아래로 (매수 진입 구간)
        for level in FIBO_RETRACEMENT_LEVELS:
            retracement[level] = round(swing_high - diff * level, 2)
        # 확장: 저점 기준으로 위로 (목표가)
        for level in FIBO_EXTENSION_LEVELS:
            extension[level] = round(swing_low + diff * level, 2)
    else:
        # 하락 후 되돌림: 저점에서 위로 (매도 진입 구간)
        for level in FIBO_RETRACEMENT_LEVELS:
            retracement[level] = round(swing_low + diff * level, 2)
        # 확장: 고점 기준으로 아래로 (목표가)
        for level in FIBO_EXTENSION_LEVELS:
            extension[level] = round(swing_high - diff * level, 2)

    return FibonacciLevels(
        swing_high=swing_high,
        swing_low=swing_low,
        direction=direction,
        retracement=retracement,
        extension=extension,
    )


def find_swing_points(
    df: pd.DataFrame,
    lookback: int = 60,
    window: int = 5,
) -> tuple[float, float, str]:
    """
    최근 lookback 기간 내 주요 스윙 고점/저점을 찾습니다.

    Args:
        df:       OHLCV DataFrame
        lookback: 탐색 기간 (기본 60일)
        window:   피벗 포인트 탐색 윈도우 (기본 5일)

    Returns:
        (swing_high, swing_low, direction)
        direction: 가장 최근 스윙이 상승("up") 또는 하락("down")
    """
    recent = df.tail(lookback)
    highs = recent["High"].values
    lows = recent["Low"].values

    swing_high = float(np.max(highs))
    swing_low = float(np.min(lows))

    # 고점과 저점의 발생 시점으로 방향 판단
    high_idx = int(np.argmax(highs))
    low_idx = int(np.argmin(lows))

    # 저점이 먼저 → 상승 파동, 고점이 먼저 → 하락 파동
    direction = "up" if low_idx < high_idx else "down"

    return swing_high, swing_low, direction


def get_fibonacci_zone(
    current_price: float,
    fibo: FibonacciLevels,
) -> str:
    """
    현재 가격이 피보나치 되돌림 어느 구간에 있는지 판단.

    Returns:
        "골든존(38.2~61.8%)" / "얕은되돌림(23.6~38.2%)" /
        "깊은되돌림(61.8~78.6%)" / "과매도(<78.6%)" /
        "추세진행중(0~23.6%)" / "범위밖"
    """
    levels = fibo.retracement
    if fibo.direction == "up":
        # 상승 후 되돌림: 가격이 내려올수록 깊은 되돌림
        r_0 = levels.get(0.0, fibo.swing_high)
        r_236 = levels.get(0.236, fibo.swing_high)
        r_382 = levels.get(0.382, fibo.swing_high)
        r_618 = levels.get(0.618, fibo.swing_low)
        r_786 = levels.get(0.786, fibo.swing_low)
        r_100 = levels.get(1.0, fibo.swing_low)

        if current_price >= r_236:
            return "추세진행중(0~23.6%)"
        if current_price >= r_382:
            return "얕은되돌림(23.6~38.2%)"
        if current_price >= r_618:
            return "골든존(38.2~61.8%)"
        if current_price >= r_786:
            return "깊은되돌림(61.8~78.6%)"
        return "과매도(>78.6%)"
    else:
        # 하락 후 되돌림: 가격이 올라갈수록 깊은 되돌림
        r_0 = levels.get(0.0, fibo.swing_low)
        r_236 = levels.get(0.236, fibo.swing_low)
        r_382 = levels.get(0.382, fibo.swing_low)
        r_618 = levels.get(0.618, fibo.swing_high)
        r_786 = levels.get(0.786, fibo.swing_high)

        if current_price <= r_236:
            return "추세진행중(0~23.6%)"
        if current_price <= r_382:
            return "얕은되돌림(23.6~38.2%)"
        if current_price <= r_618:
            return "골든존(38.2~61.8%)"
        if current_price <= r_786:
            return "깊은되돌림(61.8~78.6%)"
        return "과매도(>78.6%)"
