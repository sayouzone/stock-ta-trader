"""
ta_trader/models/position.py
포지션 트레이딩 7단계 분석 데이터 모델

7단계 프로세스:
  1. 시장 환경 판단   (200MA, ADX, 정배열, ATR%)
  2. 섹터/테마 선정   (섹터 RS, 자금 흐름)
  3. 종목 선정        (RS, Stage2, ADX, 52주 신고가)
  4. 매수 타이밍      (MA Pullback, Breakout, MACD, BB Squeeze)
  5. 리스크 관리      (ATR 손절/익절, 포지션 사이징, 분할매수)
  6. 보유 관리        (트레일링 스톱, 파라볼릭 SAR, 피라미딩)
  7. 매도/청산        (MA 이탈, 다이버전스, ADX 하락)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from ta_trader.models.llm import LLMAnalysis

# ── 신호 Enum ────────────────────────────────────────────

class PositionSignal(Enum):
    """포지션 트레이딩 진입/청산 신호"""
    STRONG_ENTRY = "강력진입"
    ENTRY = "진입"
    HOLD = "보류"
    PARTIAL_EXIT = "부분청산"
    EXIT = "청산"
    STRONG_EXIT = "강력청산"


class PositionMarketEnv(Enum):
    """시장 환경"""
    STRONG_BULLISH = "강세추세"
    BULLISH = "약한강세"
    SIDEWAYS = "횡보"
    BEARISH = "약세추세"
    HIGH_VOLATILITY = "고변동성"


class PositionScreenGrade(Enum):
    """종목 스크리닝 등급"""
    A_PLUS = "A+"    # 모든 조건 충족
    A = "A"          # 대부분 충족
    B = "B"          # 일부 충족
    C = "C"          # 미충족 다수
    F = "F"          # 부적격


class SectorStrength(Enum):
    """섹터 강도"""
    LEADING = "주도섹터"
    STRONG = "강세섹터"
    NEUTRAL = "중립"
    WEAK = "약세섹터"
    LAGGING = "부진섹터"


# ── 1단계: 시장 환경 판단 ────────────────────────────────

@dataclass
class MarketEnvResult:
    """시장 환경 판단 결과"""
    environment: PositionMarketEnv
    adx_value: float
    adx_trend_exists: bool         # ADX ≥ 25
    above_sma200: bool             # 가격 > SMA200
    ma_trend_score: int            # 정배열 점수 (0~4)
    atr_pct: float                 # ATR% (변동성)
    sma50_above_sma200: bool       # SMA50 > SMA200 (골든크로스 상태)
    score: float                   # 0~100
    detail: str = ""

    @property
    def is_favorable(self) -> bool:
        """포지션 매매에 유리한 환경인지"""
        return self.environment in (
            PositionMarketEnv.STRONG_BULLISH,
            PositionMarketEnv.BULLISH,
        )


# ── 2단계: 섹터/테마 선정 ────────────────────────────────

@dataclass
class SectorResult:
    """섹터 분석 결과"""
    strength: SectorStrength
    rs_vs_market: float            # 시장 대비 상대 수익률 (%)
    volume_trend: float            # 거래량 추세 비율
    score: float                   # 0~100
    detail: str = ""

    @property
    def is_leading(self) -> bool:
        """주도/강세 섹터인지"""
        return self.strength in (
            SectorStrength.LEADING,
            SectorStrength.STRONG,
        )


# ── 3단계: 종목 선정 ────────────────────────────────────

@dataclass
class ScreeningResult:
    """종목 스크리닝 결과"""
    grade: PositionScreenGrade
    rs_score: float                # 상대강도 수익률 (%)
    rs_positive: bool              # RS > 기준
    adx_sufficient: bool           # ADX ≥ 25
    di_bullish: bool               # +DI > -DI
    above_sma50: bool              # 가격 > SMA50
    above_sma200: bool             # 가격 > SMA200
    ma_aligned: bool               # 정배열 점수 ≥ 3 (Stage 2)
    near_52w_high: bool            # 52주 고가 대비 90% 이상
    volume_surge: bool             # 거래량 150%+
    score: float                   # 0~100
    checks_passed: int = 0
    checks_total: int = 8
    detail: str = ""

    @property
    def is_qualified(self) -> bool:
        """종목 스크리닝 통과 여부"""
        return self.grade in (
            PositionScreenGrade.A_PLUS,
            PositionScreenGrade.A,
            PositionScreenGrade.B,
        )


# ── 4단계: 매수 타이밍 ──────────────────────────────────

@dataclass
class EntrySignalDetail:
    """개별 진입 신호 상세"""
    name: str                      # 신호명
    triggered: bool                # 발동 여부
    score: float                   # 기여 점수
    description: str = ""


@dataclass
class EntryResult:
    """매수 타이밍 분석 결과"""
    signal: PositionSignal
    score: float                   # 0~100
    signals: list[EntrySignalDetail] = field(default_factory=list)
    ma20_pullback: bool = False    # 20일 MA 풀백 반등
    ma50_pullback: bool = False    # 50일 MA 풀백 반등
    breakout: bool = False         # 저항선 돌파 + 거래량
    macd_golden_cross: bool = False  # MACD 시그널 상향 교차
    bb_squeeze_breakout: bool = False  # BB Squeeze 후 돌파
    ema_golden_cross: bool = False  # EMA 골든크로스
    detail: str = ""

    @property
    def triggered_count(self) -> int:
        return sum(1 for s in self.signals if s.triggered)


# ── 5단계: 리스크 관리 ──────────────────────────────────

@dataclass
class RiskManagementResult:
    """리스크 관리 결과"""
    entry_price: float
    stop_loss: float               # ATR 기반 손절가
    take_profit: float             # ATR 기반 익절가
    risk_reward_ratio: float       # R배수
    risk_per_share: float          # 주당 리스크 (진입가 - 손절가)
    position_size: int             # 매수 수량 (주)
    position_value: float          # 매수 금액
    portfolio_pct: float           # 포트폴리오 비중 (%)
    capital: float                 # 투입 자본금
    atr: float                     # ATR 값
    is_acceptable: bool            # R배수 ≥ 최소 기준
    score: float                   # 0~100
    detail: str = ""

    # 분할 매수 계획
    split_buy_1: int = 0           # 1차 매수 수량
    split_buy_2: int = 0           # 2차 매수 수량
    split_buy_3: int = 0           # 3차 매수 수량

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


# ── 6단계: 보유 관리 ────────────────────────────────────

@dataclass
class HoldingManagementResult:
    """보유 관리 결과"""
    trailing_stop_atr: float       # ATR 기반 트레일링 스톱
    trailing_stop_ma50: float      # 50일 MA 기반 트레일링 스톱
    parabolic_sar: float           # 파라볼릭 SAR 값
    can_pyramid: bool              # 피라미딩 가능 여부
    pyramid_condition: str         # 피라미딩 조건 설명
    current_profit_pct: float      # 현재 추정 수익률 (진입 대비)
    score: float                   # 0~100
    detail: str = ""


# ── 7단계: 매도/청산 ────────────────────────────────────

@dataclass
class ExitResult:
    """매도/청산 분석 결과"""
    signal: PositionSignal
    ma50_broken: bool              # 50일 MA 종가 이탈
    ma200_broken: bool             # 200일 MA 이탈
    macd_divergence: bool          # MACD 다이버전스
    rsi_divergence: bool           # RSI 다이버전스
    adx_declining: bool            # ADX 피크 대비 하락
    volume_dry_up: bool            # 신고가 시 거래량 감소
    rsi_overbought: bool           # RSI 과매수
    trailing_stop_atr: float       # ATR 트레일링 스톱
    partial_exit_price: float      # 1차 부분 익절가
    full_exit_price: float         # 전량 청산가
    score: float                   # 0~100 (높을수록 청산 권장)
    detail: str = ""

    @property
    def should_partial_exit(self) -> bool:
        return self.signal == PositionSignal.PARTIAL_EXIT

    @property
    def should_full_exit(self) -> bool:
        return self.signal in (
            PositionSignal.EXIT,
            PositionSignal.STRONG_EXIT,
        )


# ── 종합 결과 ───────────────────────────────────────────

@dataclass
class PositionAnalysisResult:
    """포지션 트레이딩 7단계 종합 결과"""
    ticker: str
    name: str
    date: str
    current_price: float

    # 7단계 결과
    market_env: MarketEnvResult              # 1단계
    sector: SectorResult                     # 2단계
    screening: ScreeningResult               # 3단계
    entry: EntryResult                       # 4단계
    risk: RiskManagementResult               # 5단계
    holding: HoldingManagementResult         # 6단계
    exit_strategy: ExitResult                # 7단계

    # 종합
    overall_signal: PositionSignal
    overall_score: float                     # 0~100
    summary: str = ""
    llm_analysis: Optional["LLMAnalysis"] = None

    @property
    def is_actionable(self) -> bool:
        """실제 매수 실행 가능 여부"""
        return (
            self.market_env.is_favorable
            and self.screening.is_qualified
            and self.entry.signal in (
                PositionSignal.STRONG_ENTRY,
                PositionSignal.ENTRY,
            )
            and self.risk.is_acceptable
        )

    def to_dict(self) -> dict:
        """DataFrame 행 변환용"""
        d = {
            "Ticker": self.ticker,
            "Name": self.name,
            "Date": self.date,
            "Price": self.current_price,
            "MarketEnv": self.market_env.environment.value,
            "Sector": self.sector.strength.value,
            "Screen": self.screening.grade.value,
            "EntrySignal": self.entry.signal.value,
            "EntryScore": self.entry.score,
            "StopLoss": self.risk.stop_loss,
            "TakeProfit": self.risk.take_profit,
            "RR": self.risk.risk_reward_ratio,
            "Qty": self.risk.position_size,
            "TrailingATR": self.holding.trailing_stop_atr,
            "TrailingMA50": self.holding.trailing_stop_ma50,
            "ExitSignal": self.exit_strategy.signal.value,
            "OverallSignal": self.overall_signal.value,
            "OverallScore": self.overall_score,
        }
        if self.llm_analysis:
            d["LLM_Confidence"] = self.llm_analysis.confidence
            d["LLM_Assessment"] = self.llm_analysis.overall_assessment[:80] + "..."
        return d
