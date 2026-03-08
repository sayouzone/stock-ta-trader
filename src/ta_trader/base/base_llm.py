"""
ta_trader/llm/base.py
LLM 분석기 공통 인터페이스 (추상 기반 클래스)

모든 Provider(Anthropic, Gemini, …)는 이 클래스를 상속합니다.
외부에서는 BaseLLMAnalyzer 타입으로만 다루므로
Provider 교체 시 호출 코드를 수정할 필요가 없습니다.
"""

from __future__ import annotations

import json
import re
from abc import ABC, abstractmethod
from typing import Iterator

import pandas as pd

from ta_trader.models.llm_models import LLMAnalysis
from ta_trader.llm.prompt_builder import PromptBuilder
from ta_trader.models import TradingDecision
from ta_trader.utils.logger import get_logger

logger = get_logger(__name__)


class BaseLLMAnalyzer(ABC):
    """
    LLM Provider 공통 인터페이스.

    하위 클래스 구현 의무:
        _call_api(system, prompt) -> str          # 동기 호출 → 원문 응답
        _call_api_stream(system, prompt) -> Iterator[str]  # 스트리밍

    공통 제공:
        analyze()        # _call_api 호출 → LLMAnalysis 반환
        analyze_stream() # _call_api_stream 호출 → Iterator[str]
        _parse_response() # JSON 파싱 + 폴백
    """

    def __init__(self, model: str) -> None:
        self._model   = model
        self._builder = PromptBuilder()

    # ── 공개 API (공통 구현) ──────────────────────────────

    def analyze(
        self,
        decision:    TradingDecision,
        df:          pd.DataFrame,
        recent_days: int = 10,
    ) -> LLMAnalysis:
        """동기 분석 실행 → LLMAnalysis 반환"""
        from ta_trader.llm.prompt_builder import SYSTEM_PROMPT
        prompt = self._builder.build(decision, df, recent_days)
        logger.info("LLM 분석 시작", ticker=decision.ticker,
                    provider=self.provider_name, model=self._model)

        raw = self._call_api(SYSTEM_PROMPT, prompt)

        logger.info("LLM 분석 완료", ticker=decision.ticker, provider=self.provider_name)
        return self._parse_response(raw, self._model, self.provider_name)

    def analyze_stream(
        self,
        decision:    TradingDecision,
        df:          pd.DataFrame,
        recent_days: int = 10,
    ) -> Iterator[str]:
        """스트리밍 분석 → 텍스트 청크 Iterator"""
        from ta_trader.llm.prompt_builder import SYSTEM_PROMPT
        prompt = self._builder.build(decision, df, recent_days)
        logger.info("LLM 스트리밍 시작", ticker=decision.ticker, provider=self.provider_name)
        yield from self._call_api_stream(SYSTEM_PROMPT, prompt)

    # ── Provider별 구현 의무 ──────────────────────────────

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Provider 식별자 ('anthropic' | 'google')"""

    @abstractmethod
    def _call_api(self, system: str, prompt: str) -> str:
        """동기 API 호출 → 원문 응답 텍스트"""

    @abstractmethod
    def _call_api_stream(self, system: str, prompt: str) -> Iterator[str]:
        """스트리밍 API 호출 → 텍스트 청크 Iterator"""

    # ── 공통 파싱 (모든 Provider 공유) ───────────────────

    @staticmethod
    def _parse_response(raw: str, model: str, provider: str = "") -> LLMAnalysis:
        """JSON 응답 → LLMAnalysis. 파싱 실패 시 원문으로 폴백."""
        cleaned = re.sub(r"```(?:json)?\s*|\s*```", "", raw).strip()
        try:
            data = json.loads(cleaned)
        except json.JSONDecodeError as exc:
            logger.warning("JSON 파싱 실패, 원문으로 폴백",
                           provider=provider, error=str(exc))
            return LLMAnalysis(
                overall_assessment = raw,
                signal_rationale   = "JSON 파싱 실패 - 원문 응답을 확인하세요.",
                provider           = provider,
                model              = model,
                raw_response       = raw,
            )

        return LLMAnalysis(
            overall_assessment = data.get("overall_assessment", ""),
            signal_rationale   = data.get("signal_rationale", ""),
            key_risks          = data.get("key_risks", []),
            opportunities      = data.get("opportunities", []),
            action_plan        = data.get("action_plan", ""),
            confidence         = float(data.get("confidence", 0.0)),
            provider           = provider,
            model              = model,
            raw_response       = raw,
        )
