"""
ta_trader/data/fetcher.py
yfinance 기반 OHLCV 데이터 수집
"""

from __future__ import annotations

import pandas as pd
import yfinance as yf

from ta_trader.constants import DEFAULT_INTERVAL, DEFAULT_PERIOD, MIN_DATA_ROWS
from ta_trader.exceptions import DataFetchError, InsufficientDataError, InvalidTickerError
from ta_trader.utils.logger import get_logger

logger = get_logger(__name__)


class DataFetcher:
    """yfinance를 통한 주가 데이터 수집기"""

    def __init__(
        self,
        period: str = DEFAULT_PERIOD,
        interval: str = DEFAULT_INTERVAL,
    ) -> None:
        self.period   = period
        self.interval = interval

    def fetch(self, ticker: str) -> pd.DataFrame:
        """
        OHLCV 데이터를 수집하고 검증 후 반환합니다.

        Args:
            ticker: 종목 코드 (예: '005930.KS', 'AAPL')

        Returns:
            OHLCV DataFrame (인덱스: DatetimeIndex)

        Raises:
            InvalidTickerError: 유효하지 않은 티커
            DataFetchError: 데이터 수집 실패
            InsufficientDataError: 최소 데이터 부족
        """
        logger.info("데이터 수집 시작", ticker=ticker, period=self.period, interval=self.interval)

        try:
            info = yf.Ticker(ticker).info
            name = (
                info.get("shortName")
                or info.get("longName")
                or info.get("displayName")
                or ticker
            )
            
            df = yf.download(
                ticker,
                period=self.period,
                interval=self.interval,
                progress=False,
                auto_adjust=True,
            )
        except Exception as exc:
            raise DataFetchError(f"yfinance 수집 실패 [{ticker}]: {exc}") from exc

        if df is None or df.empty:
            raise InvalidTickerError(f"데이터 없음 - 유효하지 않은 티커일 수 있습니다: {ticker}")

        # MultiIndex 컬럼 평탄화
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        df = df.dropna()

        if len(df) < MIN_DATA_ROWS:
            raise InsufficientDataError(
                f"데이터 부족 [{ticker}]: {len(df)}행 (최소 {MIN_DATA_ROWS}행 필요)"
            )

        logger.info("데이터 수집 완료", ticker=ticker, rows=len(df))
        return name, df

    def info(self, ticker: str) -> tuple[str, dict]:
        # yfinance info (펀더멘털)
        name = ticker
        info = {}
        try:
            tk = yf.Ticker(ticker)
            info = tk.info or {}
            name = (
                info.get("shortName")
                or info.get("longName")
                or info.get("displayName")
                or ticker
            )
        except Exception:
            pass

        return name, info