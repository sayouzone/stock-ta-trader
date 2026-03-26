"""
WebSocket 라우터.
실시간 분석 결과 스트리밍 및 알림을 제공합니다.
"""

import asyncio
import json

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from ta_trader.infra.cache import cache
from ta_trader.interfaces.api.auth import verify_token
from ta_trader.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(tags=["websocket"])


class ConnectionManager:
    """WebSocket 연결 관리자."""

    def __init__(self) -> None:
        self._active: list[WebSocket] = []

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self._active.append(websocket)
        logger.info("WebSocket connected. Active: %d", len(self._active))

    def disconnect(self, websocket: WebSocket) -> None:
        self._active.remove(websocket)
        logger.info("WebSocket disconnected. Active: %d", len(self._active))

    async def broadcast(self, message: dict) -> None:
        disconnected = []
        for ws in self._active:
            try:
                await ws.send_json(message)
            except Exception:
                disconnected.append(ws)
        for ws in disconnected:
            self._active.remove(ws)


manager = ConnectionManager()


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket 엔드포인트.

    연결 시 token 쿼리 파라미터로 인증:
        ws://host/api/v1/ws?token=<jwt_token>

    수신 메시지 포맷:
        {"type": "subscribe", "channel": "analysis_completed"}
        {"type": "ping"}

    발신 메시지 포맷:
        {"type": "analysis_completed", "data": {...}}
        {"type": "pong"}
    """
    # 인증 확인
    token = websocket.query_params.get("token")
    if not token:
        await websocket.close(code=4001, reason="Missing token")
        return

    try:
        verify_token(token)
    except Exception:
        await websocket.close(code=4001, reason="Invalid token")
        return

    await manager.connect(websocket)

    # Redis pub/sub 리스너 시작
    listener_task = asyncio.create_task(
        _redis_listener(websocket)
    )

    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)

            if message.get("type") == "ping":
                await websocket.send_json({"type": "pong"})

    except WebSocketDisconnect:
        manager.disconnect(websocket)
        listener_task.cancel()
    except Exception as e:
        logger.error("WebSocket error: %s", e)
        manager.disconnect(websocket)
        listener_task.cancel()


async def _redis_listener(websocket: WebSocket) -> None:
    """Redis pub/sub → WebSocket 브릿지."""
    try:
        pubsub = await cache.subscribe("analysis_completed")
        async for message in pubsub.listen():
            if message["type"] == "message":
                data = json.loads(message["data"])
                await websocket.send_json({
                    "type": "analysis_completed",
                    "data": data,
                })
    except asyncio.CancelledError:
        pass
    except Exception as e:
        logger.error("Redis listener error: %s", e)
