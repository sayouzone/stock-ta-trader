"""
ta_trader/indicators/swing_calculator.py
스윙 트레이딩용 확장 지표 계산기

기존 IndicatorCalculator의 지표에 추가로:
  - ATR (Average True Range) + ATR%
  - 거래량 지표 (vol_ma5, vol_ma20, vol_ratio, vol_trend)
  - 이동평균 (EMA9, EMA21, SMA50, SMA200, 정배열 점수)
  - 피보나치 레벨 (별도 compute)
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from ta_trader.indicators.calculator import IndicatorCalculator
from ta_trader.indicators.atr import compute_atr, compute_atr_pct
from ta_trader.indicators.volume import compute_volume_indicators
from ta_trader.indicators.moving_avg import compute_moving_averages
from ta_trader.exceptions import IndicatorCalculationError
from ta_trader.utils.logger import get_logger

logger = get_logger(__name__)


class SwingIndicatorCalculator(IndicatorCalculator):
    """
    스윙 트레이딩에 필요한 확장 지표를 추가합니다.

    기존 지표: rsi, macd, macd_signal, macd_diff,
              bb_upper, bb_middle, bb_lower, bb_pct, bb_width,
              adx, adx_pos, adx_neg

    추가 지표: atr, atr_pct,
              vol_ma5, vol_ma20, vol_ratio, vol_trend,
              ema9, ema21, sma50, sma200,
              ema_cross, price_vs_sma200, ma_trend_score
    """

    def __init__(self, df: pd.DataFrame, atr_window: int = 14) -> None:
        self._atr_window = atr_window
        # 부모 __init__에서 _compute() 호출됨
        super().__init__(df)

    def _compute(self) -> None:
        """기존 지표 + 스윙 확장 지표"""
        try:
            # 기존 지표 (RSI, MACD, BB, ADX)
            self._add_rsi()
            self._add_macd()
            self._add_bollinger()
            self._add_adx()

            # 스윙 확장 지표 (NaN 제거 전에 추가)
            self._add_atr()
            self._add_volume()
            self._add_moving_averages()
            #print(self._df)

            #self._df.dropna(inplace=True)
            #print(self._df)
        except Exception as exc:
            raise IndicatorCalculationError(f"스윙 지표 계산 실패: {exc}") from exc

    def _add_atr(self) -> None:
        """ATR + ATR% 추가"""
        self._df["atr"] = compute_atr(self._df, window=self._atr_window)
        self._df["atr_pct"] = compute_atr_pct(self._df, window=self._atr_window)

    def _add_volume(self) -> None:
        """거래량 지표 추가"""
        vol = self._df["Volume"].astype(float)
        self._df["vol_ma5"] = vol.rolling(5).mean()
        self._df["vol_ma20"] = vol.rolling(20).mean()
        self._df["vol_ratio"] = vol / self._df["vol_ma20"]
        self._df["vol_trend"] = self._df["vol_ma5"] / self._df["vol_ma20"]

    def _add_moving_averages(self) -> None:
        """이동평균 지표 추가"""
        close = self._df["Close"]
        self._df["ema9"] = close.ewm(span=9, adjust=False).mean()
        self._df["ema21"] = close.ewm(span=21, adjust=False).mean()
        self._df["sma50"] = close.rolling(50).mean()
        self._df["sma200"] = close.rolling(200).mean()

        self._df["ema_cross"] = self._df["ema9"] - self._df["ema21"]

        # SMA200이 존재하는 행에 대해서만 계산
        self._df["price_vs_sma200"] = np.where(
            self._df["sma200"].notna() & (self._df["sma200"] > 0),
            close / self._df["sma200"],
            np.nan,
        )

        # 이동평균 정배열 점수 (0~4)
        self._df["ma_trend_score"] = (
            (close > self._df["ema9"]).astype(int)
            + (self._df["ema9"] > self._df["ema21"]).astype(int)
            + (self._df["ema21"] > self._df["sma50"]).astype(int)
            + (self._df["sma50"] > self._df["sma200"]).astype(int)
        )
