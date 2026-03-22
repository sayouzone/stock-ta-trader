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
from ta_trader.models.position import PositionAnalysisResult

from ta_trader.constants.position import (
    RISK_ATR_SL_MULTIPLIER,
    RISK_ATR_TP_MULTIPLIER,
)


class PositionPromptBuilder(BasePromptBuilder[PositionAnalysisResult]):
    """TradingDecision + DataFrame → LLM 입력 프롬프트 생성"""

    # ── 섹션 빌더 ────────────────────────────────────────

    @staticmethod
    def _section_header(d: PositionAnalysisResult) -> str:
        env = d.market_env
        sec = d.sector
        return (
            f"## 시장 환경 판단\n"
            f"- 티커: {d.ticker}\n"
            f"- 분석 기준일: {d.date}\n"
            f"- 현재가: {d.current_price:,.2f}\n"
            f"- 시장 환경: {env.environment.value}\n"
            f"     {env.detail}\n"
            f"- 적용 전략: 포지션\n"
            f"- 환경 점수: {env.score:+.2f}/100점\n"
            f"## 섹터/테마 선정\n"
            f"- 강도: {sec.strength.value}\n"
            f"     {sec.detail}\n"
            f"- 선정 점수: {sec.score:.0f}/100점\n"
        )

    @staticmethod
    def _section_indicators(d: PositionAnalysisResult) -> str:
        scr = d.screening
        lines = ["## 종목 스크리닝"]
        return (
            f"- 선정 점수: {scr.score:.0f}/100점\n"
            f"- 등급: {scr.grade.value}  ({scr.checks_passed}/{scr.checks_total} 통과)\n"
            f"     {scr.detail}"
        )

    @staticmethod
    def _section_risk(d: PositionAnalysisResult) -> str:
        if not d.risk:
            return ""
        
        risk = d.risk
        return (
            f"## 리스크 관리 수준\n"
            f"- 진입가: {risk.entry_price:>12,.0f}\n"
            f"- 손절가: {risk.stop_loss:>12,.0f}  (ATR×{RISK_ATR_SL_MULTIPLIER})\n"
            f"- 익절가: {risk.take_profit:>12,.0f}  (ATR×{RISK_ATR_TP_MULTIPLIER})\n"
            f"- R배수: 1:{risk.risk_reward_ratio}  {'✅ 적합' if risk.is_acceptable else '⚠️  부적합'}\n"
            f"- 총 매수수량: {risk.position_size:>8,}주  ({risk.position_value:,.0f}원)\n"
            f"    1차 매수: {risk.split_buy_1:>6,}주  (피벗/풀백 확인 시)\n"
            f"    2차 매수: {risk.split_buy_2:>6,}주  (추가 상승 확인 시)\n"
            f"    3차 매수: {risk.split_buy_3:>6,}주  (추세 안착 확인 시)\n"
            f"- 비중: {risk.portfolio_pct:>8.1f}%  (자본금: {risk.capital:,.0f}원)\n"
            f"- 최대손실: {risk.max_loss:>12,.0f}원  (자본의 {risk.max_loss/risk.capital*100:.1f}%)\n"
            f"- 피보목표: 161.8%={risk.fibo_target_161:,.0f}  261.8%={risk.fibo_target_261:,.0f}\n" if risk.fibo_target_161 > 0 else ""
            f"## 보유 관리\n"
            f"- 트레일링(ATR): {hold.trailing_stop_atr:>10,.0f}\n"
            f"- 트레일링(MA50): {hold.trailing_stop_ma50:>10,.0f}\n"
            f"- 파라볼릭 SAR: {hold.parabolic_sar:>10,.0f}\n"
            f"- 현재 수익률: {hold.current_profit_pct:>+8.1f}%\n"
            f"- 피라미딩: {'✅ ' if hold.can_pyramid else '❌ '}{hold.pyramid_condition}\n"
        )
