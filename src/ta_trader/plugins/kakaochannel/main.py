"""
OpenClaw KakaoTalk Channel Plugin (Python Relay Server)
========================================================
카카오 i 오픈빌더 ↔ OpenClaw Gateway 릴레이 서버

아키텍처:
  [카카오 i 오픈빌더] --webhook POST--> [이 서버] --REST/WS--> [OpenClaw Gateway :18789]

실행:
  pip install fastapi uvicorn httpx python-dotenv
  uvicorn main:app --host 0.0.0.0 --port 8000 --reload
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import os
import secrets
import time
from contextlib import asynccontextmanager
from typing import Any

import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, Header, HTTPException, Request, status
from fastapi.responses import JSONResponse

load_dotenv()

# ---------------------------------------------------------------------------
# 설정
# ---------------------------------------------------------------------------
OPENCLAW_GATEWAY_URL = os.getenv("OPENCLAW_GATEWAY_URL", "http://localhost:18789")
OPENCLAW_GATEWAY_TOKEN = os.getenv("OPENCLAW_GATEWAY_TOKEN", "")
RELAY_TOKEN = os.getenv("RELAY_TOKEN", secrets.token_hex(32))
KAKAO_CHANNEL_SECRET = os.getenv("KAKAO_CHANNEL_SECRET", "")   # 오픈빌더 채널 시크릿 (선택)
SESSION_PREFIX = os.getenv("SESSION_PREFIX", "kakao")           # OpenClaw 세션 ID 접두사
DM_POLICY = os.getenv("DM_POLICY", "pairing")                  # pairing | open | allowlist | disabled
ALLOW_FROM: list[str] = [
    u.strip() for u in os.getenv("ALLOW_FROM", "").split(",") if u.strip()
]
RESPONSE_TIMEOUT = float(os.getenv("RESPONSE_TIMEOUT", "25"))  # 카카오 제한: 5초 미만 권장

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
log = logging.getLogger("openclaw_kakao")


# ---------------------------------------------------------------------------
# 페어링 저장소 (인메모리, 실서비스는 Redis/DB로 교체 가능)
# ---------------------------------------------------------------------------
class PairingStore:
    """OpenClaw 인스턴스 ↔ 카카오 사용자 페어링 관리."""

    def __init__(self) -> None:
        # code -> {"openclaw_session": str, "created_at": float, "ttl": float}
        self._pending: dict[str, dict] = {}
        # kakao_user_id -> openclaw_session_id
        self._pairs: dict[str, str] = {}

    def generate_code(self, session_id: str, ttl: float = 300.0) -> str:
        """페어링 코드 생성 (기본 5분 TTL)."""
        code = secrets.token_hex(3).upper()          # ABCD 형식 6자리
        formatted = f"{code[:3]}-{code[3:]}"
        self._pending[formatted] = {
            "openclaw_session": session_id,
            "created_at": time.time(),
            "ttl": ttl,
        }
        log.info("페어링 코드 생성: %s (세션: %s)", formatted, session_id)
        return formatted

    def claim_code(self, code: str, kakao_user_id: str) -> str | None:
        """카카오 사용자가 코드를 입력해 세션에 연결."""
        entry = self._pending.get(code.upper())
        if not entry:
            return None
        if time.time() - entry["created_at"] > entry["ttl"]:
            del self._pending[code.upper()]
            return None
        session_id = entry["openclaw_session"]
        self._pairs[kakao_user_id] = session_id
        del self._pending[code.upper()]
        log.info("페어링 완료: 카카오 사용자=%s → 세션=%s", kakao_user_id, session_id)
        return session_id

    def get_session(self, kakao_user_id: str) -> str | None:
        return self._pairs.get(kakao_user_id)

    def remove_pair(self, kakao_user_id: str) -> None:
        self._pairs.pop(kakao_user_id, None)

    def expire_codes(self) -> None:
        """만료된 코드 정리."""
        now = time.time()
        expired = [
            k for k, v in self._pending.items()
            if now - v["created_at"] > v["ttl"]
        ]
        for k in expired:
            del self._pending[k]


pairing_store = PairingStore()


# ---------------------------------------------------------------------------
# 카카오 SkillResponse 빌더
# ---------------------------------------------------------------------------
class KakaoResponse:
    """카카오 i 오픈빌더 SkillResponse v2 빌더."""

    @staticmethod
    def text(message: str, quick_replies: list[dict] | None = None) -> dict:
        payload: dict[str, Any] = {
            "version": "2.0",
            "template": {
                "outputs": [
                    {"simpleText": {"text": message[:1000]}}  # 카카오 최대 1000자
                ]
            },
        }
        if quick_replies:
            payload["template"]["quickReplies"] = quick_replies
        return payload

    @staticmethod
    def card(card_data: dict, quick_replies: list[dict] | None = None) -> dict:
        """JSON 카드 응답 (textCard, basicCard, listCard, etc.)."""
        card_type = next(iter(card_data))  # 첫 번째 키가 카드 타입
        payload: dict[str, Any] = {
            "version": "2.0",
            "template": {
                "outputs": [{card_type: card_data[card_type]}]
            },
        }
        if quick_replies:
            payload["template"]["quickReplies"] = quick_replies
        return payload

    @staticmethod
    def carousel(items: list[dict], carousel_type: str = "basicCard") -> dict:
        return {
            "version": "2.0",
            "template": {
                "outputs": [
                    {
                        "carousel": {
                            "type": carousel_type,
                            "items": items,
                        }
                    }
                ]
            },
        }

    @staticmethod
    def error(message: str = "잠시 후 다시 시도해 주세요.") -> dict:
        return KakaoResponse.text(f"⚠️ {message}")

    @staticmethod
    def parse_agent_response(text: str) -> dict:
        """
        OpenClaw 에이전트 응답을 Kakao SkillResponse로 변환.
        - JSON이면 카드로 변환
        - 일반 텍스트면 simpleText로 변환
        """
        stripped = text.strip()

        # JSON 카드 감지
        if stripped.startswith("{") and stripped.endswith("}"):
            try:
                data = json.loads(stripped)
                card_keys = {
                    "textCard", "basicCard", "listCard",
                    "commerceCard", "simpleImage",
                }
                # quickReplies 분리
                quick_replies = data.pop("quickReplies", None)

                if any(k in data for k in card_keys):
                    return KakaoResponse.card(data, quick_replies)

                # carousel
                if "carousel" in data:
                    return {
                        "version": "2.0",
                        "template": {
                            "outputs": [{"carousel": data["carousel"]}],
                            **({"quickReplies": quick_replies} if quick_replies else {}),
                        },
                    }
            except json.JSONDecodeError:
                pass

        # 일반 텍스트 (긴 텍스트는 청크로 분할)
        chunks = _split_text(stripped, max_len=990)
        outputs = [{"simpleText": {"text": c}} for c in chunks]
        return {"version": "2.0", "template": {"outputs": outputs}}


def _split_text(text: str, max_len: int = 990) -> list[str]:
    """카카오 텍스트 길이 제한을 위한 청크 분할."""
    if len(text) <= max_len:
        return [text]
    chunks: list[str] = []
    while text:
        chunks.append(text[:max_len])
        text = text[max_len:]
    return chunks


# ---------------------------------------------------------------------------
# OpenClaw Gateway 클라이언트
# ---------------------------------------------------------------------------
class OpenClawClient:
    """OpenClaw Gateway REST 클라이언트."""

    def __init__(self) -> None:
        headers = {"Content-Type": "application/json"}
        if OPENCLAW_GATEWAY_TOKEN:
            headers["Authorization"] = f"Bearer {OPENCLAW_GATEWAY_TOKEN}"
        self._client = httpx.AsyncClient(
            base_url=OPENCLAW_GATEWAY_URL,
            headers=headers,
            timeout=RESPONSE_TIMEOUT,
        )

    async def send_message(self, session_id: str, text: str) -> str:
        """
        OpenClaw 세션에 메시지를 전송하고 에이전트 응답을 반환.
        POST /api/sessions/{session_id}/messages
        """
        url = f"/api/sessions/{session_id}/messages"
        payload = {"text": text}
        try:
            resp = await self._client.post(url, json=payload)
            resp.raise_for_status()
            data = resp.json()
            # 응답 구조: {"message": {"text": "..."}} 또는 {"text": "..."}
            if "message" in data:
                return data["message"].get("text", "")
            return data.get("text", str(data))
        except httpx.TimeoutException:
            log.warning("OpenClaw 응답 타임아웃 (세션: %s)", session_id)
            raise
        except httpx.HTTPStatusError as e:
            log.error("OpenClaw API 오류: %s", e.response.text)
            raise

    async def create_session(self, session_id: str) -> bool:
        """세션이 없으면 생성."""
        url = f"/api/sessions/{session_id}"
        try:
            resp = await self._client.put(url, json={"sessionId": session_id})
            return resp.status_code in (200, 201, 204)
        except Exception as e:
            log.error("세션 생성 실패: %s", e)
            return False

    async def health_check(self) -> bool:
        try:
            resp = await self._client.get("/api/status", timeout=3.0)
            return resp.status_code == 200
        except Exception:
            return False

    async def aclose(self) -> None:
        await self._client.aclose()


openclaw_client = OpenClawClient()


# ---------------------------------------------------------------------------
# FastAPI 앱
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info("=== OpenClaw KakaoTalk Relay Server 시작 ===")
    log.info("OpenClaw Gateway: %s", OPENCLAW_GATEWAY_URL)
    log.info("DM 정책: %s", DM_POLICY)
    if not OPENCLAW_GATEWAY_TOKEN:
        log.warning("⚠️  OPENCLAW_GATEWAY_TOKEN 미설정 — 인증 없이 연결")

    # 주기적 코드 만료 태스크
    async def expire_loop():
        while True:
            await asyncio.sleep(60)
            pairing_store.expire_codes()

    task = asyncio.create_task(expire_loop())
    yield
    task.cancel()
    await openclaw_client.aclose()
    log.info("서버 종료")


app = FastAPI(
    title="OpenClaw KakaoTalk Channel Plugin",
    description="카카오 i 오픈빌더 ↔ OpenClaw 릴레이 서버 (Python)",
    version="1.0.0",
    lifespan=lifespan,
)


# ---------------------------------------------------------------------------
# 미들웨어: 카카오 채널 시크릿 검증 (선택)
# ---------------------------------------------------------------------------
def _verify_kakao_signature(body: bytes, signature: str | None) -> bool:
    if not KAKAO_CHANNEL_SECRET:
        return True  # 시크릿 미설정 시 검증 생략
    if not signature:
        return False
    expected = hashlib.sha256(KAKAO_CHANNEL_SECRET.encode() + body).hexdigest()
    return secrets.compare_digest(expected, signature.lower())


# ---------------------------------------------------------------------------
# DM 정책 게이트
# ---------------------------------------------------------------------------
def _check_dm_policy(kakao_user_id: str) -> tuple[bool, str]:
    """
    Returns (allowed, reason)
    """
    if DM_POLICY == "disabled":
        return False, "DM이 비활성화되어 있습니다."

    if DM_POLICY == "open":
        return True, ""

    if DM_POLICY == "allowlist":
        if kakao_user_id in ALLOW_FROM:
            return True, ""
        return False, "허용되지 않은 사용자입니다."

    # pairing (기본값)
    session = pairing_store.get_session(kakao_user_id)
    if session:
        return True, ""
    return False, "pairing"  # 페어링 필요


# ---------------------------------------------------------------------------
# 핵심 웹훅 엔드포인트
# ---------------------------------------------------------------------------
@app.post("/webhook/kakao", summary="카카오 i 오픈빌더 스킬 웹훅")
async def kakao_webhook(
    request: Request,
    x_kakao_signature: str | None = Header(default=None),
):
    """
    카카오 i 오픈빌더에서 POST로 호출되는 스킬 서버 엔드포인트.
    응답은 Kakao SkillResponse v2 포맷으로 반환합니다.
    """
    body = await request.body()

    # 시그니처 검증
    if not _verify_kakao_signature(body, x_kakao_signature):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid signature")

    try:
        payload: dict = json.loads(body)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON")

    # ── 카카오 페이로드 파싱 ──────────────────────────────────────────────
    user_request = payload.get("userRequest", {})
    user_info = payload.get("user", {}) or user_request.get("user", {})
    utterance: str = user_request.get("utterance", "").strip()
    kakao_user_id: str = user_info.get("id", "anonymous")
    bot_info = payload.get("bot", {})

    log.info("수신 [%s]: %r", kakao_user_id[:8], utterance[:80])

    # ── 특수 명령어 처리 ─────────────────────────────────────────────────
    if utterance.startswith("/pair "):
        code = utterance[6:].strip().upper()
        return await _handle_pair(kakao_user_id, code)

    if utterance in ("/reset", "/초기화"):
        return await _handle_reset(kakao_user_id)

    if utterance in ("/status", "/상태"):
        return await _handle_status(kakao_user_id)

    if utterance in ("/help", "/도움말"):
        return JSONResponse(_help_response())

    # ── DM 정책 검사 ─────────────────────────────────────────────────────
    allowed, reason = _check_dm_policy(kakao_user_id)
    if not allowed:
        if reason == "pairing":
            return JSONResponse(
                KakaoResponse.text(
                    "🔗 OpenClaw에 연결되지 않았습니다.\n\n"
                    "OpenClaw에서 페어링 코드를 생성한 후\n"
                    "'/pair ABCD-12' 형식으로 입력하세요.",
                    quick_replies=[
                        {
                            "label": "도움말",
                            "action": "message",
                            "messageText": "/help",
                        }
                    ],
                )
            )
        return JSONResponse(KakaoResponse.error(reason))

    # ── OpenClaw로 메시지 전달 ────────────────────────────────────────────
    session_id = pairing_store.get_session(kakao_user_id) or _default_session(kakao_user_id)

    try:
        agent_reply = await openclaw_client.send_message(session_id, utterance)
    except httpx.TimeoutException:
        return JSONResponse(
            KakaoResponse.error("응답 시간이 초과되었습니다. (25초)")
        )
    except Exception as e:
        log.error("OpenClaw 오류: %s", e)
        return JSONResponse(
            KakaoResponse.error(f"OpenClaw 연결 오류: {type(e).__name__}")
        )

    log.info("응답 [%s]: %r", kakao_user_id[:8], agent_reply[:80])
    return JSONResponse(KakaoResponse.parse_agent_response(agent_reply))


# ---------------------------------------------------------------------------
# 특수 명령어 핸들러
# ---------------------------------------------------------------------------
async def _handle_pair(kakao_user_id: str, code: str) -> JSONResponse:
    session_id = pairing_store.claim_code(code, kakao_user_id)
    if not session_id:
        return JSONResponse(
            KakaoResponse.text(
                "❌ 유효하지 않거나 만료된 코드입니다.\n"
                "OpenClaw에서 새 코드를 생성해 주세요."
            )
        )
    # OpenClaw 세션 초기화 시도
    await openclaw_client.create_session(session_id)
    return JSONResponse(
        KakaoResponse.text(
            f"✅ OpenClaw 연결 완료!\n"
            f"세션: {session_id[:12]}...\n\n"
            "이제 OpenClaw AI 어시스턴트와 대화할 수 있습니다."
        )
    )


async def _handle_reset(kakao_user_id: str) -> JSONResponse:
    session_id = pairing_store.get_session(kakao_user_id)
    if not session_id:
        return JSONResponse(KakaoResponse.text("연결된 세션이 없습니다."))
    pairing_store.remove_pair(kakao_user_id)
    return JSONResponse(
        KakaoResponse.text(
            "🔄 세션이 초기화되었습니다.\n"
            "재연결하려면 OpenClaw에서 새 페어링 코드를 생성하세요."
        )
    )


async def _handle_status(kakao_user_id: str) -> JSONResponse:
    session_id = pairing_store.get_session(kakao_user_id)
    gw_ok = await openclaw_client.health_check()

    if session_id:
        msg = (
            f"🟢 OpenClaw 연결됨\n"
            f"세션: {session_id[:12]}...\n"
            f"Gateway: {'정상' if gw_ok else '⚠️ 오프라인'}"
        )
    else:
        msg = (
            f"⚫ 연결되지 않음\n"
            f"Gateway: {'정상' if gw_ok else '⚠️ 오프라인'}\n\n"
            "'/pair <코드>'로 연결하세요."
        )
    return JSONResponse(KakaoResponse.text(msg))


def _help_response() -> dict:
    return KakaoResponse.text(
        "📖 OpenClaw KakaoTalk 채널 도움말\n\n"
        "/pair <코드>  - OpenClaw 연결\n"
        "/status       - 연결 상태 확인\n"
        "/reset        - 연결 초기화\n"
        "/help         - 도움말\n\n"
        "연결 후 자유롭게 대화하세요! 🤖",
        quick_replies=[
            {"label": "상태 확인", "action": "message", "messageText": "/status"},
        ],
    )


def _default_session(kakao_user_id: str) -> str:
    """open 정책용 기본 세션 ID."""
    short = hashlib.sha256(kakao_user_id.encode()).hexdigest()[:8]
    return f"{SESSION_PREFIX}-{short}"


# ---------------------------------------------------------------------------
# Admin API (릴레이 토큰으로 보호)
# ---------------------------------------------------------------------------
def _require_relay_token(authorization: str | None = Header(default=None)) -> None:
    if not RELAY_TOKEN:
        return
    if not authorization or authorization != f"Bearer {RELAY_TOKEN}":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid relay token",
        )


@app.post(
    "/admin/pair/generate",
    summary="OpenClaw 인스턴스용 페어링 코드 생성",
    dependencies=[],
)
async def admin_generate_pair(
    request: Request,
    authorization: str | None = Header(default=None),
):
    """
    OpenClaw 플러그인이 호출 — 페어링 코드 생성.

    Body: {"sessionId": "my-session", "ttl": 300}
    Returns: {"code": "ABC-123", "expires_in": 300}
    """
    _require_relay_token(authorization)
    body = await request.json()
    session_id: str = body.get("sessionId", f"session-{secrets.token_hex(4)}")
    ttl: float = float(body.get("ttl", 300))
    code = pairing_store.generate_code(session_id, ttl=ttl)
    return {"code": code, "expires_in": ttl, "sessionId": session_id}


@app.get("/admin/pairs", summary="현재 페어링 목록 조회")
async def admin_list_pairs(authorization: str | None = Header(default=None)):
    _require_relay_token(authorization)
    return {
        "pairs": {k[:8] + "...": v for k, v in pairing_store._pairs.items()},
        "pending_codes": list(pairing_store._pending.keys()),
    }


@app.delete("/admin/pairs/{kakao_user_id}", summary="페어링 해제")
async def admin_remove_pair(
    kakao_user_id: str,
    authorization: str | None = Header(default=None),
):
    _require_relay_token(authorization)
    pairing_store.remove_pair(kakao_user_id)
    return {"ok": True}


# ---------------------------------------------------------------------------
# 헬스체크
# ---------------------------------------------------------------------------
@app.get("/health", summary="서버 헬스체크")
async def health():
    gw_ok = await openclaw_client.health_check()
    return {
        "status": "ok",
        "openclaw_gateway": "reachable" if gw_ok else "unreachable",
        "dm_policy": DM_POLICY,
        "active_pairs": len(pairing_store._pairs),
    }


@app.get("/", summary="서버 정보")
async def root():
    return {
        "name": "OpenClaw KakaoTalk Channel Plugin",
        "version": "1.0.0",
        "docs": "/docs",
    }
