"""
ta_trader/indicators/moving_avg.py
이동평균선 분석 모듈

스윙 트레이딩 활용:
  - EMA 9/21: 단기 추세 및 골든/데드 크로스
  - SMA 50:   중기 추세 기준선 (지지/저항)
  - SMA 200:  장기 추세 (강세장/약세장 판단)

시장 환경 판단:
  - 가격 > SMA200: 강세장 → 롱 바이어스
  - 가격 < SMA200: 약세장 → 숏 바이어스 또는 관망
  - EMA9 > EMA21: 단기 상승 추세
  - EMA9 < EMA21: 단기 하락 추세
"""

from __future__ import annotations

import pandas as pd
import numpy as np

from ta_trader.models.short import IndicatorResult, Signal


# ── 이동평균 컬럼 계산 ────────────────────────────────────

def compute_moving_averages(df: pd.DataFrame) -> pd.DataFrame:
    """
    이동평균 관련 지표를 DataFrame에 추가합니다.

    추가 컬럼:
        ema9, ema21:         단기 지수이동평균
        sma50, sma200:       중·장기 단순이동평균
        ema_cross:           EMA9 - EMA21 (양수=골든, 음수=데드)
        price_vs_sma200:     종가 / SMA200 비율 (1 이상=강세)
        ma_trend_score:      이동평균 정배열 점수 (0~4)
    """
    out = df.copy()
    close = out["Close"]

    out["ema9"] = close.ewm(span=9, adjust=False).mean()
    out["ema21"] = close.ewm(span=21, adjust=False).mean()
    out["sma50"] = close.rolling(50).mean()
    out["sma200"] = close.rolling(200).mean()

    out["ema_cross"] = out["ema9"] - out["ema21"]

    # SMA200 대비 가격 위치
    out["price_vs_sma200"] = np.where(
        out["sma200"] > 0,
        close / out["sma200"],
        np.nan,
    )

    # 이동평균 정배열 점수 (0~4)
    # 가격 > EMA9 > EMA21 > SMA50 > SMA200 이면 4점
    out["ma_trend_score"] = (
        (close > out["ema9"]).astype(int)
        + (out["ema9"] > out["ema21"]).astype(int)
        + (out["ema21"] > out["sma50"]).astype(int)
        + (out["sma50"] > out["sma200"]).astype(int)
    )

    return out


# ── 이동평균 분석기 ───────────────────────────────────────

class MovingAverageAnalyzer:
    """
    이동평균 정배열/역배열 및 시장 강세/약세 판단.

    ma_trend_score:
      4 = 완전 정배열 (강한 상승 추세)
      3 = 대체로 정배열 (상승 추세)
      2 = 혼재 (전환 구간)
      1 = 대체로 역배열 (하락 추세)
      0 = 완전 역배열 (강한 하락 추세)
    """

    def analyze(self, row: pd.Series) -> IndicatorResult:
        ma_score = int(row.get("ma_trend_score", 2))
        ema_cross = float(row.get("ema_cross", 0.0))
        price_vs_200 = float(row.get("price_vs_sma200", 1.0))

        score, signal = self._score(ma_score, price_vs_200)

        if ma_score >= 4:
            zone = "완전정배열"
        elif ma_score >= 3:
            zone = "정배열"
        elif ma_score <= 0:
            zone = "완전역배열"
        elif ma_score <= 1:
            zone = "역배열"
        else:
            zone = "혼재"

        above_200 = "위" if price_vs_200 >= 1.0 else "아래"

        return IndicatorResult(
            name="이동평균",
            raw_value=float(ma_score),
            signal=signal,
            score=round(score, 2),
            description=(
                f"정배열점수={ma_score}/4 "
                f"EMA크로스={ema_cross:.2f} "
                f"SMA200{above_200} [{zone}]"
            ),
        )

    @staticmethod
    def _score(ma_score: int, price_vs_200: float) -> tuple[float, Signal]:
        # 이동평균 정배열 점수 기반 (0~4 → -60~+60)
        base = (ma_score - 2) * 30.0  # 0→-60, 2→0, 4→+60

        # SMA200 위/아래 보너스
        if price_vs_200 >= 1.0:
            base += 10.0
        else:
            base -= 10.0

        base = max(-80.0, min(80.0, base))

        if base >= 50:
            return base, Signal.STRONG_BUY
        if base >= 20:
            return base, Signal.BUY
        if base <= -50:
            return base, Signal.STRONG_SELL
        if base <= -20:
            return base, Signal.SELL
        return base, Signal.NEUTRAL


# ── 시장 환경 판단 (SMA200) ──────────────────────────────

def is_bullish_market(row: pd.Series) -> bool:
    """가격이 SMA200 위에 있는지 확인 (강세장 판단)"""
    sma200 = row.get("sma200")
    if sma200 is None or pd.isna(sma200):
        return True  # 데이터 부족 시 기본 강세 가정
    return float(row["Close"]) > float(sma200)


def detect_ema_crossover(
    row: pd.Series, prev_row: pd.Series | None
) -> str:
    """EMA9/EMA21 크로스오버 감지"""
    if prev_row is None:
        return "없음"

    curr_cross = float(row.get("ema_cross", 0.0))
    prev_cross = float(prev_row.get("ema_cross", 0.0))

    if prev_cross <= 0 < curr_cross:
        return "골든크로스"
    if prev_cross >= 0 > curr_cross:
        return "데드크로스"
    return "없음"
