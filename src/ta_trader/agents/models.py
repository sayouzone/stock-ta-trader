"""
ta_trader/agents/models.py
에이전트 간 통신 데이터 모델

에이전트 파이프라인:
  DataAgent → StrategyAgent → RiskAgent → ExecutionAgent

각 에이전트의 출력물은 다음 에이전트의 입력이 됩니다.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional

import pandas as pd

from ta_trader.models import (
    IndicatorResult, MarketRegime, RiskLevels, Signal,
    StrategyType, TradingDecision, TradingStyle,
)
from ta_trader.signals.regime import RegimeContext


# ── 공통 열거형 ────────────────────────────────────────────


class OrderType(Enum):
    """주문 유형"""
    MARKET = "시장가"
    LIMIT = "지정가"
    STOP_LIMIT = "스탑지정가"
    CONDITIONAL = "조건부"


class OrderSide(Enum):
    """주문 방향"""
    BUY = "매수"
    SELL = "매도"
    HOLD = "관망"


class OrderStatus(Enum):
    """주문 상태"""
    PENDING = "대기"
    SUBMITTED = "제출"
    PARTIAL_FILL = "부분체결"
    FILLED = "체결"
    CANCELLED = "취소"
    REJECTED = "거부"


class VetoReason(Enum):
    """리스크 에이전트 거부 사유"""
    RISK_TOO_HIGH = "1회 거래 리스크 초과"
    RR_RATIO_LOW = "위험보상비율 부족"
    MAX_POSITION_EXCEEDED = "최대 포지션 초과"
    CORRELATED_EXPOSURE = "상관관계 높은 포지션 집중"
    CAPITAL_INSUFFICIENT = "자본금 부족"
    DRAWDOWN_LIMIT = "최대 낙폭 한도 도달"
    SIGNAL_WEAK = "신호 강도 부족"
    APPROVED = "승인"


class ExecutionAlgorithm(Enum):
    """체결 알고리즘"""
    IMMEDIATE = "즉시체결"
    TWAP = "시간가중평균"
    VWAP = "거래량가중평균"
    SPLIT = "분할매매"


# ── Data & Analysis Agent 출력 ─────────────────────────────


@dataclass
class MarketDataReport:
    """
    Data & Analysis Agent 출력물

    시장 데이터를 수집·가공하여 정제된 데이터 포인트 및
    시장 동향 요약을 다음 에이전트에게 전달합니다.
    """
    ticker: str
    name: str
    date: str
    current_price: float

    # 원시 데이터
    ohlcv_df: pd.DataFrame                          # 지표가 계산된 전체 DataFrame
    latest_row: pd.Series = field(repr=False)        # 최신 데이터 행
    prev_row: Optional[pd.Series] = field(default=None, repr=False)

    # 기술적 지표 분석 결과
    indicator_results: list[IndicatorResult] = field(default_factory=list)

    # 시장 국면 판별
    regime_context: Optional[RegimeContext] = None

    # 펀더멘털 데이터 (yfinance info)
    fundamentals: dict = field(default_factory=dict)

    # 센티먼트 요약 (LLM 분석 시)
    sentiment_summary: str = ""

    # 메타데이터
    data_quality_score: float = 1.0  # 0.0~1.0 (데이터 품질)
    data_rows: int = 0
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


# ── Strategy & Decision Agent 출력 ─────────────────────────


@dataclass
class TradeSignal:
    """
    Strategy & Decision Agent 출력물 (개별 종목)

    분석된 데이터를 바탕으로 생성된 매매 시그널.
    리스크 에이전트가 이 시그널을 검토하고 승인/거부합니다.
    """
    ticker: str
    name: str
    date: str
    current_price: float

    # 매매 방향
    side: OrderSide
    signal: Signal
    composite_score: float                # -100 ~ +100

    # 전략 정보
    trading_style: TradingStyle
    market_regime: MarketRegime
    strategy_type: StrategyType
    regime_detail: str = ""

    # 목표 진입가 (현재가 기반)
    target_entry_price: float = 0.0       # 0이면 현재가
    suggested_stop_loss: float = 0.0
    suggested_take_profit: float = 0.0
    suggested_rr_ratio: float = 0.0

    # 개별 지표 결과 (상세 분석 첨부)
    indicator_results: list[IndicatorResult] = field(default_factory=list)

    # 스크리닝 근거
    signal_rationale: str = ""

    # 원본 마켓데이터 참조
    market_data: Optional[MarketDataReport] = field(default=None, repr=False)

    # LLM 분석 (선택적)
    llm_analysis: Optional[object] = None  # LLMAnalysis

    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class StrategyReport:
    """
    Strategy & Decision Agent 출력물 (복수 종목)

    다중 종목 스크리닝 결과를 리스크 에이전트에게 전달합니다.
    """
    date: str
    trading_style: TradingStyle
    signals: list[TradeSignal] = field(default_factory=list)

    # 상위 추천 (Risk/Reward 기준 정렬)
    top_picks: list[TradeSignal] = field(default_factory=list)

    # 회피 종목
    avoid_list: list[TradeSignal] = field(default_factory=list)

    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


# ── Risk Management Agent 출력 ─────────────────────────────


@dataclass
class PositionSize:
    """포지션 사이징 결과"""
    shares: int                 # 매매 수량 (주)
    position_value: float       # 포지션 금액
    position_pct: float         # 총 자본 대비 비율 (%)
    risk_per_trade: float       # 1회 거래 리스크 금액
    risk_pct: float             # 총 자본 대비 리스크 비율 (%)
    sizing_method: str = ""     # "kelly" | "fixed_ratio" | "equal_weight"


@dataclass
class RiskApproval:
    """
    Risk Management Agent 출력물

    매매 시그널에 대한 최종 승인/거부 결정.
    승인된 시그널만 Execution Agent로 전달됩니다.
    """
    # 원본 시그널 참조
    trade_signal: TradeSignal

    # 승인 여부
    approved: bool
    veto_reason: VetoReason = VetoReason.APPROVED

    # 포지션 사이징 (승인 시)
    position_size: Optional[PositionSize] = None

    # 확정된 손절/익절
    final_stop_loss: float = 0.0
    final_take_profit: float = 0.0
    final_rr_ratio: float = 0.0

    # 리스크 메트릭스
    max_loss_amount: float = 0.0      # 최대 손실 금액
    risk_score: float = 0.0           # 리스크 점수 (0~100, 높을수록 위험)

    # 조건부 승인 메모
    conditions: str = ""
    risk_commentary: str = ""

    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


# ── Execution Agent 출력 ───────────────────────────────────


@dataclass
class OrderRequest:
    """Execution Agent가 생성하는 주문 요청"""
    ticker: str
    side: OrderSide
    order_type: OrderType
    quantity: int
    limit_price: Optional[float] = None
    stop_price: Optional[float] = None
    algorithm: ExecutionAlgorithm = ExecutionAlgorithm.IMMEDIATE
    split_count: int = 1              # 분할 매수/매도 횟수
    time_in_force: str = "GTC"        # GTC | DAY | IOC


@dataclass
class ExecutionResult:
    """
    Execution Agent 출력물

    실제 거래 체결 내역 및 결과 로깅.
    """
    # 원본 승인 참조
    risk_approval: RiskApproval

    # 주문 정보
    order: OrderRequest

    # 체결 결과
    status: OrderStatus
    filled_quantity: int = 0
    filled_price: float = 0.0
    fill_time: str = ""

    # 슬리피지 정보
    expected_price: float = 0.0
    actual_slippage_pct: float = 0.0

    # 수수료
    commission: float = 0.0

    # 실행 로그
    execution_log: list[str] = field(default_factory=list)

    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


# ── 파이프라인 전체 결과 ──────────────────────────────────


@dataclass
class PipelineResult:
    """
    전체 에이전트 파이프라인 실행 결과

    4개 에이전트의 출력물을 모두 포함합니다.
    """
    ticker: str
    date: str

    # 각 에이전트 출력물
    market_data: Optional[MarketDataReport] = None
    trade_signal: Optional[TradeSignal] = None
    risk_approval: Optional[RiskApproval] = None
    execution_result: Optional[ExecutionResult] = None

    # 레거시 호환: TradingDecision 변환
    trading_decision: Optional[TradingDecision] = None

    # 파이프라인 메타
    pipeline_duration_ms: float = 0.0
    errors: list[str] = field(default_factory=list)

    @property
    def is_approved(self) -> bool:
        return self.risk_approval is not None and self.risk_approval.approved

    @property
    def is_executed(self) -> bool:
        return (
            self.execution_result is not None
            and self.execution_result.status == OrderStatus.FILLED
        )

    def to_trading_decision(self) -> Optional[TradingDecision]:
        """레거시 TradingDecision으로 변환 (하위 호환)"""
        if self.trading_decision:
            return self.trading_decision
        if not self.trade_signal or not self.market_data:
            return None

        ts = self.trade_signal
        ra = self.risk_approval

        risk_levels = None
        if ra and ra.approved:
            risk_levels = RiskLevels(
                stop_loss=ra.final_stop_loss,
                take_profit=ra.final_take_profit,
                risk_reward_ratio=ra.final_rr_ratio,
            )
        elif ts.suggested_stop_loss > 0:
            risk_levels = RiskLevels(
                stop_loss=ts.suggested_stop_loss,
                take_profit=ts.suggested_take_profit,
                risk_reward_ratio=ts.suggested_rr_ratio,
            )

        return TradingDecision(
            ticker=ts.ticker,
            name=ts.name,
            date=ts.date,
            current_price=ts.current_price,
            market_regime=ts.market_regime,
            strategy_type=ts.strategy_type,
            composite_score=ts.composite_score,
            final_signal=ts.signal,
            trading_style=ts.trading_style,
            indicators=ts.indicator_results,
            risk=risk_levels,
            summary=ts.signal_rationale,
            regime_detail=ts.regime_detail,
            llm_analysis=ts.llm_analysis,
        )
