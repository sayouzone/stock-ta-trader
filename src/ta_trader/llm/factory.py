"""
ta_trader/llm/factory.py
LLM Provider 팩토리

지원 Provider:
    'anthropic' → AnthropicAnalyzer (ANTHROPIC_API_KEY 필요)
    'gemini'    → GeminiAnalyzer    (GEMINI_API_KEY 필요)

사용 예:
    from ta_trader.llm.factory import create_llm_analyzer

    # Provider 자동 선택 (환경변수 기준)
    llm = create_llm_analyzer()

    # 명시적 지정
    llm = create_llm_analyzer(provider="gemini")
    llm = create_llm_analyzer(provider="anthropic", model="claude-opus-4-6")
"""

from __future__ import annotations

import os

from ta_trader.exceptions import TATraderError
from ta_trader.llm.base import BaseLLMAnalyzer

# 지원 Provider 등록 테이블
_PROVIDERS: dict[str, str] = {
    "anthropic": "ta_trader.llm.anthropic_analyzer.AnthropicAnalyzer",
    "google":    "ta_trader.llm.google_analyzer.GoogleAnalyzer",
}


def create_llm_analyzer(
    provider:   str | None = None,
    api_key:    str | None = None,
    model:      str | None = None,
    max_tokens: int | None = None,
) -> BaseLLMAnalyzer:
    """
    LLM 분석기 인스턴스를 생성합니다.

    Args:
        provider:   'anthropic' | 'google' | None
                    None이면 환경변수 TA_LLM_PROVIDER 확인 후
                    설정된 API 키 기준으로 자동 선택합니다.
        api_key:    해당 Provider의 API 키 (None이면 환경변수 사용)
        model:      LLM 모델명 (None이면 Provider 기본값 사용)
        max_tokens: 최대 응답 토큰 수

    Returns:
        BaseLLMAnalyzer 구현 인스턴스

    Raises:
        TATraderError: 지원하지 않는 Provider 이름이거나 API 키 미설정
    """
    resolved = provider or os.getenv("TA_LLM_PROVIDER") or _auto_detect_provider()

    if resolved not in _PROVIDERS:
        supported = ", ".join(_PROVIDERS.keys())
        raise TATraderError(
            f"지원하지 않는 LLM Provider: '{resolved}'\n"
            f"지원 목록: {supported}"
        )

    # 지연 임포트: 사용하지 않는 Provider의 패키지 설치 여부에 영향받지 않도록
    module_path, class_name = _PROVIDERS[resolved].rsplit(".", 1)
    import importlib
    module = importlib.import_module(module_path)
    cls    = getattr(module, class_name)

    kwargs: dict = {}
    if api_key    is not None: kwargs["api_key"]    = api_key
    if model      is not None: kwargs["model"]      = model
    if max_tokens is not None: kwargs["max_tokens"] = max_tokens

    return cls(**kwargs)


def _auto_detect_provider() -> str:
    """
    설정된 API 키를 기준으로 Provider 자동 감지.
    둘 다 설정된 경우 Anthropic 우선.
    """
    if os.getenv("ANTHROPIC_API_KEY"):
        return "anthropic"
    if os.getenv("GEMINI_API_KEY"):
        return "google"
    raise TATraderError(
        "LLM API 키가 설정되지 않았습니다.\n"
        "  Anthropic: export ANTHROPIC_API_KEY='sk-ant-...'\n"
        "  Gemini:    export GEMINI_API_KEY='AIza...'\n"
        "  또는 --llm-provider 옵션으로 Provider를 지정하세요."
    )


def list_providers() -> list[str]:
    """지원 Provider 목록 반환"""
    return list(_PROVIDERS.keys())