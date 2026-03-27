"""
Agent Service: Orchestrator를 비동기 API 레이어로 감싸는 서비스.
분석 작업을 백그라운드에서 실행하고, 결과를 캐싱합니다.
"""

import asyncio
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

#from ta_trader.core.orchestrator import AgentOrchestrator, AnalysisType, OrchestratorResult
from ta_trader.agents.orchestrator import AgentOrchestrator, OrchestratorConfig
from ta_trader.agents.risk import RiskConfig
from ta_trader.formatters.agent import format_pipeline_result

from ta_trader.infra.cache import cache
from ta_trader.utils.logger import get_logger

logger = get_logger(__name__)


class JobStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class AnalysisJob:
    job_id: str
    ticker: str
    trading_style: TradingStyle
    status: JobStatus = JobStatus.PENDING
    result: PipelineResult | None = None
    error: str | None = None
    created_at: datetime = field(default_factory=datetime.now)
    completed_at: datetime | None = None


class AgentService:
    """
    에이전트 오케스트레이터를 감싸는 서비스 레이어.

    - 비동기 작업 큐 (job_id로 추적)
    - Redis 캐싱 (중복 분석 방지)
    - 결과 히스토리 저장
    """

    def __init__(self) -> None:
        self._orchestrator = None
        self._jobs: dict[str, AnalysisJob] = {}

    async def submit_analysis(
        self,
        ticker: str,
        period: str = "1y",
        interval: str = "1d",
        trading_style: TradingStyle = TradingStyle.SWING,
        capital: float = 10_000_000,
        risk_pct: float = 2.0,
        sizing: str = "fixed_ratio",
        llm: bool = False,
        llm_stream: bool = False,
        llm_provider: str = None,
        llm_model: str = None,
    ) -> AnalysisJob:
        """분석 작업 제출 → 즉시 job_id 반환."""
        job_id = str(uuid.uuid4())[:8]
        job = AnalysisJob(
            job_id=job_id,
            ticker=ticker.upper(),
            trading_style=trading_style,
        )
        self._jobs[job_id] = job

        # 캐시 확인
        cache_key = f"analysis:{ticker.upper()}:{analysis_type.value}"
        cached = await cache.get(cache_key)
        if cached:
            job.status = JobStatus.COMPLETED
            job.result = cached
            job.completed_at = datetime.now()
            return job

        risk_cfg = RiskConfig(
            total_capital=capital,
            max_risk_per_trade_pct=risk_pct / 100,
            sizing_method=sizing,
        )

        config = OrchestratorConfig(
            trading_style=trading_style,
            period=period,
            interval=interval,
            use_llm=(llm or llm_stream),
            llm_provider=llm_provider,
            llm_model=llm_model,
            llm_stream=llm_stream,
            risk_config=risk_cfg,
        )

        self._orchestrator = AgentOrchestrator(config=config)

        # 백그라운드 실행
        asyncio.create_task(self._run_analysis(job, cache_key))
        return job
        
    async def _run_analysis(self, job: AnalysisJob, cache_key: str) -> None:
        """백그라운드에서 분석 실행."""
        job.status = JobStatus.RUNNING
        try:
            result = await self._orchestrator.run(ticker=job.ticker)

            job.result = result
            job.status = JobStatus.COMPLETED
            job.completed_at = datetime.now()

            output = format_pipeline_result(result)

            # 결과 캐싱
            await cache.set(cache_key, result.__dict__)

            # Redis pub/sub로 완료 알림
            await cache.publish("analysis_completed", {
                "job_id": job.job_id,
                "ticker": job.ticker,
                "score": result.score,
            })

            logger.info("Analysis completed: %s %s", job.ticker, job.job_id)

        except Exception as e:
            job.status = JobStatus.FAILED
            job.error = str(e)
            logger.error(f"❌ 분석 실패: {job.ticker} {job.job_id} - {e}")

    def get_job(self, job_id: str) -> AnalysisJob | None:
        return self._jobs.get(job_id)

    async def get_recommendations(self, top_n: int = 10) -> list[dict[str, Any]]:
        """추천 종목 조회 (캐시 우선)."""
        cache_key = "recommendations:latest"
        return await cache.get_or_set(
            cache_key,
            factory=self._orchestrator.get_recommendations,
            ttl=1800,  # 30분
        )

    async def run_screening(
        self,
        market: str = "KRX",
        top_n: int = 10,
    ) -> list[dict[str, Any]]:
        """시장 스크리닝 (캐시 우선)."""
        cache_key = f"screening:{market}:{top_n}"
        return await cache.get_or_set(
            cache_key,
            factory=lambda: self._orchestrator.run_screening(market, top_n),
            ttl=3600,
        )


# Singleton
agent_service = AgentService()
