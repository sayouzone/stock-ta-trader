"""
ta_trader/llm/prompt_builder.py
TradingDecision → LLM 프롬프트 변환기

설계 원칙:
- 기술적 지표 수치를 구조화된 컨텍스트로 변환
- LLM이 JSON으로만 응답하도록 명시
- 최근 가격 추이(10일)를 요약하여 추가 컨텍스트 제공
"""

from __future__ import annotations

import json
import pandas as pd

from abc import ABC, abstractmethod
from typing import Any, Generic, TypeVar

# LLM 응답 스키마 정의
_RESPONSE_SCHEMA = {
    "overall_assessment": "종합 시황 판단 (3~5문장, 한국어)",
    "signal_rationale":   "현재 매매 신호(강력매수/매수/중립/매도/강력매도)의 근거 설명 (한국어)",
    "key_risks":          ["리스크 요인 1", "리스크 요인 2", "리스크 요인 3"],
    "opportunities":      ["기회 요인 1", "기회 요인 2"],
    "action_plan":        "구체적 투자 액션 플랜: 진입 조건, 손절 조건, 목표가 달성 시나리오 (한국어)",
    "confidence":         0.85,
}

SYSTEM_PROMPT = """\
당신은 15년 경력의 퀀트 애널리스트입니다.
기술적 분석 데이터를 기반으로 투자 의견을 제시합니다.

규칙:
1. 반드시 JSON 형식으로만 응답하세요. 마크다운 코드 블록(```)을 사용하지 마세요.
2. 모든 텍스트 필드는 한국어로 작성하세요.
3. confidence는 0.0~1.0 사이의 숫자입니다 (데이터 신뢰도, 신호 일관성 기준).
4. 투자 결정은 최종적으로 사용자 본인의 판단임을 명심하고, 과도한 확신 표현을 피하세요.
5. 데이터에 근거한 분석만 제시하고 추측성 표현을 최소화하세요.
"""

InputT = TypeVar("InputT")

class BasePromptBuilder(ABC, Generic[InputT]):
    """TradingDecision + DataFrame → LLM 입력 프롬프트 생성"""

    def build(
        self,
        intput_data: InputT,
        df: pd.DataFrame,
        recent_days: int = 10,
    ) -> str:
        """
        Args:
            decision:    기술적 분석 결과
            df:          지표가 계산된 DataFrame
            recent_days: 최근 N일 가격 추이 요약에 사용할 일수

        Returns:
            LLM user 메시지 문자열
        """
        sections = [
            self._section_header(intput_data),
            self._section_indicators(intput_data),
            self._section_risk(intput_data),
            self._section_price_trend(df, recent_days),
            self._section_instruction(),
        ]
        return "\n\n".join(sections)

    # ── 섹션 빌더 ────────────────────────────────────────

    @abstractmethod
    def _section_header(self, intput_data: InputT) -> str:
        """분석 대상 헤더 텍스트"""

    @abstractmethod
    def _section_indicators(self, intput_data: InputT) -> str:
        """기술적 지표 상세 텍스트"""

    @abstractmethod
    def _section_risk(self, intput_data: InputT) -> str:
        """리스크 관리 수준 텍스트"""

    @staticmethod
    def _section_price_trend(df: pd.DataFrame, recent_days: int) -> str:
        recent = df["Close"].tail(recent_days)
        pct_chg = (recent.iloc[-1] / recent.iloc[0] - 1) * 100
        high    = recent.max()
        low     = recent.min()
        vol_avg = df["Volume"].tail(recent_days).mean() if "Volume" in df.columns else None

        lines = [
            f"## 최근 {recent_days}일 가격 추이",
            f"- 기간 등락: {pct_chg:+.2f}%",
            f"- 기간 고가: {high:,.2f}",
            f"- 기간 저가: {low:,.2f}",
            f"- 가격 범위: {(high/low - 1)*100:.1f}%",
        ]
        if vol_avg:
            lines.append(f"- 평균 거래량: {vol_avg:,.0f}")

        # 5일씩 끊어 mini 추이 표시
        chunk = max(1, recent_days // 5)
        trend_vals = [f"{v:,.0f}" for v in recent.iloc[::chunk]]
        lines.append(f"- 가격 흐름(샘플): {' → '.join(trend_vals)}")
        return "\n".join(lines)

    @staticmethod
    def _section_instruction() -> str:
        schema_str = json.dumps(_RESPONSE_SCHEMA, ensure_ascii=False, indent=2)
        return (
            f"## 요청\n"
            f"위 기술적 분석 데이터를 바탕으로 투자 분석 의견을 제시하세요.\n"
            f"반드시 아래 JSON 스키마 형식으로만 응답하세요:\n\n"
            f"{schema_str}"
        )
