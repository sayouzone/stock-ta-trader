"""
분석 API 라우터.
종목 분석, 스크리닝, 추천 엔드포인트를 제공합니다.
"""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status

from ta_trader.core.orchestrator import AnalysisType
from ta_trader.interfaces.api.auth import get_current_user
from ta_trader.interfaces.api.schemas import (
    AnalysisJobResponse,
    AnalysisRequest,
    AnalysisResultResponse,
    ScreeningRequest,
    ScreeningResponse,
)
from ta_trader.services.agent_service import agent_service

router = APIRouter(prefix="/analysis", tags=["analysis"])


@router.post("/", response_model=AnalysisJobResponse, status_code=status.HTTP_202_ACCEPTED)
async def submit_analysis(
    request: AnalysisRequest,
    _user: str = Depends(get_current_user),
):
    """
    종목 분석 작업 제출.
    비동기로 실행되며, job_id로 결과를 조회할 수 있습니다.
    """
    analysis_type = AnalysisType(request.analysis_type)
    job = await agent_service.submit_analysis(
        ticker=request.ticker,
        analysis_type=analysis_type,
    )
    return AnalysisJobResponse(
        job_id=job.job_id,
        ticker=job.ticker,
        analysis_type=job.analysis_type.value,
        status=job.status.value,
        created_at=job.created_at,
    )


@router.get("/jobs/{job_id}", response_model=AnalysisResultResponse)
async def get_analysis_result(
    job_id: str,
    _user: str = Depends(get_current_user),
):
    """분석 작업 결과 조회."""
    job = agent_service.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")

    result_data = None
    score = None
    if job.result:
        result_data = getattr(job.result, "recommendation", None) or {}
        score = getattr(job.result, "score", None)

    return AnalysisResultResponse(
        job_id=job.job_id,
        ticker=job.ticker,
        analysis_type=job.analysis_type.value,
        status=job.status.value,
        score=score,
        result=result_data,
        error=job.error,
        created_at=job.created_at,
        completed_at=job.completed_at,
    )


@router.post("/screening", response_model=ScreeningResponse)
async def run_screening(
    request: ScreeningRequest,
    _user: str = Depends(get_current_user),
):
    """시장 스크리닝 실행."""
    results = await agent_service.run_screening(
        market=request.market,
        top_n=request.top_n,
    )
    return ScreeningResponse(
        market=request.market,
        count=len(results),
        results=results,
    )


@router.get("/recommendations")
async def get_recommendations(
    _user: str = Depends(get_current_user),
):
    """추천 종목 조회."""
    results = await agent_service.get_recommendations()
    return {"recommendations": results, "timestamp": datetime.now()}
