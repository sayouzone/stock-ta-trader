"""
ta_trader/analyzers/google_analyzer.py
Google Gemini API Provider (google-genai SDK)

환경변수:
    GEMINI_API_KEY        : Google AI Studio API 키 (필수)
    TA_GEMINI_MODEL       : 모델명 (기본값: gemini-2.0-flash)
    TA_GEMINI_MAX_TOKENS  : 최대 출력 토큰 수 (기본값: 1500)

참고:
    - Gemini는 system instruction을 별도 파라미터로 전달
    - 스트리밍은 generate_content_stream() 사용
    - 응답 safety ratings로 차단될 경우 TATraderError 발생
"""

from __future__ import annotations

import os
from typing import Iterator

from google import genai
from google.genai import types

from ta_trader.exceptions import TATraderError
from ta_trader.base.base_llm import BaseLLMAnalyzer
from ta_trader.utils.logger import get_logger

logger = get_logger(__name__)

#_DEFAULT_MODEL      = "gemini-2.0-flash"
_DEFAULT_MODEL      = "gemini-3-pro-preview"
#_DEFAULT_MAX_TOKENS = 1500
_DEFAULT_MAX_TOKENS = 8192


class GoogleAnalyzer(BaseLLMAnalyzer):
    """
    Google Gemini API 기반 LLM 분석기.

    사용 예:
        analyzer = GeminiAnalyzer()
        result = analyzer.analyze(decision, df)

        # 스트리밍
        for chunk in analyzer.analyze_stream(decision, df):
            print(chunk, end="", flush=True)
    """

    def __init__(
        self,
        api_key:    str | None = None,
        model:      str | None = None,
        max_tokens: int | None = None,
    ) -> None:
        _key = api_key or os.getenv("GEMINI_API_KEY")
        if not _key:
            raise TATraderError(
                "GEMINI_API_KEY 환경변수가 설정되지 않았습니다.\n"
                "  export GEMINI_API_KEY='AIza...'\n"
                "  Google AI Studio: https://aistudio.google.com/app/apikey"
            )
        super().__init__(
            model=model or os.getenv("TA_GEMINI_MODEL", _DEFAULT_MODEL)
        )
        self._client     = genai.Client(api_key=_key)
        self._max_tokens = max_tokens or int(os.getenv("TA_GEMINI_MAX_TOKENS", _DEFAULT_MAX_TOKENS))

    @property
    def provider_name(self) -> str:
        return "google"

    def _call_api(self, system: str, prompt: str) -> str:
        config = types.GenerateContentConfig(
            system_instruction = system,
            max_output_tokens  = self._max_tokens,
            temperature        = 0.3,    # 금융 분석: 낮은 온도로 일관성 확보
        )
        response = self._client.models.generate_content(
            model    = self._model,
            contents = prompt,
            config   = config,
        )
        self._check_safety(response)
        text = response.text
        logger.info("Gemini 응답 수신",
                    model=self._model,
                    finish_reason=str(response.candidates[0].finish_reason) if response.candidates else "unknown")
        return text

    def _call_api_stream(self, system: str, prompt: str) -> Iterator[str]:
        config = types.GenerateContentConfig(
            system_instruction = system,
            max_output_tokens  = self._max_tokens,
            temperature        = 0.3,
        )
        for chunk in self._client.models.generate_content_stream(
            model    = self._model,
            contents = prompt,
            config   = config,
        ):
            if chunk.text:
                yield chunk.text

    # ── 내부 유틸 ─────────────────────────────────────────

    @staticmethod
    def _check_safety(response) -> None:
        """Safety filter로 응답이 차단된 경우 예외 발생"""
        if not response.candidates:
            raise TATraderError(
                "Gemini 응답이 Safety Filter에 의해 차단되었습니다. "
                "프롬프트 내용을 확인하세요."
            )
        candidate = response.candidates[0]
        # STOP이 아닌 finish_reason은 문제 상황
        finish = str(candidate.finish_reason)
        if finish not in ("FinishReason.STOP", "STOP", "1"):
            logger.warning("Gemini 비정상 종료", finish_reason=finish)
