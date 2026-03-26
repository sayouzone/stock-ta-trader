"""
알림 API 라우터.
알림 발송 및 워치리스트 관리 엔드포인트를 제공합니다.
"""

from datetime import datetime

from fastapi import APIRouter, Depends

from ta_trader.interfaces.api.auth import get_current_user
from ta_trader.interfaces.api.schemas import AlertRequest, AlertResponse
from ta_trader.services.notification import AlertPayload, NotificationService

router = APIRouter(prefix="/alerts", tags=["alerts"])

# 의존성 주입으로 교체 가능
_notification_service: NotificationService | None = None


def set_notification_service(service: NotificationService) -> None:
    global _notification_service
    _notification_service = service


def get_notification_service() -> NotificationService:
    if _notification_service is None:
        raise RuntimeError("NotificationService not initialized")
    return _notification_service


@router.post("/send", response_model=AlertResponse)
async def send_alert(
    request: AlertRequest,
    _user: str = Depends(get_current_user),
):
    """수동 알림 발송."""
    service = get_notification_service()
    payload = AlertPayload(
        ticker=request.ticker,
        title=request.title,
        message=request.message,
        priority=request.priority,
        channels=request.channels,
    )
    results = await service.send_alert(payload)
    return AlertResponse(results=results, sent_at=datetime.now())


@router.post("/test")
async def test_alert(
    _user: str = Depends(get_current_user),
):
    """테스트 알림 발송 (연결 확인용)."""
    service = get_notification_service()
    payload = AlertPayload(
        ticker="TEST",
        title="연결 테스트",
        message="Stock TA Trader 알림 시스템이 정상 작동 중입니다.",
        priority=1,
    )
    results = await service.send_alert(payload)
    return {"results": results, "sent_at": datetime.now()}
