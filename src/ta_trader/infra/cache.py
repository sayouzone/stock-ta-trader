"""
Redis 캐시 래퍼.
장 운영 시간에 따라 TTL을 자동 조절합니다.
"""

import json
from datetime import datetime
from typing import Any

import redis.asyncio as redis

from ta_trader.config import get_settings
from ta_trader.utils.logger import get_logger

logger = get_logger(__name__)


class CacheManager:
    """Redis 기반 캐시 매니저 with 시장 인지 TTL."""

    def __init__(self) -> None:
        self._settings = get_settings()
        self._redis: redis.Redis | None = None

    async def connect(self) -> None:
        self._redis = redis.from_url(
            self._settings.redis_url,
            decode_responses=True,
        )
        logger.info("Redis connected: %s", self._settings.redis_url)

    async def disconnect(self) -> None:
        if self._redis:
            await self._redis.close()
            logger.info("Redis disconnected")

    @property
    def client(self) -> redis.Redis:
        if self._redis is None:
            raise RuntimeError("Redis not connected. Call connect() first.")
        return self._redis

    def _get_market_ttl(self) -> int:
        """KRX 장 운영 시간(09:00-15:30) 기준 TTL 반환."""
        now = datetime.now()
        hour = now.hour
        is_weekday = now.weekday() < 5
        is_market_hours = is_weekday and 9 <= hour < 16
        if is_market_hours:
            return self._settings.cache_ttl_market_open
        return self._settings.cache_ttl_market_close

    async def get(self, key: str) -> Any | None:
        raw = await self.client.get(key)
        if raw is None:
            return None
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return raw

    async def set(
        self,
        key: str,
        value: Any,
        ttl: int | None = None,
    ) -> None:
        ttl = ttl or self._get_market_ttl()
        serialized = json.dumps(value, default=str, ensure_ascii=False)
        await self.client.set(key, serialized, ex=ttl)

    async def delete(self, key: str) -> None:
        await self.client.delete(key)

    async def get_or_set(
        self,
        key: str,
        factory,
        ttl: int | None = None,
    ) -> Any:
        """캐시 히트 시 반환, 미스 시 factory 실행 후 저장."""
        cached = await self.get(key)
        if cached is not None:
            return cached
        value = await factory()
        await self.set(key, value, ttl)
        return value

    # ── Pub/Sub for real-time alerts ─────────────────────

    async def publish(self, channel: str, message: dict[str, Any]) -> None:
        await self.client.publish(channel, json.dumps(message, default=str))

    async def subscribe(self, channel: str):
        pubsub = self.client.pubsub()
        await pubsub.subscribe(channel)
        return pubsub


# Singleton
cache = CacheManager()
