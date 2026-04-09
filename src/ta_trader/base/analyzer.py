"""
ta_trader/base/analyzer.py
분석기 기반 추상 클래스

모든 에이전트는 이 클래스를 상속합니다.
표준화된 인터페이스를 통해 파이프라인 결합이 가능합니다.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Generic, TypeVar

from ta_trader.data.fetcher import DataFetcher
from ta_trader.indicators.calculator import IndicatorCalculator
from ta_trader.indicators.swing_calculator import SwingIndicatorCalculator
from ta_trader.models import TradingStyle
from ta_trader.config.style_config import get_style_config
from ta_trader.utils.logger import get_logger

logger = get_logger(__name__)

OutputT = TypeVar("OutputT")

class BaseAnalyzer(ABC, Generic[OutputT]):
    """
    분석 기반 추상 클래스.

    각 에이전트는 단일 책임 원칙에 따라 하나의 역할만 수행합니다:
      - ShortTermAnalyzer:  1개월 단위 기술적 분석 트레이딩 시스템 → GrowthAnalysisResult
      - GrowthMomentumAnalyzer:  100% 상승 후보 발굴 6단계 분석 → TradingDecision
      - ValueInvestingAnalyzer:  가치 투자 5단계 분석 → ValueAnalysisResult
      - SwingTradingAnalyzer:  스윙 투자 6단계 분석 → SwingAnalysisResult
      - PositionTradingAnalyzer:  포지션 투자 7단계 분석 → PositionAnalysisResult
    """

    def __init__(
        self,
        ticker: str,
        name: str = None,
        period: str = "6mo",
        interval: str = "1d",
        trading_style: TradingStyle = TradingStyle.SWING,
        last_trading_day: str = None,
    ) -> None:
        self._logger = get_logger(self.__class__.__name__)

        self.ticker   = ticker
        self.trading_style = trading_style
        self.period = period
        self.interval = interval
        self._style_config = get_style_config(trading_style)
        self._calc: Optional[IndicatorCalculator] = None
        self._df: Optional[pd.DataFrame] = None
        self._info: dict = {}
        self._name: str = name or ticker
        # Short-Term : SHORT_DEFAULT_PERIOD = "6mo"
        # Value : VALUE_DEFAULT_PERIOD = "2y"
        # Growth : GROWTH_DEFAULT_PERIOD = "1y"

        self.last_trading_day = last_trading_day
        if not self.last_trading_day:
            self.last_trading_day = self._last_trading_day()

    @property
    def calculator(self) -> IndicatorCalculator | None:
        """analyze() 호출 후 사용 가능한 IndicatorCalculator"""
        return self._calc
    
    @property
    @abstractmethod
    def name(self) -> str:
        """에이전트 이름 (한국어)"""

    @property
    @abstractmethod
    def role(self) -> str:
        """에이전트 역할 설명 (한국어)"""

    @abstractmethod
    def analyze(self, df: pd.DataFrame | None = None) -> OutputT:
        """
        에이전트 메인 실행 로직.

        Args:
            input_data: 이전 에이전트의 출력물 또는 초기 입력

        Returns:
            다음 에이전트에게 전달할 출력물
        """

    @abstractmethod
    def analyze_with_llm(
        self, 
        df:          pd.DataFrame | None = None,
        provider:    str | None = None,
        api_key:     str | None = None,
        model:       str | None = None,
        recent_days: int = 10,
        stream:      bool = False,
    ) -> OutputT:
        """
        에이전트 메인 실행 로직.

        Args:
            input_data: 이전 에이전트의 출력물 또는 초기 입력

        Returns:
            다음 에이전트에게 전달할 출력물
        """

    def validate_input(self, input_data: InputT) -> bool:
        """입력 데이터 유효성 검증 (기본: 항상 True)"""
        return input_data is not None

    # ── 데이터 수집 ───────────────────────────────────────

    def _fetch_data(self, df: pd.DataFrame | None = None) -> None:
        """OHLCV + yfinance info 수집"""
        fetcher = DataFetcher(period=self.period, interval=self.interval)
        
        self._df = fetcher.fetch(self.ticker) if not df else df.copy()

        #self._calc = IndicatorCalculator(self._df)
        self._calc = SwingIndicatorCalculator(self._df)
        self._name, self._info = fetcher.info(self.ticker)

    def _last_trading_day(self) -> str | None:
        """ticker의 마지막 거래일 반환"""
        fetcher = DataFetcher(period=self.period, interval=self.interval)
        return fetcher.last_trading_day(self.ticker)

    def on_error(self, error: Exception, input_data: InputT) -> None:
        """에러 발생 시 훅 (기본: 로깅)"""
        self._logger.error(
            f"{self.name} 에러",
            error=str(error),
            agent=self.__class__.__name__,
        )

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}: {self.name}>"