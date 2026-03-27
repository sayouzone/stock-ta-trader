"""
OpenClaw Gateway WebSocket 클라이언트 (선택적 고급 기능)
실시간 스트리밍 응답이 필요한 경우 사용합니다.
REST 방식으로 충분하면 main.py의 OpenClawClient를 사용하세요.
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import AsyncIterator

import websockets
from websockets.exceptions import ConnectionClosed

log = logging.getLogger("openclaw_kakao.ws")


class OpenClawWSClient:
    """
    OpenClaw Gateway WebSocket 클라이언트.
    ws://localhost:18789 에 연결하여 에이전트와 실시간 통신.
    """

    def __init__(
        self,
        gateway_url: str = "ws://localhost:18789",
        token: str = "",
        reconnect_delay: float = 3.0,
    ) -> None:
        self._url = gateway_url.replace("http://", "ws://").replace("https://", "wss://")
        self._token = token
        self._reconnect_delay = reconnect_delay
        self._ws = None
        self._lock = asyncio.Lock()
        self._pending: dict[str, asyncio.Future] = {}

    async def connect(self) -> None:
        headers = {}
        if self._token:
            headers["Authorization"] = f"Bearer {self._token}"
        self._ws = await websockets.connect(self._url, extra_headers=headers)
        log.info("OpenClaw WS 연결됨: %s", self._url)
        asyncio.create_task(self._receive_loop())

    async def _receive_loop(self) -> None:
        try:
            async for raw in self._ws:
                try:
                    msg = json.loads(raw)
                    req_id = msg.get("requestId") or msg.get("id")
                    if req_id and req_id in self._pending:
                        self._pending[req_id].set_result(msg)
                except Exception as e:
                    log.error("WS 메시지 파싱 오류: %s", e)
        except ConnectionClosed:
            log.warning("OpenClaw WS 연결 끊김, %ds 후 재연결...", self._reconnect_delay)
            await asyncio.sleep(self._reconnect_delay)
            await self.connect()

    async def send_message(
        self,
        session_id: str,
        text: str,
        timeout: float = 25.0,
    ) -> str:
        """에이전트에 메시지를 보내고 응답을 대기합니다."""
        import uuid

        req_id = str(uuid.uuid4())
        future: asyncio.Future = asyncio.get_event_loop().create_future()
        self._pending[req_id] = future

        payload = {
            "type": "message",
            "requestId": req_id,
            "sessionId": session_id,
            "text": text,
        }

        async with self._lock:
            await self._ws.send(json.dumps(payload))

        try:
            response = await asyncio.wait_for(future, timeout=timeout)
            return response.get("text") or response.get("message", {}).get("text", "")
        except asyncio.TimeoutError:
            raise TimeoutError(f"OpenClaw 응답 타임아웃 ({timeout}초)")
        finally:
            self._pending.pop(req_id, None)

    async def stream_message(
        self,
        session_id: str,
        text: str,
    ) -> AsyncIterator[str]:
        """스트리밍 응답을 비동기 제너레이터로 반환합니다."""
        import uuid

        req_id = str(uuid.uuid4())
        queue: asyncio.Queue = asyncio.Queue()

        async def _handle(msg: dict) -> None:
            if msg.get("type") == "chunk":
                await queue.put(msg.get("text", ""))
            elif msg.get("type") in ("done", "end"):
                await queue.put(None)  # 종료 신호

        self._pending[req_id] = queue

        payload = {
            "type": "stream",
            "requestId": req_id,
            "sessionId": session_id,
            "text": text,
        }
        await self._ws.send(json.dumps(payload))

        try:
            while True:
                chunk = await asyncio.wait_for(queue.get(), timeout=30.0)
                if chunk is None:
                    break
                yield chunk
        finally:
            self._pending.pop(req_id, None)

    async def close(self) -> None:
        if self._ws:
            await self._ws.close()
