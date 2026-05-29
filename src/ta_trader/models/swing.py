"""
ta_trader/models/swing.py
스윙 트레이딩 6단계 분석 데이터 모델
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Optional

from ta_trader.models.base import OrderSide, TradingStyle
#from ta_trader.models import TradingStyle

if TYPE_CHECKING:
    from ta_trader.models.llm import LLMAnalysis


class MarketEnvironment(Enum):
    """시장 환경"""
    BULLISH_TREND = "강세추세"
    BULLISH_WEAK = "약세강세"
    BEARISH_TREND = "약세추세"
    SIDEWAYS = "횡보"
    HIGH_VOLATILITY = "고변동성"


class ScreeningGrade(Enum):
    """스크리닝 등급"""
    A_PLUS = "A+"   # 모든 조건 충족
    A = "A"         # 대부분 충족
    B = "B"         # 일부 충족
    C = "C"         # 미충족 다수
    F = "F"         # 부적격


# ── 1단계: 시장 환경 ──────────────────────────────────────

@dataclass
class MarketEnvResult:
    """시장 환경 판단 결과"""
    environment: MarketEnvironment
    adx_value: float
    adx_trend_exists: bool     # ADX ≥ 25
    above_sma200: bool         # 가격 > SMA200
    ma_trend_score: int        # 정배열 점수 (0~4)
    atr_pct: float             # ATR% (변동성)
    score: float               # 0~100
    detail: str = ""

    @property
    def is_favorable(self) -> bool:
        """스윙 매매에 유리한 환경인지"""
        return self.environment in (
            MarketEnvironment.BULLISH_TREND,
            MarketEnvironment.BULLISH_WEAK,
        )

    @classmethod
    def from_dict(cls, d: dict) -> "MarketEnvResult":
        return cls(
            environment      = _restore_enum(MarketEnvironment, d["environment"]),
            adx_value        = float(d["adx_value"]),
            adx_trend_exists = bool(d["adx_trend_exists"]),
            above_sma200     = bool(d["above_sma200"]),
            ma_trend_score   = int(d["ma_trend_score"]),
            atr_pct          = float(d["atr_pct"]),
            score            = float(d["score"]),
            detail           = d.get("detail", ""),
        )


# ── 2단계: 종목 스크리닝 ──────────────────────────────────

@dataclass
class ScreeningResult:
    """종목 스크리닝 결과"""
    grade: ScreeningGrade
    volume_surge: bool         # 거래량 급증 여부
    volume_ratio: float        # 거래량 비율
    adx_sufficient: bool       # ADX ≥ 20
    di_bullish: bool           # +DI > -DI
    ma_aligned: bool           # 정배열 점수 ≥ 2
    rs_positive: bool          # 상대강도 > 0
    score: float               # 0~100
    checks_passed: int = 0
    checks_total: int = 5
    detail: str = ""

    @classmethod
    def from_dict(cls, d: dict) -> "ScreeningResult":
        return cls(
            grade          = _restore_enum(ScreeningGrade, d["grade"]),
            volume_surge   = bool(d["volume_surge"]),
            volume_ratio   = float(d["volume_ratio"]),
            adx_sufficient = bool(d["adx_sufficient"]),
            di_bullish     = bool(d["di_bullish"]),
            ma_aligned     = bool(d["ma_aligned"]),
            rs_positive    = bool(d["rs_positive"]),
            score          = float(d["score"]),
            checks_passed  = int(d.get("checks_passed", 0)),
            checks_total   = int(d.get("checks_total", 5)),
            detail         = d.get("detail", ""),
        )


# ── 3단계: 진입 타이밍 ────────────────────────────────────

@dataclass
class EntrySignalDetail:
    """개별 진입 신호 상세"""
    name: str                  # 신호명
    triggered: bool            # 발동 여부
    score: float               # 기여 점수
    description: str = ""

    @classmethod
    def from_dict(cls, d: dict) -> "EntrySignalDetail":
        return cls(
            name        = d["name"],
            triggered   = bool(d["triggered"]),
            score       = float(d["score"]),
            description = d.get("description", ""),
        )


@dataclass
class EntryResult:
    """진입 타이밍 분석 결과"""
    signal: OrderSide
    score: float               # 0~100
    signals: list[EntrySignalDetail] = field(default_factory=list)
    macd_golden_cross: bool = False
    rsi_oversold_bounce: bool = False
    bb_lower_bounce: bool = False
    bb_squeeze_breakout: bool = False
    fibo_golden_zone: bool = False
    ema_golden_cross: bool = False
    detail: str = ""

    @property
    def triggered_count(self) -> int:
        return sum(1 for s in self.signals if s.triggered)

    @classmethod
    def from_dict(cls, d: dict) -> "EntryResult":
        return cls(
            signal              = _restore_enum(OrderSide, d["signal"]),
            score               = float(d["score"]),
            signals             = [
                EntrySignalDetail.from_dict(s)
                for s in d.get("signals", [])
            ],
            macd_golden_cross   = bool(d.get("macd_golden_cross",   False)),
            rsi_oversold_bounce = bool(d.get("rsi_oversold_bounce", False)),
            bb_lower_bounce     = bool(d.get("bb_lower_bounce",     False)),
            bb_squeeze_breakout = bool(d.get("bb_squeeze_breakout", False)),
            fibo_golden_zone    = bool(d.get("fibo_golden_zone",    False)),
            ema_golden_cross    = bool(d.get("ema_golden_cross",    False)),
            detail              = d.get("detail", ""),
        )


# ── 4단계: 포지션 사이징/리스크 ───────────────────────────

@dataclass
class PositionSizingResult:
    """포지션 사이징 결과"""
    entry_price: float
    stop_loss: float
    take_profit: float
    risk_reward_ratio: float
    risk_per_share: float      # 주당 리스크 (진입가 - 손절가)
    position_size: int         # 매수 수량 (주)
    position_value: float      # 매수 금액
    portfolio_pct: float       # 포트폴리오 비중 (%)
    capital: float             # 투입 자본금
    atr: float                 # ATR 값
    is_acceptable: bool        # R배수 ≥ 최소 기준
    score: float               # 0~100
    detail: str = ""

    # 피보나치 기반 목표가
    fibo_target_161: float = 0.0
    fibo_target_261: float = 0.0

    @property
    def max_loss(self) -> float:
        """최대 손실 금액"""
        return self.risk_per_share * self.position_size

    @property
    def expected_profit(self) -> float:
        """기대 수익 금액"""
        return abs(self.take_profit - self.entry_price) * self.position_size

    @classmethod
    def from_dict(cls, d: dict) -> "PositionSizingResult":
        return cls(
            entry_price       = float(d["entry_price"]),
            stop_loss         = float(d["stop_loss"]),
            take_profit       = float(d["take_profit"]),
            risk_reward_ratio = float(d["risk_reward_ratio"]),
            risk_per_share    = float(d["risk_per_share"]),
            position_size     = int(d["position_size"]),
            position_value    = float(d["position_value"]),
            portfolio_pct     = float(d["portfolio_pct"]),
            capital           = float(d["capital"]),
            atr               = float(d["atr"]),
            is_acceptable     = bool(d["is_acceptable"]),
            score             = float(d["score"]),
            detail            = d.get("detail", ""),
            fibo_target_161   = float(d.get("fibo_target_161", 0.0)),
            fibo_target_261   = float(d.get("fibo_target_261", 0.0)),
        )


# ── 5단계: 익절/청산 전략 ─────────────────────────────────

@dataclass
class ExitStrategyResult:
    """익절/청산 전략 결과"""
    signal: OrderSide          # 현재 청산 신호

    trailing_stop: float       # ATR 기반 트레일링 스톱
    partial_exit_price: float  # 1차 부분 익절가
    full_exit_price: float     # 전량 청산가
    rsi_overbought: bool       # RSI 과매수 상태
    
    macd_dead_cross: bool      # MACD 데드크로스
    bb_upper_touch: bool       # BB 상단 터치

    score: float               # 0~100 (높을수록 청산 권장)
    detail: str = ""

    @property
    def should_partial_exit(self) -> bool:
        """부분 익절 권장 여부"""
        return self.signal in (
            OrderSide.PARTIAL_EXIT,
        )

    @property
    def should_full_exit(self) -> bool:
        """전량 청산 권장 여부"""
        return self.signal in (
            OrderSide.EXIT, OrderSide.STRONG_EXIT,
        )

    @classmethod
    def from_dict(cls, d: dict) -> "ExitStrategyResult":
        return cls(
            signal             = _restore_enum(OrderSide, d["signal"]),
            trailing_stop      = float(d["trailing_stop"]),
            partial_exit_price = float(d["partial_exit_price"]),
            full_exit_price    = float(d["full_exit_price"]),
            rsi_overbought     = bool(d["rsi_overbought"]),
            macd_dead_cross    = bool(d["macd_dead_cross"]),
            bb_upper_touch     = bool(d["bb_upper_touch"]),
            score              = float(d["score"]),
            detail             = d.get("detail", ""),
        )


# ── 종합 결과 ─────────────────────────────────────────────

@dataclass
class SwingAnalysisResult:
    """스윙 트레이딩 6단계 종합 결과"""
    ticker: str
    name: str
    date: str
    current_price: float

    # 6단계 결과
    market_env: MarketEnvResult            # 1단계
    screening: ScreeningResult             # 2단계
    entry: EntryResult                     # 3단계
    position: PositionSizingResult         # 4단계
    exit_strategy: ExitStrategyResult      # 5단계

    # 종합
    overall_signal: OrderSide
    overall_score:  float                   # 0~100
    summary: str = ""
    trading_style:  TradingStyle            = TradingStyle.SWING
    llm_analysis:   Optional["LLMAnalysis"] = None

    @property
    def is_actionable(self) -> bool:
        """실제 매수 실행 가능 여부"""
        return (
            self.market_env.is_favorable
            and self.screening.grade in (ScreeningGrade.A_PLUS, ScreeningGrade.A)
            and self.entry.signal in (OrderSide.STRONG_ENTRY, OrderSide.ENTRY)
            and self.position.is_acceptable
        )

    def to_dict(self) -> dict:
        """DataFrame 행 변환용"""
        d = {
            "Ticker": self.ticker,
            "Name": self.name,
            "Date": self.date,
            "Price": self.current_price,
            "MarketEnv": self.market_env.environment.value,
            "Screen": self.screening.grade.value,
            "EntrySignal": self.entry.signal.value,
            "EntryScore": self.entry.score,
            "StopLoss": self.position.stop_loss,
            "TakeProfit": self.position.take_profit,
            "RR": self.position.risk_reward_ratio,
            "Qty": self.position.position_size,
            "TrailingStop": self.exit_strategy.trailing_stop,
            "OverallSignal": self.overall_signal.value,
            "OverallScore": self.overall_score,
        }
        if self.llm_analysis:
            d["LLM_Confidence"] = self.llm_analysis.confidence
            d["LLM_Assessment"] = self.llm_analysis.overall_assessment[:80] + "..."
        return d

    @classmethod
    def from_dict(cls, d: dict) -> "SwingAnalysisResult":
        """
        직렬화된 dict → SwingAnalysisResult 완전 복원.

        저장 시 _to_serializable() 또는 dataclasses.asdict()로
        직렬화된 dict를 받아 모든 서브 dataclass와 Enum을 재구성한다.

        Args:
            d: JSON 역직렬화 dict

        Returns:
            SwingAnalysisResult 인스턴스

        Example::

            with open("005930.KS_2026-04-30.json") as f:
                payload = json.load(f)
            result = SwingAnalysisResult.from_dict(payload["analysis"])
        """
        # LLMAnalysis는 순환 참조 방지를 위해 런타임에 import
        llm_analysis: Optional["LLMAnalysis"] = None
        if d.get("llm_analysis") is not None:
            try:
                from ta_trader.models.llm import LLMAnalysis
                llm_analysis = LLMAnalysis.from_dict(d["llm_analysis"])
            except (ImportError, Exception):
                # LLM 모듈 없거나 역직렬화 실패 시 None 유지
                llm_analysis = None

        return cls(
            ticker         = str(d["ticker"]),
            name           = str(d["name"]),
            date           = str(d["date"]),
            current_price  = float(d["current_price"]),
            market_env     = MarketEnvResult.from_dict(d["market_env"]),
            screening      = ScreeningResult.from_dict(d["screening"]),
            entry          = EntryResult.from_dict(d["entry"]),
            position       = PositionSizingResult.from_dict(d["position"]),
            exit_strategy  = ExitStrategyResult.from_dict(d["exit_strategy"]),
            overall_signal = _restore_enum(OrderSide, d["overall_signal"]),
            overall_score  = float(d["overall_score"]),
            summary        = d.get("summary", ""),
            trading_style  = _restore_enum(TradingStyle, d.get("trading_style", TradingStyle.SWING.value)),
            llm_analysis   = llm_analysis,
        )
