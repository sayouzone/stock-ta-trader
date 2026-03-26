"""
Telegram Bot 실행 엔트리포인트.
docker-compose에서 별도 컨테이너로 실행됩니다.

Usage:
    python -m run_telegram
"""

import asyncio

from ta_trader.infra.cache import cache
from ta_trader.infra.db import init_db
from ta_trader.interfaces.telegram.bot import create_telegram_bot
from ta_trader.services.agent_service import agent_service
from ta_trader.services.notification import create_notification_service
from ta_trader.utils.logger import get_logger

logger = get_logger(__name__)

async def setup() -> None:
    """Redis/DB 초기화."""
    await cache.connect()
    await init_db()
    logger.info("Infrastructure initialized for Telegram bot")


def main() -> None:
    """봇 시작."""
    # 인프라 초기화
    asyncio.get_event_loop().run_until_complete(setup())

    # 알림 서비스 생성
    notification_svc = create_notification_service()

    # 봇 생성 및 실행
    app = create_telegram_bot(
        agent_svc=agent_service,
        notification_svc=notification_svc,
    )

    logger.info("Starting Telegram bot...")
    app.run_polling(allowed_updates=["message", "callback_query"])


if __name__ == "__main__":
    main()
