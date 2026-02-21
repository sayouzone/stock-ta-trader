"""
ta_trader/llm/analyzer.py
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
from ta_trader.llm.models import LLMAnalysis
from ta_trader.llm.prompt_builder import SYSTEM_PROMPT, PromptBuilder
from ta_trader.models import TradingDecision
from ta_trader.utils.logger import get_logger

logger = get_logger(__name__)

_DEFAULT_MODEL      = "claude-sonnet-4-20250514"
#_DEFAULT_MODEL      = "claude-sonnet-4-6"  # 2026-02-20 기준 최신 버전
#_DEFAULT_MODEL      = "claude-opus-4-6"    # 2026-02-20 기준 최신 버전
#_DEFAULT_MAX_TOKENS = 1500   # 토큰 사이즈가 너무 작아서 짤림
_DEFAULT_MAX_TOKENS = 8192
_DEFAULT_TIMEOUT    = 60


class LLMAnalyzer:
    """
    TradingDecision 을 Anthropic Claude 에 전달하여
    자연어 투자 해석 및 액션 플랜을 생성합니다.

    사용 예:
        analyzer = LLMAnalyzer()
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
        timeout:    int | None = None,
    ) -> None:
        _key = api_key or os.getenv("ANTHROPIC_API_KEY")
        if not _key:
            raise TATraderError(
                "ANTHROPIC_API_KEY 환경변수가 설정되지 않았습니다.\n"
                "  export ANTHROPIC_API_KEY='sk-ant-...'"
            )
        self._client     = anthropic.Anthropic(api_key=_key)
        self._model      = model      or os.getenv("TA_LLM_MODEL",      _DEFAULT_MODEL)
        self._max_tokens = max_tokens or int(os.getenv("TA_LLM_MAX_TOKENS", _DEFAULT_MAX_TOKENS))
        self._timeout    = timeout    or int(os.getenv("TA_LLM_TIMEOUT",    _DEFAULT_TIMEOUT))
        self._builder    = PromptBuilder()

    # ── 공개 API ─────────────────────────────────────────

    def analyze(
        self,
        decision: TradingDecision,
        df: pd.DataFrame,
        recent_days: int = 10,
    ) -> LLMAnalysis:
        """
        동기 방식으로 LLM 분석을 실행하고 결과를 반환합니다.

        Args:
            decision:    기술적 분석 결과 (MonthlyTradingAnalyzer.analyze() 반환값)
            df:          지표가 계산된 DataFrame
            recent_days: 가격 추이 요약에 사용할 최근 일수

        Returns:
            LLMAnalysis 인스턴스
        """
        prompt = self._builder.build(decision, df, recent_days)
        logger.info("LLM 분석 시작", ticker=decision.ticker, model=self._model)

        message = self._client.messages.create(
            model      = self._model,
            max_tokens = self._max_tokens,
            system     = SYSTEM_PROMPT,
            messages   = [{"role": "user", "content": prompt}],
        )

        raw = message.content[0].text
        logger.info("LLM 분석 완료", ticker=decision.ticker,
                    input_tokens=message.usage.input_tokens,
                    output_tokens=message.usage.output_tokens)

        return self._parse_response(raw, self._model)

    def analyze_stream(
        self,
        decision: TradingDecision,
        df: pd.DataFrame,
        recent_days: int = 10,
    ) -> Iterator[str]:
        """
        스트리밍 방식으로 LLM 응답을 청크 단위로 yield 합니다.
        전체 텍스트 수집 후 파싱이 필요한 경우 analyze() 를 사용하세요.

        사용 예:
            for chunk in llm.analyze_stream(decision, df):
                print(chunk, end="", flush=True)
        """
        prompt = self._builder.build(decision, df, recent_days)
        logger.info("LLM 스트리밍 시작", ticker=decision.ticker)

        with self._client.messages.stream(
            model      = self._model,
            max_tokens = self._max_tokens,
            system     = SYSTEM_PROMPT,
            messages   = [{"role": "user", "content": prompt}],
        ) as stream:
            for text in stream.text_stream:
                yield text

    # ── 내부 파싱 ─────────────────────────────────────────

    @staticmethod
    def _parse_response(raw: str, model: str) -> LLMAnalysis:
        """LLM JSON 응답을 LLMAnalysis 로 변환합니다."""
        # 마크다운 코드 블록 제거 (모델이 규칙을 어길 경우 대비)
        cleaned = re.sub(r"```(?:json)?\s*|\s*```", "", raw).strip()

        try:
            data = json.loads(cleaned)
        except json.JSONDecodeError as exc:
            logger.warning("JSON 파싱 실패, 원문 응답으로 폴백", error=str(exc))
            return LLMAnalysis(
                overall_assessment = raw,
                signal_rationale   = "JSON 파싱 실패 - 원문 응답을 확인하세요.",
                raw_response       = raw,
                model              = model,
            )

        return LLMAnalysis(
            overall_assessment = data.get("overall_assessment", ""),
            signal_rationale   = data.get("signal_rationale", ""),
            key_risks          = data.get("key_risks", []),
            opportunities      = data.get("opportunities", []),
            action_plan        = data.get("action_plan", ""),
            confidence         = float(data.get("confidence", 0.0)),
            model              = model,
            raw_response       = raw,
        )
