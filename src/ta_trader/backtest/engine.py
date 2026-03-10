"""
ta_trader/backtest/engine.py
백테스팅 엔진

워크플로:
  1. 전체 기간 OHLCV 데이터 수집 → 지표 계산
  2. warm-up 구간(지표 안정화) 이후부터 일별 순회
  3. 매일: 체제 판별 → 전략 선택 → 신호 생성 → 포지션 관리
  4. 손절/익절/신호반전/체제전환 기준 자동 청산
  5. 에쿼티 커브 + 거래 목록 반환

사용 예:
    engine = BacktestEngine("AAPL", period="2y")
    result = engine.run()
"""

from __future__ import annotations

from datetime import date

import pandas as pd

from ta_trader.backtest.metrics import compute_metrics
from ta_trader.models.backtest import (
    BacktestConfig,
    BacktestResult,
    ExitReason,
    Position,
    PositionSide,
    Trade,
)
from ta_trader.data.fetcher import DataFetcher
from ta_trader.indicators.adx import ADXAnalyzer
from ta_trader.indicators.bollinger import BollingerAnalyzer
from ta_trader.indicators.calculator import IndicatorCalculator
from ta_trader.indicators.macd import MACDAnalyzer
from ta_trader.indicators.rsi import RSIAnalyzer
from ta_trader.models import Signal
from ta_trader.risk.manager import RiskManager
from ta_trader.signals.composer import SignalComposer
from ta_trader.utils.logger import get_logger

logger = get_logger(__name__)


class BacktestEngine:
    """
    체제별 전략 자동 전환 기반 백테스팅 엔진.

    기존 분석 파이프라인(IndicatorCalculator → 4개 Analyzer → SignalComposer)을
    그대로 재사용하면서, 과거 데이터를 일별로 순회합니다.
    """

    def __init__(
        self,
        ticker: str,
        period: str = "2y",
        interval: str = "1d",
        config: BacktestConfig | None = None,
    ) -> None:
        self.ticker   = ticker
        self.period   = period
        self.interval = interval
        self.config   = config or BacktestConfig()

        self._adx_analyzer  = ADXAnalyzer()
        self._rsi_analyzer  = RSIAnalyzer()
        self._macd_analyzer = MACDAnalyzer()
        self._bb_analyzer   = BollingerAnalyzer()
        self._composer      = SignalComposer()
        self._risk_manager  = RiskManager()

    def run(self) -> BacktestResult:
        """백테스팅 실행 후 결과 반환"""
        logger.info("백테스팅 시작", ticker=self.ticker, period=self.period)

        # 1. 데이터 수집 + 지표 계산
        name, raw_df = DataFetcher(
            period=self.period, interval=self.interval,
        ).fetch(self.ticker)

        calc = IndicatorCalculator(raw_df)
        df   = calc.dataframe

        # 2. 초기화
        cfg    = self.config
        equity = cfg.initial_capital
        position: Position | None = None
        trades: list[Trade] = []
        equity_curve: list[float] = []
        dates_list: list[date] = []
        daily_returns: list[float] = []
        cooldown_remaining = 0

        # 3. 일별 순회 (인덱스 1부터 → prev_row 필요)
        for i in range(1, len(df)):
            row      = df.iloc[i]
            prev_row = df.iloc[i - 1]
            bar_date = df.index[i].date()
            prev_rows = df.iloc[:i + 1]  # 현재까지의 데이터

            high  = float(row["High"])
            low   = float(row["Low"])
            close = float(row["Close"])

            prev_equity = equity

            # ── A. 보유 포지션 체크: 손절/익절 ─────────────
            if position is not None:
                exit_check = position.check_exit(bar_date, high, low, close)
                if exit_check is not None:
                    exit_price, exit_reason = exit_check
                    trade = position.close_trade(bar_date, exit_price, exit_reason)
                    equity = self._apply_trade(equity, trade, cfg)
                    trades.append(trade)
                    position = None
                    cooldown_remaining = cfg.cooldown_days

            # ── B. 지표 분석 + 신호 생성 ──────────────────
            adx_result  = self._adx_analyzer.analyze(row)
            rsi_result  = self._rsi_analyzer.analyze(row)
            macd_result = self._macd_analyzer.analyze(row, prev_row)
            bb_result   = self._bb_analyzer.analyze(row)

            score, signal, regime_ctx = self._composer.compose_with_strategy(
                adx_result, rsi_result, macd_result, bb_result,
                row=row, prev_row=prev_row, prev_rows=prev_rows,
            )

            # ── C. 보유 중: 신호 반전 / 체제 전환 청산 ────
            if position is not None:
                exit_reason = self._check_signal_exit(position, signal, regime_ctx)
                if exit_reason is not None:
                    trade = position.close_trade(bar_date, close, exit_reason)
                    equity = self._apply_trade(equity, trade, cfg)
                    trades.append(trade)
                    position = None
                    cooldown_remaining = cfg.cooldown_days

            # ── D. 미보유: 진입 판단 ──────────────────────
            if position is None and cooldown_remaining <= 0:
                position = self._try_enter(
                    bar_date, close, score, signal, regime_ctx, row, cfg,
                )

            # ── E. 쿨다운 카운트 ──────────────────────────
            if cooldown_remaining > 0:
                cooldown_remaining -= 1

            # ── F. 에쿼티 기록 ────────────────────────────
            # 미결제 포지션의 평가손익 반영
            mark_equity = equity
            if position is not None:
                if position.side == PositionSide.LONG:
                    unrealized = (close - position.entry_price) / position.entry_price
                else:
                    unrealized = (position.entry_price - close) / position.entry_price
                mark_equity = equity * (1 + unrealized * cfg.position_size_pct / 100)

            equity_curve.append(round(mark_equity, 2))
            dates_list.append(bar_date)

            if prev_equity > 0:
                daily_returns.append((mark_equity - prev_equity) / prev_equity)

        # 4. 기간 종료 시 미결제 포지션 강제 청산
        if position is not None and len(df) > 0:
            last_close = float(df.iloc[-1]["Close"])
            last_date  = df.index[-1].date()
            trade = position.close_trade(last_date, last_close, ExitReason.END_OF_DATA)
            equity = self._apply_trade(equity, trade, cfg)
            trades.append(trade)
            if equity_curve:
                equity_curve[-1] = round(equity, 2)

        # 5. 결과 조립 + 지표 계산
        result = BacktestResult(
            ticker=self.ticker,
            period=self.period,
            config=cfg,
            trades=trades,
            equity_curve=equity_curve,
            dates=dates_list,
            daily_returns=daily_returns,
        )

        result = compute_metrics(result)

        logger.info(
            "백테스팅 완료",
            ticker=self.ticker,
            trades=len(trades),
            return_pct=result.total_return_pct,
            sharpe=result.sharpe_ratio,
        )
        return result

    # ── 내부 메서드 ──────────────────────────────────────

    def _try_enter(
        self, bar_date, close, score, signal, regime_ctx, row, cfg,
    ) -> Position | None:
        """진입 조건 체크 후 포지션 생성"""
        if abs(score) < cfg.min_score_entry:
            return None

        if signal.is_bullish:
            side = PositionSide.LONG
        elif signal.is_bearish and cfg.allow_short:
            side = PositionSide.SHORT
        else:
            return None

        risk = self._risk_manager.calculate(close, row, signal)

        # 슬리피지 적용
        slip = close * (cfg.slippage_pct / 100)
        entry_price = close + slip if side == PositionSide.LONG else close - slip

        return Position(
            entry_date=bar_date,
            side=side,
            entry_price=round(entry_price, 4),
            stop_loss=risk.stop_loss,
            take_profit=risk.take_profit,
            regime=regime_ctx.regime,
            strategy=regime_ctx.strategy,
            entry_score=score,
        )

    @staticmethod
    def _check_signal_exit(position, signal, regime_ctx) -> ExitReason | None:
        """신호 반전 또는 체제 전환 시 청산 사유 반환"""
        if position.side == PositionSide.LONG and signal.is_bearish:
            return ExitReason.SIGNAL_REVERSE
        if position.side == PositionSide.SHORT and signal.is_bullish:
            return ExitReason.SIGNAL_REVERSE
        # 체제가 바뀌면서 현재 전략이 더 이상 유효하지 않을 때
        if regime_ctx.strategy != position.strategy:
            return ExitReason.REGIME_CHANGE
        return None

    @staticmethod
    def _apply_trade(equity: float, trade: Trade, cfg: BacktestConfig) -> float:
        """거래 손익 + 수수료를 에쿼티에 반영"""
        position_value = equity * (cfg.position_size_pct / 100)
        pnl_amount = position_value * (trade.pnl_pct / 100)

        # 양방향 수수료 (진입 + 청산)
        commission = position_value * (cfg.commission_pct / 100) * 2

        return round(equity + pnl_amount - commission, 2)
