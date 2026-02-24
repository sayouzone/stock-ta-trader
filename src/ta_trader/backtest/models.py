"""
ta_trader/backtest/models.py
백테스팅 도메인 모델
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from enum import Enum
from typing import Optional

from ta_trader.models import MarketRegime, Signal, StrategyType


class PositionSide(Enum):
    """포지션 방향"""
    LONG  = "매수"
    SHORT = "매도"


class ExitReason(Enum):
    """청산 사유"""
    STOP_LOSS      = "손절"
    TAKE_PROFIT    = "익절"
    SIGNAL_REVERSE = "신호반전"
    REGIME_CHANGE  = "체제전환"
    END_OF_DATA    = "기간종료"


@dataclass
class Trade:
    """완결된 개별 거래"""
    entry_date:    date
    exit_date:     date
    side:          PositionSide
    entry_price:   float
    exit_price:    float
    stop_loss:     float
    take_profit:   float
    pnl:           float          # 수익 (금액)
    pnl_pct:       float          # 수익률 (%)
    holding_days:  int
    exit_reason:   ExitReason
    regime:        MarketRegime
    strategy:      StrategyType
    entry_score:   float          # 진입 시 복합 점수


@dataclass
class Position:
    """현재 보유 포지션 (미결제)"""
    entry_date:   date
    side:         PositionSide
    entry_price:  float
    stop_loss:    float
    take_profit:  float
    regime:       MarketRegime
    strategy:     StrategyType
    entry_score:  float

    def check_exit(
        self,
        bar_date: date,
        high: float,
        low: float,
        close: float,
    ) -> Optional[tuple[float, ExitReason]]:
        """
        당일 고/저가로 손절·익절 체크, 종가로 최종 청산가 결정.

        Returns:
            (exit_price, exit_reason) 또는 None
        """
        if self.side == PositionSide.LONG:
            if low <= self.stop_loss:
                return self.stop_loss, ExitReason.STOP_LOSS
            if high >= self.take_profit:
                return self.take_profit, ExitReason.TAKE_PROFIT
        else:  # SHORT
            if high >= self.stop_loss:
                return self.stop_loss, ExitReason.STOP_LOSS
            if low <= self.take_profit:
                return self.take_profit, ExitReason.TAKE_PROFIT
        return None

    def close_trade(
        self,
        exit_date: date,
        exit_price: float,
        exit_reason: ExitReason,
    ) -> Trade:
        """포지션 → 완결 거래 변환"""
        if self.side == PositionSide.LONG:
            pnl = exit_price - self.entry_price
        else:
            pnl = self.entry_price - exit_price

        pnl_pct = (pnl / self.entry_price) * 100
        holding = (exit_date - self.entry_date).days

        return Trade(
            entry_date=self.entry_date,
            exit_date=exit_date,
            side=self.side,
            entry_price=self.entry_price,
            exit_price=exit_price,
            stop_loss=self.stop_loss,
            take_profit=self.take_profit,
            pnl=round(pnl, 4),
            pnl_pct=round(pnl_pct, 4),
            holding_days=max(holding, 1),
            exit_reason=exit_reason,
            regime=self.regime,
            strategy=self.strategy,
            entry_score=self.entry_score,
        )


@dataclass
class BacktestConfig:
    """백테스팅 설정"""
    initial_capital:   float = 10_000_000.0  # 초기 자본 (원)
    commission_pct:    float = 0.015         # 편도 수수료 (%)
    slippage_pct:      float = 0.05          # 슬리피지 (%)
    position_size_pct: float = 100.0         # 자본 대비 포지션 비율 (%)
    allow_short:       bool  = False         # 공매도 허용 여부
    min_score_entry:   float = 20.0          # 진입 최소 |score| 임계값
    cooldown_days:     int   = 1             # 청산 후 재진입 대기일


@dataclass
class BacktestResult:
    """백테스팅 결과"""
    ticker:         str
    period:         str
    config:         BacktestConfig
    trades:         list[Trade]         = field(default_factory=list)
    equity_curve:   list[float]         = field(default_factory=list)
    dates:          list[date]          = field(default_factory=list)
    daily_returns:  list[float]         = field(default_factory=list)

    # ── 성과 지표 (metrics.py에서 계산하여 주입) ──────────
    total_return_pct:   float = 0.0
    annual_return_pct:  float = 0.0
    max_drawdown_pct:   float = 0.0
    sharpe_ratio:       float = 0.0
    win_rate_pct:       float = 0.0
    profit_factor:      float = 0.0
    avg_holding_days:   float = 0.0
    total_trades:       int   = 0
    winning_trades:     int   = 0
    losing_trades:      int   = 0
    avg_win_pct:        float = 0.0
    avg_loss_pct:       float = 0.0
    best_trade_pct:     float = 0.0
    worst_trade_pct:    float = 0.0

    # 전략별 집계
    regime_stats:       dict  = field(default_factory=dict)
    strategy_stats:     dict  = field(default_factory=dict)
