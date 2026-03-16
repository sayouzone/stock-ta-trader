"""
ta_trader/indicators/volume.py
거래량 분석 모듈

스윙 트레이딩 스크리닝 핵심 지표:
  - 20일 평균 대비 거래량 비율 (Volume Ratio)
  - 거래량 급증 감지 (150~300% 이상)
  - 거래량 추세 (5일/20일 이평 비교)
"""

from __future__ import annotations

import pandas as pd
import numpy as np

from ta_trader.models.short import IndicatorResult, Signal


# ── 거래량 컬럼 계산 ──────────────────────────────────────

def compute_volume_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """
    거래량 관련 지표를 DataFrame에 추가합니다.

    추가 컬럼:
        vol_ma5:    5일 거래량 이동평균
        vol_ma20:   20일 거래량 이동평균
        vol_ratio:  당일 거래량 / 20일 평균 거래량 (배율)
        vol_trend:  5일 평균 / 20일 평균 (1 이상이면 단기 거래량 증가)
    """
    out = df.copy()
    vol = out["Volume"].astype(float)

    out["vol_ma5"] = vol.rolling(5).mean()
    out["vol_ma20"] = vol.rolling(20).mean()
    out["vol_ratio"] = vol / out["vol_ma20"]
    out["vol_trend"] = out["vol_ma5"] / out["vol_ma20"]

    return out


# ── 거래량 분석기 ─────────────────────────────────────────

class VolumeAnalyzer:
    """
    거래량 급증/감소 판단 및 신호 생성.

    임계값:
      - vol_ratio ≥ 2.5 (250%): 강한 수급 유입 → 강매수 신호
      - vol_ratio ≥ 1.5 (150%): 수급 유입 → 매수 보조 신호
      - vol_ratio ≤ 0.5 (50%):  거래 감소 → 관심 저하
    """

    STRONG_SURGE: float = 2.5   # 250%
    SURGE: float = 1.5          # 150%
    DRIED_UP: float = 0.5       # 50%

    def analyze(self, row: pd.Series) -> IndicatorResult:
        vol_ratio = float(row.get("vol_ratio", 1.0))
        vol_trend = float(row.get("vol_trend", 1.0))

        score, signal = self._score(vol_ratio, vol_trend)

        if vol_ratio >= self.STRONG_SURGE:
            zone = "강한급증"
        elif vol_ratio >= self.SURGE:
            zone = "급증"
        elif vol_ratio <= self.DRIED_UP:
            zone = "감소"
        else:
            zone = "보통"

        return IndicatorResult(
            name="Volume",
            raw_value=vol_ratio,
            signal=signal,
            score=round(score, 2),
            description=(
                f"거래량비율={vol_ratio:.2f}x "
                f"(추세={vol_trend:.2f}x) [{zone}]"
            ),
        )

    def _score(self, vol_ratio: float, vol_trend: float) -> tuple[float, Signal]:
        """거래량 비율 기반 점수 산출"""
        if vol_ratio >= self.STRONG_SURGE:
            return 30.0, Signal.STRONG_BUY
        if vol_ratio >= self.SURGE:
            return 15.0, Signal.BUY
        if vol_ratio <= self.DRIED_UP:
            return -10.0, Signal.NEUTRAL
        return 0.0, Signal.NEUTRAL


# ── 거래량 스크리닝 필터 ──────────────────────────────────

def is_volume_surge(row: pd.Series, threshold: float = 1.5) -> bool:
    """거래량 급증 여부 판단"""
    return float(row.get("vol_ratio", 0.0)) >= threshold


def volume_screen(df: pd.DataFrame, threshold: float = 1.5) -> pd.DataFrame:
    """거래량 급증 종목만 필터링"""
    if "vol_ratio" not in df.columns:
        df = compute_volume_indicators(df)
    return df[df["vol_ratio"] >= threshold]
