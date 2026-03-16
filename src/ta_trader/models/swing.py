"""
ta_trader/swing/models.py
스윙 트레이딩 6단계 분석 데이터 모델
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class SwingSignal(Enum):
    """스윙 진입/청산 신호"""
    STRONG_ENTRY = "강력진입"
    ENTRY = "진입"
    HOLD = "보류"
    PARTIAL_EXIT = "부분청산"
    EXIT = "청산"
    STRONG_EXIT = "강력청산"


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


# ── 3단계: 진입 타이밍 ────────────────────────────────────

@dataclass
class EntrySignalDetail:
    """개별 진입 신호 상세"""
    name: str                  # 신호명
    triggered: bool            # 발동 여부
    score: float               # 기여 점수
    description: str = ""


@dataclass
class EntryResult:
    """진입 타이밍 분석 결과"""
    signal: SwingSignal
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


# ── 5단계: 익절/청산 전략 ─────────────────────────────────

@dataclass
class ExitStrategyResult:
    """익절/청산 전략 결과"""
    trailing_stop: float       # ATR 기반 트레일링 스톱
    partial_exit_price: float  # 1차 부분 익절가
    full_exit_price: float     # 전량 청산가
    rsi_overbought: bool       # RSI 과매수 상태
    macd_dead_cross: bool      # MACD 데드크로스
    bb_upper_touch: bool       # BB 상단 터치
    current_signal: SwingSignal  # 현재 청산 신호
    score: float               # 0~100 (높을수록 청산 권장)
    detail: str = ""

    @property
    def should_partial_exit(self) -> bool:
        """부분 익절 권장 여부"""
        return self.current_signal in (
            SwingSignal.PARTIAL_EXIT,
        )

    @property
    def should_full_exit(self) -> bool:
        """전량 청산 권장 여부"""
        return self.current_signal in (
            SwingSignal.EXIT, SwingSignal.STRONG_EXIT,
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
    overall_signal: SwingSignal
    overall_score: float                   # 0~100
    summary: str = ""

    @property
    def is_actionable(self) -> bool:
        """실제 매수 실행 가능 여부"""
        return (
            self.market_env.is_favorable
            and self.screening.grade in (ScreeningGrade.A_PLUS, ScreeningGrade.A)
            and self.entry.signal in (SwingSignal.STRONG_ENTRY, SwingSignal.ENTRY)
            and self.position.is_acceptable
        )

    def to_dict(self) -> dict:
        """DataFrame 행 변환용"""
        return {
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
