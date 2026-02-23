"""
ta_trader/utils/logger.py
structlog 기반 구조화 로깅 설정

Notes:
    - PrintLoggerFactory 는 .name 속성이 없어 add_logger_name 과 충돌.
    - stdlib.LoggerFactory 를 사용하면 표준 logging.Logger 를 백엔드로 써서 .name 을 지원.
"""

from __future__ import annotations

import logging
import os
import sys

_LOG_LEVEL_NAME: str = os.getenv("TA_TRADER_LOG_LEVEL", "INFO")
_LOG_LEVEL: int = logging.getLevelName(_LOG_LEVEL_NAME)

try:
    import structlog

    # 표준 logging 설정 (structlog 의 stdlib 백엔드 요구사항)
    logging.basicConfig(
        level=_LOG_LEVEL,
        format="%(message)s",
        stream=sys.stderr,
    )

    structlog.configure(
        processors=[
            structlog.stdlib.add_log_level,           # level 필드 추가
            structlog.stdlib.add_logger_name,         # logger 이름 추가 (stdlib 백엔드 필요)
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="%H:%M:%S", utc=False),
            structlog.dev.ConsoleRenderer(colors=True),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(_LOG_LEVEL),
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),   # PrintLoggerFactory → stdlib
        cache_logger_on_first_use=True,
    )

    def get_logger(name: str):  # type: ignore[return]
        return structlog.get_logger(name)

except ImportError:
    # structlog 미설치 시 표준 logging 폴백
    logging.basicConfig(
        level=_LOG_LEVEL,
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        stream=sys.stderr,
    )

    def get_logger(name: str):  # type: ignore[return]
        return logging.getLogger(name)
