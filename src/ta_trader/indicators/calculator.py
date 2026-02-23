"""
ta_trader/indicators/calculator.py
모든 기술적 지표를 DataFrame에 추가하는 계산기
"""

from __future__ import annotations

import pandas as pd
from ta.momentum import RSIIndicator
from ta.trend import MACD, ADXIndicator
from ta.volatility import BollingerBands

from ta_trader.constants import (
    ADX_WINDOW, BB_STD_DEV, BB_WINDOW,
    MACD_FAST, MACD_SIGNAL_PERIOD, MACD_SLOW, RSI_WINDOW,
)
from ta_trader.exceptions import IndicatorCalculationError
from ta_trader.utils.logger import get_logger

logger = get_logger(__name__)


class IndicatorCalculator:
    """
    OHLCV DataFrame에 ADX·RSI·MACD·Bollinger Bands 컬럼을 추가합니다.

    추가 컬럼:
        rsi, macd, macd_signal, macd_diff,
        bb_upper, bb_middle, bb_lower, bb_pct,
        adx, adx_pos, adx_neg
    """

    def __init__(self, df: pd.DataFrame) -> None:
        self._df = df.copy()
        self._compute()

    def _compute(self) -> None:
        try:
            self._add_rsi()
            self._add_macd()
            self._add_bollinger()
            self._add_adx()
            self._df.dropna(inplace=True)
        except Exception as exc:
            raise IndicatorCalculationError(f"지표 계산 실패: {exc}") from exc

    def _add_rsi(self) -> None:
        ind = RSIIndicator(close=self._df["Close"], window=RSI_WINDOW)
        self._df["rsi"] = ind.rsi()

    def _add_macd(self) -> None:
        ind = MACD(
            close=self._df["Close"],
            window_slow=MACD_SLOW,
            window_fast=MACD_FAST,
            window_sign=MACD_SIGNAL_PERIOD,
        )
        self._df["macd"]        = ind.macd()
        self._df["macd_signal"] = ind.macd_signal()
        self._df["macd_diff"]   = ind.macd_diff()

    def _add_bollinger(self) -> None:
        ind = BollingerBands(
            close=self._df["Close"],
            window=BB_WINDOW,
            window_dev=BB_STD_DEV,
        )
        self._df["bb_upper"]  = ind.bollinger_hband()
        self._df["bb_middle"] = ind.bollinger_mavg()
        self._df["bb_lower"]  = ind.bollinger_lband()
        self._df["bb_pct"]    = ind.bollinger_pband()   # 0=하단, 1=상단
        self._df["bb_width"]  = ind.bollinger_wband() * 100  # BandWidth %

    def _add_adx(self) -> None:
        ind = ADXIndicator(
            high=self._df["High"],
            low=self._df["Low"],
            close=self._df["Close"],
            window=ADX_WINDOW,
        )
        self._df["adx"]     = ind.adx()
        self._df["adx_pos"] = ind.adx_pos()
        self._df["adx_neg"] = ind.adx_neg()

    @property
    def dataframe(self) -> pd.DataFrame:
        """지표가 추가된 DataFrame 반환"""
        return self._df

    def latest(self) -> pd.Series:
        """마지막 행(최신 데이터) 반환"""
        return self._df.iloc[-1]

    def previous(self) -> pd.Series | None:
        """직전 행 반환 (없으면 None)"""
        return self._df.iloc[-2] if len(self._df) >= 2 else None
