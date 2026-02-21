"""
ta_trader/models.py
도메인 데이터 모델 (dataclass 기반)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from ta_trader.llm.models import LLMAnalysis


class Signal(Enum):
    """매매 신호"""
    STRONG_BUY  = "강력매수"
    BUY         = "매수"
    NEUTRAL     = "중립"
    SELL        = "매도"
    STRONG_SELL = "강력매도"

    @property
    def is_bullish(self) -> bool:
        return self in (Signal.BUY, Signal.STRONG_BUY)

    @property
    def is_bearish(self) -> bool:
        return self in (Signal.SELL, Signal.STRONG_SELL)


class MarketRegime(Enum):
    """시장 국면"""
    STRONG_TREND = "강한추세"
    WEAK_TREND   = "약한추세"
    SIDEWAYS     = "횡보"


@dataclass
class WeightSet:
    """지표별 가중치 묶음"""
    adx:  int
    rsi:  int
    macd: int
    bb:   int

    def __post_init__(self) -> None:
        total = self.adx + self.rsi + self.macd + self.bb
        if total != 100:
            raise ValueError(f"가중치 합계는 100이어야 합니다. 현재: {total}")


@dataclass
class IndicatorResult:
    """개별 지표 분석 결과"""
    name:        str
    raw_value:   float
    signal:      Signal
    score:       float          # -100 ~ +100
    description: str


@dataclass
class RiskLevels:
    """손절/익절 수준"""
    stop_loss:         float
    take_profit:       float
    risk_reward_ratio: float


@dataclass
class TradingDecision:
    """최종 매매 결정"""
    ticker:            str
    name:              str
    date:              str
    current_price:     float
    market_regime:     MarketRegime
    composite_score:   float           # -100 ~ +100
    final_signal:      Signal
    indicators:        list[IndicatorResult]           = field(default_factory=list)
    risk:              Optional[RiskLevels]            = None
    summary:           str                             = ""
    llm_analysis:      Optional["LLMAnalysis"]         = None

    @property
    def stop_loss(self) -> Optional[float]:
        return self.risk.stop_loss if self.risk else None

    @property
    def take_profit(self) -> Optional[float]:
        return self.risk.take_profit if self.risk else None

    @property
    def risk_reward_ratio(self) -> Optional[float]:
        return self.risk.risk_reward_ratio if self.risk else None

    def to_dict(self) -> dict:
        """스크리닝 DataFrame 행 변환용"""
        d = {
            "Ticker":      self.ticker,
            "Name":        self.name,
            "Date":        self.date,
            "Price":       self.current_price,
            "Regime":      self.market_regime.value,
            "Score":       self.composite_score,
            "Signal":      self.final_signal.value,
            "StopLoss":    self.stop_loss,
            "TakeProfit":  self.take_profit,
            "RiskReward":  self.risk_reward_ratio,
        }
        if self.llm_analysis:
            d["LLM_Confidence"] = self.llm_analysis.confidence
            d["LLM_Assessment"] = self.llm_analysis.overall_assessment[:80] + "..."
        return d
