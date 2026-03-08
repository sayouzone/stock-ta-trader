"""
ta_trader/agents/orchestrator.py
Agent Orchestrator — 4-에이전트 파이프라인 총괄 지휘

파이프라인:
  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐    ┌──────────────┐
  │  Data Agent   │ →  │ Strategy     │ →  │ Risk Agent   │ →  │ Execution    │
  │  (눈과 귀)   │    │ Agent (브레인)│    │ (브레이크)   │    │ Agent (행동) │
  └──────────────┘    └──────────────┘    └──────────────┘    └──────────────┘
       데이터 수집         전략 수립           리스크 검증         주문 체결
       지표 연산           시그널 생성         포지션 사이징       체결 관리
       국면 판별           스크리닝            승인/거부(Veto)     결과 로깅

사용 예:
    # 단일 종목 전체 파이프라인
    orchestrator = AgentOrchestrator()
    result = orchestrator.run("AAPL")

    # 분석만 (Data + Strategy)
    result = orchestrator.analyze_only("005930.KS")

    # 복수 종목 스크리닝
    results = orchestrator.screen(["AAPL", "NVDA", "TSLA"])
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Optional

from ta_trader.agents.data_agent import DataAgent, DataAgentInput
from ta_trader.agents.execution_agent import (
    DryRunBackend, ExecutionAgent, ExecutionBackend, ExecutionConfig,
)
from ta_trader.models.agent_models import (
    ExecutionResult, MarketDataReport, PipelineResult,
    RiskApproval, StrategyReport, TradeSignal,
)
from ta_trader.agents.risk_agent import RiskAgent, RiskConfig
from ta_trader.agents.strategy_agent import StrategyAgent
from ta_trader.models import TradingDecision, TradingStyle
from ta_trader.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class OrchestratorConfig:
    """오케스트레이터 설정"""
    # 기본 트레이딩 스타일
    trading_style: TradingStyle = TradingStyle.SWING

    # 데이터 수집 설정
    period: str = "6mo"
    interval: str = "1d"
    include_fundamentals: bool = True

    # LLM 설정
    use_llm: bool = False
    llm_provider: Optional[str] = None
    llm_model: Optional[str] = None
    llm_stream: bool = False
    include_sentiment: bool = False

    # 리스크 설정
    risk_config: Optional[RiskConfig] = None

    # 체결 설정
    execution_config: Optional[ExecutionConfig] = None
    execution_backend: Optional[ExecutionBackend] = None

    # 파이프라인 제어
    execute_trades: bool = False       # True이면 Execution Agent까지 실행
    stop_on_veto: bool = True          # Veto 시 파이프라인 중단


class AgentOrchestrator:
    """
    4-에이전트 파이프라인 총괄 지휘관.

    각 에이전트를 순차적으로 실행하고, 이전 에이전트의 출력물을
    다음 에이전트에게 전달합니다.
    """

    def __init__(self, config: Optional[OrchestratorConfig] = None) -> None:
        self.config = config or OrchestratorConfig()

        # 에이전트 초기화
        self._data_agent = DataAgent()
        self._strategy_agent = StrategyAgent(
            trading_style=self.config.trading_style,
            use_llm=self.config.use_llm,
            llm_provider=self.config.llm_provider,
            llm_model=self.config.llm_model,
            llm_stream=self.config.llm_stream,
        )
        self._risk_agent = RiskAgent(
            config=self.config.risk_config,
        )
        self._execution_agent = ExecutionAgent(
            backend=self.config.execution_backend,
            config=self.config.execution_config,
        )

    # ── 전체 파이프라인 실행 ─────────────────────────────

    def run(self, ticker: str) -> PipelineResult:
        """
        전체 4-에이전트 파이프라인 실행

        Data → Strategy → Risk → Execution(선택)

        Args:
            ticker: 종목 코드

        Returns:
            PipelineResult: 모든 에이전트 출력물 포함
        """
        start = time.time()
        result = PipelineResult(ticker=ticker, date="")

        try:
            # ── Stage 1: Data & Analysis Agent ────────
            market_data = self._run_data_agent(ticker)
            result.market_data = market_data
            result.date = market_data.date

            # ── Stage 2: Strategy & Decision Agent ────
            trade_signal = self._run_strategy_agent(market_data)
            result.trade_signal = trade_signal

            # ── Stage 3: Risk Management Agent ────────
            risk_approval = self._run_risk_agent(trade_signal)
            result.risk_approval = risk_approval

            # ── Stage 4: Execution Agent (선택적) ─────
            if self.config.execute_trades:
                execution = self._run_execution_agent(risk_approval)
                result.execution_result = execution

            # ── 레거시 호환: TradingDecision 변환 ─────
            result.trading_decision = result.to_trading_decision()

        except Exception as e:
            result.errors.append(str(e))
            logger.error("파이프라인 실패", ticker=ticker, error=str(e))
            raise

        result.pipeline_duration_ms = round((time.time() - start) * 1000, 2)

        logger.info(
            "파이프라인 완료",
            ticker=ticker,
            duration_ms=result.pipeline_duration_ms,
            approved=result.is_approved,
            executed=result.is_executed,
        )

        return result

    def analyze_only(self, ticker: str) -> PipelineResult:
        """
        분석만 실행 (Data + Strategy 에이전트만)

        기존 ShortTermAnalyzer.analyze()와 동등한 기능.
        리스크 검증과 체결은 수행하지 않습니다.

        Args:
            ticker: 종목 코드

        Returns:
            PipelineResult: 마켓 데이터 + 트레이드 시그널
        """
        start = time.time()
        result = PipelineResult(ticker=ticker, date="")

        market_data = self._run_data_agent(ticker)
        result.market_data = market_data
        result.date = market_data.date

        trade_signal = self._run_strategy_agent(market_data)
        result.trade_signal = trade_signal

        result.trading_decision = result.to_trading_decision()
        result.pipeline_duration_ms = round((time.time() - start) * 1000, 2)

        return result

    def screen(
        self,
        tickers: list[str],
        top_n: int = 0,
    ) -> list[PipelineResult]:
        """
        복수 종목 스크리닝 파이프라인

        Args:
            tickers: 종목 코드 리스트
            top_n: 상위 N개만 반환 (0=전체)

        Returns:
            PipelineResult 리스트 (점수 내림차순 정렬)
        """
        logger.info("배치 스크리닝 시작", count=len(tickers))

        results = []
        for ticker in tickers:
            try:
                result = self.run(ticker)
                results.append(result)
            except Exception as e:
                logger.error(f"[{ticker}] 스크리닝 실패: {e}")

        # 점수 기준 정렬
        results.sort(
            key=lambda r: (
                r.trade_signal.composite_score if r.trade_signal else -999
            ),
            reverse=True,
        )

        if top_n > 0:
            results = results[:top_n]

        return results

    # ── 레거시 호환 메서드 ───────────────────────────────

    def to_trading_decision(self, result: PipelineResult) -> Optional[TradingDecision]:
        """PipelineResult → TradingDecision 변환 (하위 호환)"""
        return result.to_trading_decision()

    # ── 개별 에이전트 실행 ───────────────────────────────

    def _run_data_agent(self, ticker: str) -> MarketDataReport:
        """Data & Analysis Agent 실행"""
        input_data = DataAgentInput(
            ticker=ticker,
            period=self.config.period,
            interval=self.config.interval,
            trading_style=self.config.trading_style,
            include_fundamentals=self.config.include_fundamentals,
            include_sentiment=self.config.include_sentiment,
            llm_provider=self.config.llm_provider,
            llm_model=self.config.llm_model,
        )
        return self._data_agent.execute(input_data)

    def _run_strategy_agent(
        self,
        market_data: MarketDataReport,
    ) -> TradeSignal:
        """Strategy & Decision Agent 실행"""
        return self._strategy_agent.execute(market_data)

    def _run_risk_agent(
        self,
        trade_signal: TradeSignal,
    ) -> RiskApproval:
        """Risk Management Agent 실행"""
        return self._risk_agent.execute(trade_signal)

    def _run_execution_agent(
        self,
        risk_approval: RiskApproval,
    ) -> ExecutionResult:
        """Execution Agent 실행"""
        return self._execution_agent.execute(risk_approval)

    # ── 에이전트 직접 접근 (상태 변경 등) ────────────────

    @property
    def data_agent(self) -> DataAgent:
        return self._data_agent

    @property
    def strategy_agent(self) -> StrategyAgent:
        return self._strategy_agent

    @property
    def risk_agent(self) -> RiskAgent:
        return self._risk_agent

    @property
    def execution_agent(self) -> ExecutionAgent:
        return self._execution_agent
