"""
ta_trader/llm/models.py
LLM 분석 결과 데이터 모델
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class LLMAnalysis:
    """
    Claude LLM 기반 기술적 분석 해석 결과.

    Attributes:
        overall_assessment : 종합 시황 판단 (3~5문장)
        signal_rationale   : 매매 신호 근거 설명
        key_risks          : 주요 리스크 요인 목록
        opportunities      : 기회 요인 목록
        action_plan        : 구체적 액션 플랜 (진입/청산 조건 포함)
        confidence         : LLM 신뢰도 (0.0 ~ 1.0)
        model              : 사용된 LLM 모델명
        raw_response       : LLM 원문 응답 (디버깅용)
    """
    overall_assessment: str
    signal_rationale:   str
    key_risks:          list[str] = field(default_factory=list)
    opportunities:      list[str] = field(default_factory=list)
    action_plan:        str = ""
    confidence:         float = 0.0
    model:              str = ""
    raw_response:       str = ""

    def to_dict(self) -> dict:
        return {
            "overall_assessment": self.overall_assessment,
            "signal_rationale":   self.signal_rationale,
            "key_risks":          self.key_risks,
            "opportunities":      self.opportunities,
            "action_plan":        self.action_plan,
            "confidence":         self.confidence,
            "model":              self.model,
        }
