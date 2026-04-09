"""
ta_trader/llm/swing_prompt_builder.py
SwingAnalysisResult → LLM 프롬프트 변환기

설계 원칙:
- 기술적 지표 수치를 구조화된 컨텍스트로 변환
- LLM이 JSON으로만 응답하도록 명시
- 최근 가격 추이(10일)를 요약하여 추가 컨텍스트 제공
"""

from __future__ import annotations

import json

from ta_trader.base.prompt_builder import BasePromptBuilder
from ta_trader.models.swing import SwingAnalysisResult

# 상수 참조 (detail 표시용)
from ta_trader.constants.swing import (
    POSITION_ATR_SL_MULTIPLIER as POSITION_ATR_SL_MULT,
    POSITION_ATR_TP_MULTIPLIER as POSITION_ATR_TP_MULT,
)

class SwingPromptBuilder(BasePromptBuilder[SwingAnalysisResult]):
    """TradingDecision + DataFrame → LLM 입력 프롬프트 생성"""

    # ── 섹션 빌더 ────────────────────────────────────────

    @staticmethod
    def _section_header(d: SwingAnalysisResult) -> str:
        return (
            f"## 분석 대상\n"
            f"- 티커: {d.ticker}\n"
            f"- 분석 기준일: {d.date}\n"
            f"- 현재가: {d.current_price:,.2f}\n"
            f"- 시장 국면: {d.market_env.environment.value}\n"
            f"- 적용 전략: 스윙\n"
            f"- 복합 점수: {d.market_env.score:+.2f} / ±100\n"
            f"- 최종 신호: **{d.overall_signal.value}**"
            + (f"\n- 요약: {d.summary}" if d.summary else "")
        )

    @staticmethod
    def _section_indicators(d: SwingAnalysisResult) -> str:
        lines = ["## 기술적 지표 상세"]
        return d.screening.detail

    @staticmethod
    def _section_risk(d: SwingAnalysisResult) -> str:
        if not d.position:
            return ""
        
        pos = d.position
        return (
            f"## 리스크 관리 수준\n"
            f"  진입가:   {pos.entry_price:>12,.0f}"
            f"  손절가:   {pos.stop_loss:>12,.0f}  (ATR×{POSITION_ATR_SL_MULT})"
            f"  익절가:   {pos.take_profit:>12,.0f}  (ATR×{POSITION_ATR_TP_MULT})"
            f"  R배수:    1:{pos.risk_reward_ratio}  {'✅ 적합' if pos.is_acceptable else '⚠️  부적합'}"
            f"  매수수량: {pos.position_size:>8,}주  ({pos.position_value:,.0f}원)"
            f"  비중:     {pos.portfolio_pct:>8.1f}%  (자본금: {pos.capital:,.0f}원)"
            f"  최대손실: {pos.max_loss:>12,.0f}원  (자본의 {pos.max_loss/pos.capital*100:.1f}%)"
        )
