"""
ta_trader/agents/
4-에이전트 트레이딩 시스템

에이전트 파이프라인:
  DataAgent → StrategyAgent → RiskAgent → ExecutionAgent

각 에이전트는 단일 책임 원칙에 따라 독립적으로 동작하며,
AgentOrchestrator가 파이프라인을 총괄합니다.
"""

from ta_trader.agents.data_agent import DataAgent, DataAgentInput
from ta_trader.agents.execution_agent import (
    DryRunBackend,
    ExecutionAgent,
    ExecutionBackend,
    ExecutionConfig,
)
from ta_trader.models.agents_models import (
    ExecutionResult,
    MarketDataReport,
    OrderSide,
    OrderStatus,
    OrderType,
    PipelineResult,
    PositionSize,
    RiskApproval,
    StrategyReport,
    TradeSignal,
    VetoReason,
)
from ta_trader.agents.orchestrator import AgentOrchestrator, OrchestratorConfig
from ta_trader.agents.risk_agent import RiskAgent, RiskConfig
from ta_trader.agents.strategy_agent import StrategyAgent

__all__ = [
    # 에이전트
    "DataAgent",
    "DataAgentInput",
    "StrategyAgent",
    "RiskAgent",
    "RiskConfig",
    "ExecutionAgent",
    "ExecutionConfig",
    "ExecutionBackend",
    "DryRunBackend",
    # 오케스트레이터
    "AgentOrchestrator",
    "OrchestratorConfig",
    # 데이터 모델
    "MarketDataReport",
    "TradeSignal",
    "StrategyReport",
    "RiskApproval",
    "PositionSize",
    "ExecutionResult",
    "PipelineResult",
    # 열거형
    "OrderSide",
    "OrderType",
    "OrderStatus",
    "VetoReason",
]
