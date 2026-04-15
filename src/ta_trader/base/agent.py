"""
ta_trader/base/agent.py
에이전트 기반 추상 클래스

모든 에이전트는 이 클래스를 상속합니다.
표준화된 인터페이스를 통해 파이프라인 결합이 가능합니다.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Generic, TypeVar

from ta_trader.data.fetcher import DataFetcher
from ta_trader.indicators.calculator import IndicatorCalculator
from ta_trader.indicators.swing_calculator import SwingIndicatorCalculator
from ta_trader.utils.logger import get_logger

InputT = TypeVar("InputT")
OutputT = TypeVar("OutputT")


class BaseAgent(ABC, Generic[InputT, OutputT]):
    """
    에이전트 기반 추상 클래스.

    각 에이전트는 단일 책임 원칙에 따라 하나의 역할만 수행합니다:
      - DataAgent:      데이터 수집 + 지표 연산 → MarketDataReport
      - StrategyAgent:  전략 수립 + 시그널 생성 → TradeSignal
      - RiskAgent:      리스크 평가 + 승인/거부 → RiskApproval
      - ExecutionAgent: 주문 실행 + 체결 관리   → ExecutionResult
    """

    def __init__(self) -> None:
        self._logger = get_logger(self.__class__.__name__)
        self._calc: Optional[IndicatorCalculator] = None
        self._df: Optional[pd.DataFrame] = None
        self._info: dict = {}
        self._name: str = None

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
    def execute(self, input_data: InputT) -> OutputT:
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

    def _fetch_data(self, ticker: str, period: str, interval: str, df: pd.DataFrame | None = None) -> None:
        """OHLCV + yfinance info 수집"""
        fetcher = DataFetcher(period=period, interval=interval)
        self._df = fetcher.fetch(ticker) if not df else df.copy()

        #self._calc = IndicatorCalculator(self._df)
        self._calc = SwingIndicatorCalculator(self._df)
        self._name, self._info = fetcher.info(ticker)

    def on_error(self, error: Exception, input_data: InputT) -> None:
        """에러 발생 시 훅 (기본: 로깅)"""
        self._logger.error(
            f"{self.name} 에러",
            error=str(error),
            agent=self.__class__.__name__,
        )

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}: {self.name}>"
