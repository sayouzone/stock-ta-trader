"""
ta_trader/models/recommend.py
종목 추천 도메인 모델

추천 등급:
  STRONG_BUY   : 적극 매수 - 복수 지표 합치, 높은 신뢰도
  BUY          : 매수 - 전략적 진입 근거 존재
  CONDITIONAL  : 조건부 매수 - 특정 조건 충족 시 진입
  WATCH        : 관망 - 신호 혼재, 추가 확인 필요
  AVOID        : 비추천 - 매도 신호 또는 높은 리스크
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

from ta_trader.models import TradingDecision


class Grade(Enum):
    """추천 등급"""
    STRONG_BUY  = "적극매수"
    BUY         = "매수"
    CONDITIONAL = "조건부매수"
    WATCH       = "관망"
    AVOID       = "비추천"

    @property
    def emoji(self) -> str:
        return {
            Grade.STRONG_BUY:  "🟢",
            Grade.BUY:         "🔵",
            Grade.CONDITIONAL: "🟡",
            Grade.WATCH:       "⚪",
            Grade.AVOID:       "🔴",
        }[self]


@dataclass
class Rationale:
    """개별 추천 근거 항목"""
    category:    str       # "추세", "모멘텀", "변동성", "가격위치", "전략합치"
    direction:   str       # "긍정", "부정", "중립"
    summary:     str       # 한 줄 요약
    detail:      str       # 상세 설명


@dataclass
class Recommendation:
    """단일 종목 추천 결과"""
    decision:        TradingDecision
    grade:           Grade
    confidence:      float                    # 0.0 ~ 1.0
    rank:            int              = 0     # 전체 순위 (1부터)
    bullish_factors: list[Rationale]  = field(default_factory=list)
    bearish_factors: list[Rationale]  = field(default_factory=list)
    risk_factors:    list[Rationale]  = field(default_factory=list)
    entry_condition: str              = ""    # 진입 조건 요약
    action_plan:     str              = ""    # 구체적 행동 제안

    @property
    def ticker(self) -> str:
        return self.decision.ticker

    @property
    def score(self) -> float:
        return self.decision.composite_score


@dataclass
class RecommendationReport:
    """전체 추천 보고서"""
    date:              str
    recommendations:   list[Recommendation]  = field(default_factory=list)
    buy_picks:         list[Recommendation]  = field(default_factory=list)
    watch_list:        list[Recommendation]  = field(default_factory=list)
    avoid_list:        list[Recommendation]  = field(default_factory=list)
