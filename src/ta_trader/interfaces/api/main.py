"""
Stock TA Trader — Mobile API Server.

기존 Four Agent System 코어를 REST/WebSocket API로 노출합니다.
"""

from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from ta_trader.config import get_settings
from ta_trader.infra.cache import cache
from ta_trader.infra.db import init_db
from ta_trader.interfaces.api.auth import create_access_token
from ta_trader.interfaces.api.routers import alerts_router, analysis_router, ws_router
from ta_trader.interfaces.api.routers.alerts import set_notification_service
from ta_trader.interfaces.api.schemas import HealthResponse, TokenRequest, TokenResponse
from ta_trader.services.notification import create_notification_service
from ta_trader.services.scheduler import SchedulerService
from ta_trader.utils.logger import get_logger

logger = get_logger(__name__)

# ── Globals ──────────────────────────────────────────────
scheduler_service: SchedulerService | None = None


# ── Lifespan ─────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """앱 시작/종료 시 리소스 관리."""
    global scheduler_service
    settings = get_settings()

    # Startup
    logger.info("Starting Stock TA Trader API [%s]", settings.app_env)

    # Redis 연결
    await cache.connect()

    # DB 초기화
    await init_db()

    # 알림 서비스 등록
    notification_service = create_notification_service()
    set_notification_service(notification_service)

    # 스케줄러 시작
    scheduler_service = SchedulerService(notification_service)
    scheduler_service.start()

    logger.info("All services started successfully")
    yield

    # Shutdown
    logger.info("Shutting down...")
    if scheduler_service:
        scheduler_service.stop()
    await cache.disconnect()
    logger.info("Shutdown complete")


# ── App ──────────────────────────────────────────────────

def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title=settings.app_name,
        version=settings.api_version,
        docs_url="/docs" if settings.debug else None,
        redoc_url="/redoc" if settings.debug else None,
        lifespan=lifespan,
    )

    # CORS (모바일 PWA 접근 허용)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"] if settings.debug else ["https://your-domain.com"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 라우터 등록
    prefix = settings.api_prefix
    app.include_router(analysis_router, prefix=prefix)
    app.include_router(alerts_router, prefix=prefix)
    app.include_router(ws_router, prefix=prefix)

    # ── Root & Utility Endpoints ─────────────────────────

    @app.get("/")
    async def root():
        return {
            "name": settings.app_name,
            "version": settings.api_version,
            "docs": "/docs" if settings.debug else "disabled",
        }

    @app.get("/health", response_model=HealthResponse)
    async def health_check():
        redis_ok = False
        try:
            await cache.client.ping()
            redis_ok = True
        except Exception:
            pass

        return HealthResponse(
            status="ok",
            version=settings.api_version,
            redis_connected=redis_ok,
            db_connected=True,  # TODO: 실제 DB ping
            scheduler_running=scheduler_service is not None,
            timestamp=datetime.now(),
        )

    @app.post("/auth/token", response_model=TokenResponse)
    async def login(request: TokenRequest):
        """
        토큰 발급.
        개인용이므로 환경변수의 고정 credentials와 비교합니다.
        프로덕션에서는 적절한 인증 체계로 교체하세요.
        """
        # TODO: 실제 인증 로직으로 교체
        if request.username == "admin" and request.password == "changeme":
            token, expires_in = create_access_token(subject=request.username)
            return TokenResponse(
                access_token=token,
                expires_in=expires_in,
            )
        from fastapi import HTTPException, status
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )

    return app


app = create_app()
