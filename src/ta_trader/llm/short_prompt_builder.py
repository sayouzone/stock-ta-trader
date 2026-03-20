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

from ta_trader.base.prompt_builder import BasePromptBuilder
from ta_trader.models.short import TradingDecision

class ShortPromptBuilder(BasePromptBuilder[TradingDecision]):
    """TradingDecision + DataFrame → LLM 입력 프롬프트 생성"""

    # ── 섹션 빌더 ────────────────────────────────────────

    @staticmethod
    def _section_header(input_data: TradingDecision) -> str:
        return (
            f"## 분석 대상\n"
            f"- 티커: {input_data.ticker}\n"
            f"- 분석 기준일: {input_data.date}\n"
            f"- 현재가: {input_data.current_price:,.2f}\n"
            f"- 시장 국면: {input_data.market_regime.value}\n"
            f"- 적용 전략: {input_data.strategy_type.value}\n"
            f"- 복합 점수: {input_data.composite_score:+.2f} / ±100\n"
            f"- 최종 신호: **{input_data.final_signal.value}**"
            + (f"\n- 체제 판별 근거: {input_data.regime_detail}" if input_data.regime_detail else "")
        )

    @staticmethod
    def _section_indicators(input_data: TradingDecision) -> str:
        lines = ["## 기술적 지표 상세"]
        for ind in input_data.indicators:
            lines.append(
                f"- [{ind.name}] 신호={ind.signal.value} | 점수={ind.score:+.1f} | {ind.description}"
            )
        return "\n".join(lines)

    @staticmethod
    def _section_risk(input_data: TradingDecision) -> str:
        if not input_data.risk:
            return ""
        return (
            f"## 리스크 관리 수준\n"
            f"- 손절가: {input_data.stop_loss:,.2f}  "
            f"(현재가 대비 {(input_data.stop_loss / input_data.current_price - 1) * 100:.1f}%)\n"
            f"- 목표가: {input_data.take_profit:,.2f}  "
            f"(현재가 대비 +{(input_data.take_profit / input_data.current_price - 1) * 100:.1f}%)\n"
            f"- 위험보상비율: 1 : {input_data.risk_reward_ratio}"
        )
