"""
ta_trader/data/krx_stock_fetcher.py
yfinance 기반 OHLCV 데이터 수집
"""

from __future__ import annotations

import os
import pandas as pd
import requests

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional

from ta_trader.constants import DEFAULT_INTERVAL, DEFAULT_PERIOD, MIN_DATA_ROWS
from ta_trader.exceptions import DataFetchError, InsufficientDataError, InvalidTickerError
from ta_trader.utils.logger import get_logger

logger = get_logger(__name__)

class Market(str, Enum):
    """KRX 시장 구분"""
    KOSPI = "STK"
    KOSDAQ = "KSQ"
    KONEX = "KNX"
 
    @property
    def yahoo_suffix(self) -> str:
        """Yahoo Finance 티커 접미사"""
        return {
            Market.KOSPI: ".KS",
            Market.KOSDAQ: ".KQ",
            Market.KONEX: ".KN",
        }[self]
 
    @property
    def display_name(self) -> str:
        return {
            Market.KOSPI: "코스피",
            Market.KOSDAQ: "코스닥",
            Market.KONEX: "코넥스",
        }[self]

@dataclass
class StockInfo:
    """종목 정보"""
    code: str           # 종목코드 (6자리)
    name: str           # 종목명
    market: Market      # 시장 구분
    sector: str = ""    # 업종
 
    @property
    def yahoo_ticker(self) -> str:
        """Yahoo Finance 티커 형식"""
        return f"{self.code}{self.market.yahoo_suffix}"
 
    def __repr__(self) -> str:
        return (
            f"StockInfo(name='{self.name}', code='{self.code}', "
            f"market='{self.market.display_name}', ticker='{self.yahoo_ticker}')"
        )

class KRXStockFetcher:
    """
    KRX 종목명을 Yahoo Finance 티커로 변환하는 클래스.
 
    KRX 공식 API에서 전체 종목 리스트를 가져와 캐싱한 뒤,
    종목명 검색 및 Yahoo Finance 티커 변환 기능을 제공합니다.
    """

    #KRX_API_URL = "http://data.krx.co.kr/comm/bldAttend498/getJsonData.cmd"
    KRX_API_URL = "https://data.krx.co.kr/contents/MDC/MDI/mdiLoader/index.cmd?menuId=MDC0201020203"

    def __init__(
        self, 
        stock_path: Optional[str] = "data/stocks/krx_stock_data_4128_20260319.csv",
        etf_path: Optional[str] = "data/stocks/krx_etf_data_0437_20260319.csv",
    ) -> None:
        """
        Args:
            stock_path: 종목 리스트 캐시 CSV 파일 경로.
                        지정 시 파일이 있으면 로드, 없으면 API 호출 후 저장.
            etf_path: ETF 리스트 캐시 CSV 파일 경로.
                        지정 시 파일이 있으면 로드, 없으면 API 호출 후 저장.
        """
        self._stock_path = Path(stock_path) if stock_path else None
        self._etf_path = Path(etf_path) if etf_path else None
        self._stocks: dict[str, StockInfo] = {}       # name -> StockInfo
        self._code_map: dict[str, StockInfo] = {}     # code -> StockInfo
        self._loaded = False

    # ─────────────────────────────────────────────
    # Public API
    # ─────────────────────────────────────────────
 
    def load(self, force_refresh: bool = False) -> "KRXStockFetcher":
        """
        종목 데이터를 로드합니다.
 
        Args:
            force_refresh: True이면 캐시를 무시하고 KRX API에서 새로 가져옵니다.
        """
        if self._loaded and not force_refresh:
            return self

        #logger.info("Cache Path %s %s %d", os.getcwd(), self._stock_path, self._stock_path.exists())

        self._stocks.clear()
        self._code_map.clear()
 
        if self._stock_path and self._stock_path.exists() and not force_refresh:
            logger.info("종목 파일에서 종목 데이터 로드: %s", self._stock_path)
            self._load_stocks_from_csv(self._stock_path)
        else:
            logger.info("KRX API에서 종목 데이터 가져오는 중...")
            self._fetch_from_krx()
            if self._stock_path:
                self._save_to_csv(self._stock_path)
                logger.info("캐시 파일 저장 완료: %s", self._stock_path)

        if self._etf_path and self._etf_path.exists() and not force_refresh:
            logger.info("ETF 파일에서 종목 데이터 로드: %s", self._etf_path)
            self._load_etfs_from_csv(self._etf_path)
        else:
            logger.info("KRX API에서 종목 데이터 가져오는 중...")
            self._fetch_from_krx()
            if self._etf_path:
                self._save_to_csv(self._etf_path)
                logger.info("캐시 파일 저장 완료: %s", self._etf_path)
 
        self._loaded = True
        logger.info("총 %d개 종목 로드 완료", len(self._stocks))
        return self

    def get_ticker(self, name_or_code: str) -> Optional[str]:
        """
        종목명 또는 종목코드로 Yahoo Finance 티커를 반환합니다.
 
        Args:
            name_or_code: 종목명 (예: "삼성전자") 또는 종목코드 (예: "005930")
 
        Returns:
            Yahoo Finance 티커 문자열 (예: "005930.KS") 또는 None
        """
        self._ensure_loaded()
        info = self._find_stock(name_or_code)
        return info.yahoo_ticker if info else None
 
    def get_info(self, name_or_code: str) -> Optional[StockInfo]:
        """종목명 또는 종목코드로 종목 상세 정보를 반환합니다."""
        self._ensure_loaded()
        return self._find_stock(name_or_code)
 
    def search(self, keyword: str, limit: int = 20) -> list[StockInfo]:
        """
        키워드로 종목을 검색합니다 (부분 문자열 매칭).
 
        Args:
            keyword: 검색 키워드 (예: "삼성", "카카오")
            limit: 최대 결과 수
 
        Returns:
            매칭되는 StockInfo 리스트
        """
        self._ensure_loaded()
        keyword_lower = keyword.lower()
        results = [
            info for name, info in self._stocks.items()
            if keyword_lower in name.lower()
            or keyword_lower in info.code
        ]
        return results[:limit]
 
    def batch_convert(self, names: list[str]) -> dict[str, Optional[str]]:
        """
        여러 종목명을 한꺼번에 Yahoo Finance 티커로 변환합니다.
 
        Args:
            names: 종목명 리스트
 
        Returns:
            {종목명: Yahoo Finance 티커 또는 None} 딕셔너리
        """
        self._ensure_loaded()
        return {name: self.get_ticker(name) for name in names}
 
    def to_dataframe(self) -> pd.DataFrame:
        """전체 종목 리스트를 DataFrame으로 반환합니다."""
        self._ensure_loaded()
        records = [
            {
                "종목코드": info.code,
                "종목명": info.name,
                "시장": info.market.display_name,
                "업종": info.sector,
                "Yahoo_Ticker": info.yahoo_ticker,
            }
            for info in self._stocks.values()
        ]
        return pd.DataFrame(records)
 
    @property
    def stock_count(self) -> int:
        self._ensure_loaded()
        return len(self._stocks)
 
    # ─────────────────────────────────────────────
    # Private Methods
    # ─────────────────────────────────────────────
 
    def _ensure_loaded(self) -> None:
        if not self._loaded:
            self.load()
 
    def _find_stock(self, name_or_code: str) -> Optional[StockInfo]:
        """종목명 또는 코드로 StockInfo를 찾습니다."""
        # 1) 정확한 종목명 매칭
        if name_or_code in self._stocks:
            return self._stocks[name_or_code]
 
        # 2) 종목코드 매칭
        code = name_or_code.zfill(6) if name_or_code.isdigit() else name_or_code
        logger.info("종목코드: %s %s", name_or_code, code)
        if code in self._code_map:
            return self._code_map[code]

        # 3) .KS 또는 .KQ 포함 코드 매칭
        index = name_or_code.find('.')
        code = name_or_code[:index] if index != -1 else name_or_code
        logger.info("종목코드: %s %s", name_or_code, code)
        if code in self._code_map:
            return self._code_map[code]
 
        # 4) 대소문자 무시 매칭
        name_lower = name_or_code.lower()
        for name, info in self._stocks.items():
            if name.lower() == name_lower:
                return info
 
        return None
 
    def _fetch_from_krx(self) -> None:
        """KRX data.krx.co.kr API에서 전체 종목 리스트를 가져옵니다."""
        self._stocks.clear()
        self._code_map.clear()
 
        for market in [Market.KOSPI, Market.KOSDAQ]:
            stocks = self._fetch_market_stocks(market)
            for info in stocks:
                self._stocks[info.name] = info
                self._code_map[info.code] = info
 
            logger.info(
                "%s: %d개 종목 로드", market.display_name, len(stocks)
            )
 
    def _fetch_market_stocks(self, market: Market) -> list[StockInfo]:
        """특정 시장의 종목 리스트를 KRX API에서 가져옵니다."""
        headers = {
            "User-Agent": "Mozilla/5.0",
            "Referer": "http://data.krx.co.kr/contents/MDC/MDI/mdiLoader/index.cmd",
        }
 
        payload = {
            "bld": "dbms/MDC/STAT/standard/MDCSTAT01901",
            "locale": "ko_KR",
            "mktId": market.value,
            "share": "1",
            "csvxls_is498": "false",
        }
 
        try:
            response = requests.post(
                self.KRX_API_URL,
                data=payload,
                headers=headers,
                timeout=30,
            )
            response.raise_for_status()
            data = response.json()
        except requests.RequestException as e:
            logger.error("KRX API 호출 실패 (%s): %s", market.display_name, e)
            return []
 
        items = data.get("OutBlock_1", [])
        stocks = []
        for item in items:
            code = item.get("ISU_SRT_CD", "").strip()
            name = item.get("ISU_ABBRV", "").strip()
            sector = item.get("IDX_IND_NM", "").strip()
 
            if code and name and len(code) == 6 and code.isdigit():
                stocks.append(
                    StockInfo(code=code, name=name, market=market, sector=sector)
                )
 
        return stocks
 
    def _load_stocks_from_csv(self, path: Path) -> None:
        """CSV 캐시 파일에서 종목 데이터를 로드합니다."""
 
        df = pd.read_csv(path, dtype={"종목코드": str})
        #market_map = {"코스피": Market.KOSPI, "코스닥": Market.KOSDAQ, "코넥스": Market.KONEX}
        market_map = {"KOSPI": Market.KOSPI, "KOSDAQ": Market.KOSDAQ, "KOSDAQ GLOBAL": Market.KOSDAQ, "KONEX": Market.KONEX}
 
        for _, row in df.iterrows():
            market = market_map.get(row["시장구분"])
            #logger.info("Market %s", market)

            if market is None:
                continue
            info = StockInfo(
                code=row["단축코드"],
                name=row["한글 종목약명"],
                market=market,
                #sector=row.get("업종", ""),
            )
            self._stocks[info.name] = info
            self._code_map[info.code] = info
 
    def _load_etfs_from_csv(self, path: Path) -> None:
        """CSV 캐시 파일에서 종목 데이터를 로드합니다."""
        #self._stocks.clear()
        #self._code_map.clear()
 
        df = pd.read_csv(path, dtype={"종목코드": str})

        for _, row in df.iterrows():
            code = row["단축코드"]

            if code is None:
                continue
            info = StockInfo(
                code=code,
                name=row["한글종목명"],
                market=Market.KOSPI,
                #sector=row.get("업종", ""),
            )
            self._stocks[info.name] = info
            self._code_map[info.code] = info
 
    def _save_to_csv(self, path: Path) -> None:
        """종목 데이터를 CSV 파일로 저장합니다."""
        path.parent.mkdir(parents=True, exist_ok=True)
        df = self.to_dataframe()
        df.to_csv(path, index=False, encoding="utf-8-sig")