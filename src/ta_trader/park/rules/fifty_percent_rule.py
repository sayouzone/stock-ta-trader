from __future__ import annotations
 
from dataclasses import dataclass
from enum import Enum
from typing import Optional
 
import pandas as pd


# ─────────────────────────────────────────────────────────────
# 공통 열거형 / 결과 구조
# ─────────────────────────────────────────────────────────────
class RuleAction(Enum):
    BUY = "매수"
    SELL = "매도"
    HOLD = "관망"
 
 
class MAZone(Enum):
    """현재가의 이동평균선 기준 위치"""
    ABOVE_MA5 = "5일선 위"               # 매수 1원칙 / 매도 1원칙 구간
    BETWEEN_MA5_MA20 = "5일선-20일선 사이"  # 매수 2원칙 / 매도 2원칙 구간
    BELOW_MA20 = "20일선 아래"            # 매수 3원칙 구간


class FiftyRuleType(Enum):
    BULL = "황소의 50% 룰"   # 전일 양봉 → 50%선이 지지
    BEAR = "곰의 50% 룰"     # 전일 음봉 → 50%선이 저항
    NONE = "해당 없음"        # 전일 도지 등
 
 
@dataclass
class FiftyRuleResult:
    """50% 룰 평가 결과"""
    rule_type: FiftyRuleType
    midpoint: float                 # 전일 봉의 50% 가격선
    is_holding: bool                # 50%선을 지키고 있는가
    current_price: float
    detail: str
 
    @property
    def is_support_held(self) -> bool:
        """황소 룰에서 지지선을 지켰는가 (매수 유효)"""
        return self.rule_type == FiftyRuleType.BULL and self.is_holding
 
    @property
    def is_resistance_held(self) -> bool:
        """곰 룰에서 저항선에 눌렸는가 (매도/공매 유효)"""
        return self.rule_type == FiftyRuleType.BEAR and self.is_holding
 
 
@dataclass
class RuleSignal:
    """매매 원칙 평가 결과"""
    action: RuleAction
    principle: int                  # 원칙 번호 (1, 2, 3)
    zone: MAZone
    confidence: float               # 0.0 ~ 1.0
    entry_hint: Optional[float] = None    # 진입 참고가
    stop_loss: Optional[float] = None     # 손절가
    rationale: str = ""             # 한국어 매매 근거


# ─────────────────────────────────────────────────────────────
# 통합 평가기
# ─────────────────────────────────────────────────────────────
@dataclass
class RuleVerdict:
    """50% 룰 + 매수/매도 원칙 통합 판정"""
    fifty: FiftyRuleResult
    buy_signal: RuleSignal
    sell_signal: RuleSignal
    zone: MAZone
 
    def summary(self) -> str:
        lines = [
            f"■ 50% 룰: {self.fifty.rule_type.value} | {self.fifty.detail}",
            f"■ 현재 구간: {self.zone.value}",
            f"■ 매수 {self.buy_signal.principle}원칙: "
            f"{self.buy_signal.action.value} (신뢰도 {self.buy_signal.confidence:.2f})",
            f"    └ {self.buy_signal.rationale}",
            f"■ 매도 {self.sell_signal.principle}원칙: "
            f"{self.sell_signal.action.value} (신뢰도 {self.sell_signal.confidence:.2f})",
            f"    └ {self.sell_signal.rationale}",
        ]
        return "\n".join(lines)


# ─────────────────────────────────────────────────────────────
# 1. 50% 룰
# ─────────────────────────────────────────────────────────────
class FiftyPercentRule:
    """박병창 50% 룰.
 
    전일 봉의 50% 가격(시가와 종가의 중간값)을 기준으로:
        · 전일이 양봉이면 → 황소의 50% 룰: 그 선이 '지지'.
          오늘 종가가 이 선 위면 황소(매수세) 우위 유지 → 매수 유효.
        · 전일이 음봉이면 → 곰의 50% 룰: 그 선이 '저항'.
          오늘 종가가 이 선 아래면 곰(매도세) 우위 유지 → 매도/공매 유효.
 
    주의: 박병창은 봉의 50%를 '시가-종가 중간'이 아니라 봉 전체(고가-저가)의
          중간으로 보기도 한다. 책의 기본은 몸통(시가~종가) 기준이며,
          use_full_range=True로 고가-저가 기준 전환 가능.
    """
 
    def __init__(self, use_full_range: bool = False):
        self.use_full_range = use_full_range
 
    def compute_midpoint(self, prev: pd.Series) -> tuple[float, FiftyRuleType]:
        """전일 봉의 50% 가격과 룰 종류 반환."""
        is_bull = prev["Close"] > prev["Open"]
        is_bear = prev["Close"] < prev["Open"]
 
        if self.use_full_range:
            midpoint = (prev["High"] + prev["Low"]) / 2.0
        else:
            midpoint = (prev["Open"] + prev["Close"]) / 2.0
 
        if is_bull:
            return float(midpoint), FiftyRuleType.BULL
        elif is_bear:
            return float(midpoint), FiftyRuleType.BEAR
        return float(midpoint), FiftyRuleType.NONE
 
    def evaluate(self, df: pd.DataFrame) -> FiftyRuleResult:
        """가장 최근 봉 기준으로 50% 룰 평가."""
        if len(df) < 2:
            raise ValueError("최소 2거래일 데이터 필요")
 
        prev = df.iloc[-2]
        curr = df.iloc[-1]
        midpoint, rule_type = self.compute_midpoint(prev)
        price = float(curr["Close"])
 
        if rule_type == FiftyRuleType.BULL:
            # 황소 룰: 종가가 50%선 위에 있으면 지지 유지
            holding = price >= midpoint
            detail = (
                f"전일 양봉 50%선 {midpoint:,.2f} "
                f"{'지지 유지 (황소 우위)' if holding else '이탈 (황소 약화)'}"
            )
        elif rule_type == FiftyRuleType.BEAR:
            # 곰 룰: 종가가 50%선 아래에 있으면 저항 유지
            holding = price <= midpoint
            detail = (
                f"전일 음봉 50%선 {midpoint:,.2f} "
                f"{'저항 유지 (곰 우위)' if holding else '돌파 (곰 약화)'}"
            )
        else:
            holding = False
            detail = f"전일 도지(중립) 50%선 {midpoint:,.2f}"
 
        return FiftyRuleResult(rule_type, midpoint, holding, price, detail)