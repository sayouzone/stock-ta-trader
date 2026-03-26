"""
API 요청/응답 스키마 (Pydantic v2).
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


# ── Analysis ─────────────────────────────────────────────

class AnalysisRequest(BaseModel):
    ticker: str = Field(..., min_length=1, max_length=20, examples=["005930", "AAPL"])
    analysis_type: str = Field(
        default="swing",
        pattern="^(swing|growth_momentum|full)$",
    )


class AnalysisJobResponse(BaseModel):
    job_id: str
    ticker: str
    analysis_type: str
    status: str
    created_at: datetime


class AnalysisResultResponse(BaseModel):
    job_id: str
    ticker: str
    analysis_type: str
    status: str
    score: float | None = None
    result: dict[str, Any] | None = None
    error: str | None = None
    created_at: datetime
    completed_at: datetime | None = None


# ── Screening ────────────────────────────────────────────

class ScreeningRequest(BaseModel):
    market: str = Field(default="KRX", pattern="^(KRX|NASDAQ|NYSE)$")
    top_n: int = Field(default=10, ge=1, le=50)


class ScreeningResult(BaseModel):
    ticker: str
    score: float
    analysis_type: str
    recommendation: dict[str, Any] = {}


class ScreeningResponse(BaseModel):
    market: str
    count: int
    results: list[ScreeningResult]


# ── Alerts ───────────────────────────────────────────────

class AlertRequest(BaseModel):
    ticker: str
    title: str = Field(..., max_length=100)
    message: str = Field(..., max_length=1000)
    priority: int = Field(default=3, ge=1, le=5)
    channels: list[str] | None = None


class AlertResponse(BaseModel):
    results: dict[str, bool]
    sent_at: datetime


# ── Watchlist ────────────────────────────────────────────

class WatchlistItem(BaseModel):
    ticker: str
    name: str | None = None
    alert_conditions: dict[str, Any] = {}


class WatchlistResponse(BaseModel):
    items: list[WatchlistItem]
    count: int


# ── Auth ─────────────────────────────────────────────────

class TokenRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


# ── Health ───────────────────────────────────────────────

class HealthResponse(BaseModel):
    status: str
    version: str
    redis_connected: bool
    db_connected: bool
    scheduler_running: bool
    timestamp: datetime
