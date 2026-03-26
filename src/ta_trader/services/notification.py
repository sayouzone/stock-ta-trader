"""
Notification Service: 다중 채널 알림 라우팅.
Strategy Pattern으로 채널별 발송 로직을 분리합니다.
"""

import abc
from dataclasses import dataclass
from typing import Any

import httpx

from ta_trader.config import get_settings
from ta_trader.utils.logger import get_logger

logger = get_logger(__name__)


# ── Channel Interface ────────────────────────────────────

class NotificationChannel(abc.ABC):
    """알림 채널 인터페이스."""

    @property
    @abc.abstractmethod
    def channel_name(self) -> str: ...

    @abc.abstractmethod
    async def send(self, message: str, metadata: dict[str, Any] | None = None) -> bool: ...


# ── Telegram Channel ────────────────────────────────────

class TelegramChannel(NotificationChannel):
    """텔레그램 알림 채널."""

    channel_name = "telegram"

    def __init__(self, bot_token: str, chat_id: int) -> None:
        self._bot_token = bot_token
        self._chat_id = chat_id
        self._base_url = f"https://api.telegram.org/bot{bot_token}"

    async def send(self, message: str, metadata: dict[str, Any] | None = None) -> bool:
        async with httpx.AsyncClient() as client:
            try:
                resp = await client.post(
                    f"{self._base_url}/sendMessage",
                    json={
                        "chat_id": self._chat_id,
                        "text": message,
                        "parse_mode": "Markdown",
                    },
                )
                resp.raise_for_status()
                return True
            except httpx.HTTPError as e:
                logger.error("Telegram send failed: %s", e)
                return False


# ── Ntfy Push Channel ───────────────────────────────────

class NtfyChannel(NotificationChannel):
    """ntfy.sh 푸시 알림 채널."""

    channel_name = "ntfy"

    def __init__(self, server: str, topic: str) -> None:
        self._url = f"{server}/{topic}"

    async def send(self, message: str, metadata: dict[str, Any] | None = None) -> bool:
        headers = {}
        if metadata:
            if title := metadata.get("title"):
                headers["Title"] = title
            if priority := metadata.get("priority"):
                headers["Priority"] = str(priority)
            if tags := metadata.get("tags"):
                headers["Tags"] = tags

        async with httpx.AsyncClient() as client:
            try:
                resp = await client.post(
                    self._url,
                    content=message.encode("utf-8"),
                    headers=headers,
                )
                resp.raise_for_status()
                return True
            except httpx.HTTPError as e:
                logger.error("Ntfy send failed: %s", e)
                return False


# ── KakaoTalk Channel (stub) ────────────────────────────

class KakaoTalkChannel(NotificationChannel):
    """카카오톡 알림 채널 (카카오 i 오픈빌더 연동)."""

    channel_name = "kakaotalk"

    def __init__(self, rest_api_key: str) -> None:
        self._api_key = rest_api_key

    async def send(self, message: str, metadata: dict[str, Any] | None = None) -> bool:
        # TODO: 카카오 알림톡 API 연동
        logger.warning("KakaoTalk channel not yet implemented")
        return False


# ── Notification Router ─────────────────────────────────

@dataclass
class AlertPayload:
    """알림 페이로드."""
    ticker: str
    title: str
    message: str
    priority: int = 3  # 1(min) ~ 5(max)
    channels: list[str] | None = None  # None이면 모든 채널


class NotificationService:
    """다중 채널 알림 서비스."""

    def __init__(self) -> None:
        self._channels: dict[str, NotificationChannel] = {}
        self._default_channels: list[str] = []

    def register_channel(
        self,
        channel: NotificationChannel,
        default: bool = True,
    ) -> None:
        self._channels[channel.channel_name] = channel
        if default:
            self._default_channels.append(channel.channel_name)
        logger.info("Registered notification channel: %s", channel.channel_name)

    async def send_alert(self, payload: AlertPayload) -> dict[str, bool]:
        """
        알림을 지정된 채널(또는 기본 채널)로 발송.
        Returns: {channel_name: success} 딕셔너리
        """
        target_channels = payload.channels or self._default_channels
        results: dict[str, bool] = {}

        formatted = self._format_message(payload)

        for ch_name in target_channels:
            channel = self._channels.get(ch_name)
            if channel is None:
                logger.warning("Unknown channel: %s", ch_name)
                results[ch_name] = False
                continue

            success = await channel.send(
                formatted,
                metadata={
                    "title": payload.title,
                    "priority": payload.priority,
                    "tags": f"chart,{payload.ticker}",
                },
            )
            results[ch_name] = success

        return results

    def _format_message(self, payload: AlertPayload) -> str:
        """채널 공통 메시지 포맷."""
        priority_emoji = {1: "⬜", 2: "🟦", 3: "🟨", 4: "🟧", 5: "🟥"}
        emoji = priority_emoji.get(payload.priority, "🟨")
        return (
            f"{emoji} *{payload.title}*\n"
            f"종목: `{payload.ticker}`\n"
            f"───────────\n"
            f"{payload.message}"
        )


def create_notification_service() -> NotificationService:
    """설정 기반 NotificationService 팩토리."""
    settings = get_settings()
    service = NotificationService()

    # Ntfy (항상 등록)
    service.register_channel(
        NtfyChannel(server=settings.ntfy_server, topic=settings.ntfy_topic)
    )

    # Telegram (토큰이 있을 때만)
    token = settings.telegram_bot_token.get_secret_value()
    if token:
        for user_id in settings.telegram_allowed_user_ids:
            service.register_channel(
                TelegramChannel(bot_token=token, chat_id=user_id)
            )

    # KakaoTalk (키가 있을 때만)
    kakao_key = settings.kakao_rest_api_key.get_secret_value()
    if kakao_key:
        service.register_channel(
            KakaoTalkChannel(rest_api_key=kakao_key),
            default=False,  # 명시적 요청 시에만 사용
        )

    return service
