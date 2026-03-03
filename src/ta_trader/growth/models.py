"""
ta_trader/growth/models.py
100% 상승 후보 발굴 6단계 분석 결과 모델
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class GrowthGrade(Enum):
    """종합 등급"""
    STRONG_BUY  = "적극매수"    # ★★★★★  75+
    BUY         = "매수"        # ★★★★   60~74
    CONDITIONAL = "조건부매수"   # ★★★    45~59
    WATCH       = "관심관망"    # ★★     30~44
    UNFIT       = "부적합"      # ★      0~29

    @property
    def stars(self) -> str:
        return {
            GrowthGrade.STRONG_BUY:  "★★★★★",
            GrowthGrade.BUY:         "★★★★☆",
            GrowthGrade.CONDITIONAL: "★★★☆☆",
            GrowthGrade.WATCH:       "★★☆☆☆",
            GrowthGrade.UNFIT:       "★☆☆☆☆",
        }[self]

    @property
    def emoji(self) -> str:
        return {
            GrowthGrade.STRONG_BUY:  "🟢",
            GrowthGrade.BUY:         "🔵",
            GrowthGrade.CONDITIONAL: "🟡",
            GrowthGrade.WATCH:       "⚪",
            GrowthGrade.UNFIT:       "🔴",
        }[self]


class StageStatus(Enum):
    """단계별 통과 상태"""
    PASS     = "통과"
    PARTIAL  = "부분충족"
    FAIL     = "미충족"
    MANUAL   = "수동확인"   # 자동 판별 불가 (촉매 등)


@dataclass
class CheckItem:
    """개별 체크 항목 결과"""
    name:        str                    # 항목명
    passed:      bool                   # 통과 여부
    value:       Optional[float] = None # 실제 측정값
    threshold:   Optional[float] = None # 임계값
    score:       float = 0.0            # 기여 점수
    description: str = ""               # 설명


@dataclass
class StageResult:
    """단계별 분석 결과"""
    stage_num:    int                         # 1~6
    stage_name:   str                         # 단계명
    status:       StageStatus                 # 통과 상태
    score:        float                       # 이 단계 점수
    max_score:    float                       # 이 단계 최대 점수
    checks:       list[CheckItem] = field(default_factory=list)
    description:  str = ""                    # 종합 설명

    @property
    def pass_rate(self) -> float:
        """통과 비율 (0.0~1.0)"""
        if not self.checks:
            return 0.0
        passed = sum(1 for c in self.checks if c.passed)
        return passed / len(self.checks)

    @property
    def score_pct(self) -> float:
        """점수 달성률 (%)"""
        return (self.score / self.max_score * 100) if self.max_score > 0 else 0.0


@dataclass
class FundamentalData:
    """yfinance에서 추출한 펀더멘털 데이터"""
    eps_growth:         Optional[float] = None  # 분기/연간 EPS 성장률
    revenue_growth:     Optional[float] = None  # 매출 성장률
    profit_margin:      Optional[float] = None  # 영업이익률
    earnings_surprise:  Optional[float] = None  # 어닝 서프라이즈
    sector:             str = ""
    industry:           str = ""
    market_cap:         Optional[float] = None
    forward_pe:         Optional[float] = None
    peg_ratio:          Optional[float] = None

    @property
    def has_data(self) -> bool:
        """펀더멘털 데이터가 하나라도 있는지"""
        return any(v is not None for v in [
            self.eps_growth, self.revenue_growth,
            self.profit_margin, self.earnings_surprise,
        ])


@dataclass
class GrowthScreenResult:
    """6단계 종합 분석 결과"""
    ticker:           str
    name:             str
    date:             str
    current_price:    float

    # 6단계 결과
    stages:           list[StageResult] = field(default_factory=list)

    # 종합 평가
    total_score:      float = 0.0               # 0~100
    grade:            GrowthGrade = GrowthGrade.UNFIT
    fundamentals:     Optional[FundamentalData] = None

    # 리스크 관리
    stop_loss:        Optional[float] = None
    take_profit:      Optional[float] = None
    risk_reward:      Optional[float] = None

    # 가격 위치 정보
    high_52w:         Optional[float] = None
    low_52w:          Optional[float] = None
    sma_150:          Optional[float] = None
    sma_200:          Optional[float] = None

    # 경고/참고
    warnings:         list[str] = field(default_factory=list)
    action:           str = ""                   # 권장 행동

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
            "StopLoss":   self.stop_loss,
            "Target":     self.take_profit,
            "R:R":        self.risk_reward,
            "Action":     self.action,
        })
        if self.fundamentals and self.fundamentals.has_data:
            d["EPS_Growth"]  = (
                f"{self.fundamentals.eps_growth:.0%}"
                if self.fundamentals.eps_growth is not None else "N/A"
            )
            d["Rev_Growth"]  = (
                f"{self.fundamentals.revenue_growth:.0%}"
                if self.fundamentals.revenue_growth is not None else "N/A"
            )
        return d
