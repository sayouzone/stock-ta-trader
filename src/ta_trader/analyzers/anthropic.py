"""
ta_trader/analyzers/anthropic.py
Anthropic Claude API 기반 기술적 분석 해석기

환경변수:
    ANTHROPIC_API_KEY  : Anthropic API 키 (필수)
    TA_LLM_MODEL       : 사용 모델 (기본값: claude-sonnet-4-20250514)
    TA_LLM_MAX_TOKENS  : 최대 응답 토큰 수 (기본값: 1500)
    TA_LLM_TIMEOUT     : 요청 타임아웃 초 (기본값: 60)
"""

from __future__ import annotations

import json
import os
import re
from typing import Iterator

import anthropic
import pandas as pd

from ta_trader.exceptions import TATraderError
from ta_trader.base.llm import BaseLLMAnalyzer
from ta_trader.utils.logger import get_logger

logger = get_logger(__name__)

_DEFAULT_MODEL      = "claude-sonnet-4-20250514"
#_DEFAULT_MODEL      = "claude-sonnet-4-6"  # 2026-02-20 기준 최신 버전
#_DEFAULT_MODEL      = "claude-opus-4-6"    # 2026-02-20 기준 최신 버전
#_DEFAULT_MAX_TOKENS = 1500   # 토큰 사이즈가 너무 작아서 짤림
_DEFAULT_MAX_TOKENS = 8192
_DEFAULT_TIMEOUT    = 60


class AnthropicAnalyzer(BaseLLMAnalyzer):
    """
    TradingDecision 을 Anthropic Claude 에 전달하여
    자연어 투자 해석 및 액션 플랜을 생성합니다.

    사용 예:
        analyzer = AnthropicAnalyzer()
        result = analyzer.analyze(decision, df)
        print(result.overall_assessment)

        # 스트리밍 출력
        for chunk in analyzer.analyze_stream(decision, df):
            print(chunk, end="", flush=True)
    """

    def __init__(
        self,
        api_key:    str | None = None,
        model:      str | None = None,
        max_tokens: int | None = None,
    ) -> None:
        _key = api_key or os.getenv("ANTHROPIC_API_KEY")
        if not _key:
            raise TATraderError(
                "ANTHROPIC_API_KEY 환경변수가 설정되지 않았습니다.\n"
                "  export ANTHROPIC_API_KEY='sk-ant-...'"
            )
        super().__init__(
            model=model or os.getenv("TA_LLM_MODEL", _DEFAULT_MODEL)
        )
        self._client     = anthropic.Anthropic(api_key=_key)
        self._max_tokens = max_tokens or int(os.getenv("TA_LLM_MAX_TOKENS", _DEFAULT_MAX_TOKENS))

    @property
    def provider_name(self) -> str:
        return "anthropic"

    def _call_api(self, system: str, prompt: str) -> str:
        message = self._client.messages.create(
            model      = self._model,
            max_tokens = self._max_tokens,
            system     = system,
            messages   = [{"role": "user", "content": prompt}],
        )
        logger.info("Anthropic 응답 수신",
                    input_tokens=message.usage.input_tokens,
                    output_tokens=message.usage.output_tokens)
        return message.content[0].text

    def _call_api_stream(self, system: str, prompt: str) -> Iterator[str]:
        with self._client.messages.stream(
            model      = self._model,
            max_tokens = self._max_tokens,
            system     = system,
            messages   = [{"role": "user", "content": prompt}],
        ) as stream:
            yield from stream.text_stream


# 하위 호환성: 기존 코드가 LLMAnalyzer 이름으로 import 하던 경우 대비
LLMAnalyzer = AnthropicAnalyzer
