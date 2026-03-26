# ta_trader/core/orchestrator.py
"""
Agent Orchestrator stub.
Replace with actual import:
    from stock_ta_trader.orchestrator import AgentOrchestrator
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

from ta_trader.core.agents import AgentResult, DataAgent, ExecutionAgent, RiskAgent, StrategyAgent


class AnalysisType(str, Enum):
    SWING = "swing"
    GROWTH_MOMENTUM = "growth_momentum"
    FULL = "full"


@dataclass
class OrchestratorResult:
    analysis_type: AnalysisType
    ticker: str
    agents_results: dict[str, AgentResult] = field(default_factory=dict)
    recommendation: dict[str, Any] = field(default_factory=dict)
    score: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)


class AgentOrchestrator:
    """
    Four Agent System 조율자.
    DataAgent → StrategyAgent → RiskAgent → ExecutionAgent 순서로 실행.
    """

    def __init__(self) -> None:
        self.data_agent = DataAgent()
        self.strategy_agent = StrategyAgent()
        self.risk_agent = RiskAgent()
        self.execution_agent = ExecutionAgent()

    async def run_analysis(
        self,
        ticker: str,
        analysis_type: AnalysisType = AnalysisType.SWING,
    ) -> OrchestratorResult:
        """
        전체 분석 파이프라인 실행.
        TODO: 기존 AgentOrchestrator.run() 로직으로 교체
        """
        raise NotImplementedError("Connect to existing AgentOrchestrator")

    async def run_screening(
        self,
        market: str = "KRX",
        top_n: int = 10,
    ) -> list[OrchestratorResult]:
        """
        전체 시장 스크리닝 후 상위 N개 종목 반환.
        TODO: 기존 screening 로직 연결
        """
        raise NotImplementedError("Connect to existing screening logic")

    async def get_recommendations(self) -> list[OrchestratorResult]:
        """
        추천 엔진 실행 (6차원 평가).
        TODO: 기존 recommendation engine 연결
        """
        raise NotImplementedError("Connect to existing recommendation engine")
