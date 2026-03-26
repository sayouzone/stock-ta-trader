# ta_trader/config/settings.py
"""
Application settings with environment-based configuration.
Uses pydantic-settings for validation and .env file support.
"""

from functools import lru_cache
from typing import Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # ── App ──────────────────────────────────────────────
    app_name: str = "Stock TA Trader"
    app_env: Literal["dev", "staging", "prod"] = "dev"
    debug: bool = True
    api_version: str = "v1"
    api_prefix: str = "/api/v1"

    # ── Auth ─────────────────────────────────────────────
    jwt_secret_key: SecretStr = Field(default="change-me-in-production")
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 24 * 7  # 7 days

    # ── Database ─────────────────────────────────────────
    database_url: str = "postgresql+asyncpg://trader:trader@localhost:5432/trader_db"
    db_echo: bool = False

    # ── Redis ────────────────────────────────────────────
    redis_url: str = "redis://localhost:6379/0"
    cache_ttl_market_open: int = 60        # 장 중 1분
    cache_ttl_market_close: int = 3600     # 장 후 1시간
    cache_ttl_fundamental: int = 86400     # 기본적 데이터 24시간

    # ── Telegram ─────────────────────────────────────────
    telegram_bot_token: SecretStr = Field(default="")
    telegram_allowed_user_ids: list[int] = []

    # ── KakaoTalk ────────────────────────────────────────
    kakao_rest_api_key: SecretStr = Field(default="")

    # ── Push Notification ────────────────────────────────
    ntfy_topic: str = "stock-ta-trader"
    ntfy_server: str = "https://ntfy.sh"

    # ── External APIs ────────────────────────────────────
    anthropic_api_key: SecretStr = Field(default="")
    gemini_api_key: SecretStr = Field(default="")
    kis_app_key: SecretStr = Field(default="")
    kis_app_secret: SecretStr = Field(default="")
    dart_api_key: SecretStr = Field(default="")

    # ── Scheduler ────────────────────────────────────────
    scheduler_enabled: bool = True
    market_pre_scan_cron: str = "0 8 * * 1-5"     # 월-금 08:00
    market_post_review_cron: str = "0 16 * * 1-5"  # 월-금 16:00

    @property
    def is_production(self) -> bool:
        return self.app_env == "prod"


@lru_cache
def get_settings() -> Settings:
    return Settings()
