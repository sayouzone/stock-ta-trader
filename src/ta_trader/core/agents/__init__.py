# ta_trader/core/agents/__init__.py
"""
Core agent interfaces.
These are stubs representing the existing stock-ta-trader Four Agent System.
Replace with actual imports from your existing codebase:

    from stock_ta_trader.agents import DataAgent, StrategyAgent, RiskAgent, ExecutionAgent
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class AgentStatus(str, Enum):
    IDLE = "idle"
    RUNNING = "running"
    COMPLETED = "completed"
    ERROR = "error"


@dataclass
class AgentResult:
    agent_name: str
    status: AgentStatus
    data: dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
    error: str | None = None


class DataAgent:
    """시장 데이터 수집 에이전트 (yfinance, DART, KIS, FnGuide)."""

    async def fetch_market_data(self, ticker: str) -> AgentResult:
        # TODO: 기존 DataAgent.fetch_market_data() 호출
        raise NotImplementedError("Connect to existing DataAgent")

    async def fetch_fundamental_data(self, ticker: str) -> AgentResult:
        raise NotImplementedError("Connect to existing DataAgent")


class StrategyAgent:
    """매매 전략 분석 에이전트 (기술적 지표 + LLM 분석)."""

    async def analyze_swing(self, ticker: str) -> AgentResult:
        # TODO: 기존 SwingTradingAnalyzer 호출
        raise NotImplementedError("Connect to existing StrategyAgent")

    async def analyze_growth_momentum(self, ticker: str) -> AgentResult:
        # TODO: 기존 GrowthMomentumAnalyzer 호출
        raise NotImplementedError("Connect to existing StrategyAgent")


class RiskAgent:
    """리스크 평가 에이전트 (포지션 사이징, 손절 전략)."""

    async def evaluate_risk(self, ticker: str, strategy_result: AgentResult) -> AgentResult:
        raise NotImplementedError("Connect to existing RiskAgent")


class ExecutionAgent:
    """주문 실행 에이전트 (KIS API 연동)."""

    async def execute_order(self, order_params: dict[str, Any]) -> AgentResult:
        raise NotImplementedError("Connect to existing ExecutionAgent")
