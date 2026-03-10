"""
ta_trader/models/value.py
가치 투자 5단계 분석 결과 모델

growth/models.py와 동일한 패턴:
  - ValueGrade (종합 등급)
  - StageStatus / CheckItem / StageResult (단계별 결과)
  - ValueFundamentals (펀더멘털 데이터)
  - ValueScreenResult (종합 분석 결과)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from ta_trader.models.llm import LLMAnalysis


class ValueGrade(Enum):
    """가치 투자 종합 등급"""
    STRONG_BUY  = "적극매수"    # ★★★★★  75+
    BUY         = "매수"        # ★★★★   60~74
    CONDITIONAL = "조건부매수"   # ★★★    45~59
    WATCH       = "관심관망"    # ★★     30~44
    UNFIT       = "부적합"      # ★      0~29

    @property
    def stars(self) -> str:
        return {
            ValueGrade.STRONG_BUY:  "★★★★★",
            ValueGrade.BUY:         "★★★★☆",
            ValueGrade.CONDITIONAL: "★★★☆☆",
            ValueGrade.WATCH:       "★★☆☆☆",
            ValueGrade.UNFIT:       "★☆☆☆☆",
        }[self]

    @property
    def emoji(self) -> str:
        return {
            ValueGrade.STRONG_BUY:  "🟢",
            ValueGrade.BUY:         "🔵",
            ValueGrade.CONDITIONAL: "🟡",
            ValueGrade.WATCH:       "⚪",
            ValueGrade.UNFIT:       "🔴",
        }[self]

@dataclass
class ValueFundamentals:
    """yfinance에서 추출한 가치 투자 펀더멘털 데이터"""
    # 밸류에이션
    trailing_pe:        Optional[float] = None  # Trailing PER
    forward_pe:         Optional[float] = None  # Forward PER
    pbr:                Optional[float] = None  # PBR (priceToBook)
    psr:                Optional[float] = None  # PSR (priceToSalesTrailing12Months)
    ev_ebitda:          Optional[float] = None  # EV/EBITDA
    peg_ratio:          Optional[float] = None  # PEG Ratio

    # 수익성
    roe:                Optional[float] = None  # ROE (returnOnEquity)
    operating_margin:   Optional[float] = None  # 영업이익률
    profit_margin:      Optional[float] = None  # 순이익률
    revenue_growth:     Optional[float] = None  # 매출 성장률
    earnings_growth:    Optional[float] = None  # 이익 성장률

    # 재무 건전성
    debt_to_equity:     Optional[float] = None  # 부채비율
    current_ratio:      Optional[float] = None  # 유동비율
    total_cash:         Optional[float] = None  # 총 현금
    total_debt:         Optional[float] = None  # 총 부채
    free_cashflow:      Optional[float] = None  # 잉여현금흐름
    operating_cashflow: Optional[float] = None  # 영업현금흐름
    net_income:         Optional[float] = None  # 당기순이익

    # 배당
    dividend_yield:     Optional[float] = None  # 배당수익률
    payout_ratio:       Optional[float] = None  # 배당성향

    # 기업 정보
    sector:             str = ""
    industry:           str = ""
    market_cap:         Optional[float] = None

    # EV 관련
    enterprise_value:   Optional[float] = None
    ebitda:             Optional[float] = None

    @property
    def has_valuation_data(self) -> bool:
        """밸류에이션 데이터가 하나라도 있는지"""
        return any(v is not None for v in [
            self.trailing_pe, self.forward_pe,
            self.pbr, self.psr, self.ev_ebitda,
        ])

    @property
    def has_profitability_data(self) -> bool:
        """수익성 데이터가 하나라도 있는지"""
        return any(v is not None for v in [
            self.roe, self.operating_margin, self.profit_margin,
        ])

    @property
    def fcf_yield(self) -> Optional[float]:
        """FCF Yield = FCF / 시가총액"""
        if self.free_cashflow is not None and self.market_cap and self.market_cap > 0:
            return self.free_cashflow / self.market_cap
        return None

    @property
    def cash_conversion_ratio(self) -> Optional[float]:
        """Cash Conversion Ratio = FCF / 순이익"""
        if (self.free_cashflow is not None
                and self.net_income is not None
                and self.net_income > 0):
            return self.free_cashflow / self.net_income
        return None

    @property
    def net_cash(self) -> Optional[float]:
        """순현금 = 총현금 - 총부채"""
        if self.total_cash is not None and self.total_debt is not None:
            return self.total_cash - self.total_debt
        return None


@dataclass
class ValueScreenResult:
    """5단계 가치 투자 종합 분석 결과"""
    ticker:           str
    name:             str
    date:             str
    current_price:    float

    # 5단계 결과
    stages:           list[StageResult] = field(default_factory=list)

    # 종합 평가
    total_score:      float = 0.0               # 0~100
    grade:            ValueGrade = ValueGrade.UNFIT
    fundamentals:     Optional[ValueFundamentals] = None

    # 리스크 관리
    stop_loss:        Optional[float] = None
    take_profit:      Optional[float] = None
    risk_reward:      Optional[float] = None

    # 가격 위치 정보
    high_52w:         Optional[float] = None
    low_52w:          Optional[float] = None
    sma_200:          Optional[float] = None

    # 내재가치 추정
    intrinsic_value:  Optional[float] = None    # 비교 밸류에이션 기반 추정
    margin_of_safety: Optional[float] = None    # 안전마진 (%)

    # 경고/참고
    warnings:         list[str] = field(default_factory=list)
    action:           str = ""                   # 권장 행동

    # LLM 분석 결과
    llm_analysis:      Optional["LLMAnalysis"]         = None

    def get_stage(self, num: int) -> Optional[StageResult]:
        """단계 번호로 결과 조회"""
        for s in self.stages:
            if s.stage_num == num:
                return s
        return None

    def to_dict(self) -> dict:
        """스크리닝 DataFrame 행 변환용"""
        d = {
            "Ticker":     self.ticker,
            "Name":       self.name,
            "Date":       self.date,
            "Price":      self.current_price,
            "Grade":      f"{self.grade.stars} {self.grade.value}",
            "Score":      self.total_score,
        }
        for s in self.stages:
            d[f"S{s.stage_num}"] = f"{s.score:.0f}/{s.max_score:.0f}"
        d.update({
            "52wH":       self.high_52w,
            "52wL":       self.low_52w,
            "SMA200":     self.sma_200,
            "MoS":        f"{self.margin_of_safety:.0%}" if self.margin_of_safety else "N/A",
            "StopLoss":   self.stop_loss,
            "Target":     self.take_profit,
            "R:R":        self.risk_reward,
            "Action":     self.action,
        })
        if self.fundamentals:
            d["PER"] = (
                f"{self.fundamentals.trailing_pe:.1f}"
                if self.fundamentals.trailing_pe is not None else "N/A"
            )
            d["PBR"] = (
                f"{self.fundamentals.pbr:.2f}"
                if self.fundamentals.pbr is not None else "N/A"
            )
            d["ROE"] = (
                f"{self.fundamentals.roe:.1%}"
                if self.fundamentals.roe is not None else "N/A"
            )
            d["Div_Yield"] = (
                f"{self.fundamentals.dividend_yield:.1%}"
                if self.fundamentals.dividend_yield is not None else "N/A"
            )
        if self.llm_analysis:
            d["LLM_Confidence"] = self.llm_analysis.confidence
            d["LLM_Assessment"] = self.llm_analysis.overall_assessment[:80] + "..."
        return d
