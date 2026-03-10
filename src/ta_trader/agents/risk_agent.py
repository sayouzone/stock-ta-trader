"""
ta_trader/agents/risk_agent.py
Risk Management Agent — 감정에 휘둘리지 않고 자본을 보호하는 브레이크

역할:
  Strategy Agent의 매매 시그널을 검토하고,
  계좌의 생존을 위해 최종 승인하거나 거부(Veto)합니다.

주요 기능:
  - 포지션 사이징 (Position Sizing): 켈리 공식 또는 고정 비율로 투자 비중 결정
  - 손익비 계산 및 제한: 손절매(Stop-Loss) 및 이익 실현(Take-Profit) 가격 설정
  - 리스크 제한 공식: 1회 거래당 리스크를 총 자본의 1~2%로 제한

출력물:
  RiskApproval — 매매 시그널 최종 승인 여부, 구체적인 매매 수량(주), 손절/익절 라인
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Optional

from ta_trader.base.agent import BaseAgent
from ta_trader.models.agent import (
    OrderSide, PositionSize, RiskApproval,
    TradeSignal, VetoReason,
)
from ta_trader.models import Signal


@dataclass
class RiskConfig:
    """리스크 관리 설정"""
    # 총 투자 자본금
    total_capital: float = 10_000_000.0     # 1천만 원

    # 1회 거래당 최대 리스크 비율 (총 자본 대비)
    max_risk_per_trade_pct: float = 0.02    # 2%

    # 최대 포지션 비율 (총 자본 대비)
    max_position_pct: float = 0.20          # 20%

    # 최소 위험보상비율
    min_rr_ratio: float = 1.5

    # 최대 동시 포지션 수
    max_concurrent_positions: int = 10

    # 최대 포트폴리오 낙폭 한도 (%)
    max_drawdown_pct: float = 0.20          # 20%

    # 최소 신호 강도 (절대값 점수)
    min_signal_score: float = 15.0

    # 포지션 사이징 방법
    sizing_method: str = "fixed_ratio"      # "kelly" | "fixed_ratio" | "equal_weight"

    # 켈리 공식 파라미터 (sizing_method == "kelly")
    kelly_win_rate: float = 0.55            # 예상 승률
    kelly_avg_win_loss_ratio: float = 2.0   # 평균 이익/손실 비율
    kelly_fraction: float = 0.25            # Kelly 비율 (full Kelly의 1/4)

    # 현재 보유 포지션 수 (외부에서 주입)
    current_positions: int = 0

    # 현재 포트폴리오 낙폭 (외부에서 주입)
    current_drawdown_pct: float = 0.0


class RiskAgent(BaseAgent[TradeSignal, RiskApproval]):
    """
    Risk Management Agent

    Strategy Agent의 매매 시그널을 받아 다단계 리스크 검증을 수행합니다.
    모든 검증을 통과한 시그널만 승인(approved=True)되며,
    하나라도 실패하면 거부(Veto)됩니다.

    검증 순서:
      1. 신호 강도 검증 → 너무 약한 시그널 거부
      2. 위험보상비율 검증 → 최소 R/R 기준 미달 거부
      3. 포지션 수 제한 → 동시 포지션 초과 거부
      4. 최대 낙폭 검증 → 포트폴리오 낙폭 한도 도달 시 거부
      5. 포지션 사이징 → 매매 수량 산출
      6. 1회 거래 리스크 검증 → 자본의 1~2% 초과 시 수량 조정

    사용 예:
        agent = RiskAgent(config=RiskConfig(total_capital=50_000_000))
        approval = agent.execute(trade_signal)
    """

    def __init__(self, config: Optional[RiskConfig] = None) -> None:
        super().__init__()
        self.config = config or RiskConfig()

    @property
    def name(self) -> str:
        return "리스크 관리 에이전트"

    @property
    def role(self) -> str:
        return "매매 시그널 검증 및 포지션 사이징"

    def execute(self, input_data: TradeSignal) -> RiskApproval:
        """
        매매 시그널 리스크 검증 파이프라인

        Args:
            input_data: StrategyAgent의 출력물 (TradeSignal)

        Returns:
            RiskApproval: 승인/거부 결정 + 포지션 사이징 + 확정 손절/익절
        """
        self._logger.info(
            "리스크 검증 시작",
            ticker=input_data.ticker,
            signal=input_data.signal.value,
            score=input_data.composite_score,
        )

        ts = input_data
        cfg = self.config

        # ── 관망 시그널은 즉시 승인 (실행 불필요) ──────
        if ts.side == OrderSide.HOLD:
            return RiskApproval(
                trade_signal=ts,
                approved=True,
                veto_reason=VetoReason.APPROVED,
                risk_commentary="관망 시그널 — 포지션 변경 없음",
            )

        # ── 1. 신호 강도 검증 ──────────────────────────
        if abs(ts.composite_score) < cfg.min_signal_score:
            return self._reject(ts, VetoReason.SIGNAL_WEAK,
                f"신호 강도 부족: |{ts.composite_score:.1f}| < {cfg.min_signal_score:.1f}")

        # ── 2. 위험보상비율 검증 ───────────────────────
        if ts.suggested_rr_ratio < cfg.min_rr_ratio and ts.side == OrderSide.BUY:
            return self._reject(ts, VetoReason.RR_RATIO_LOW,
                f"R/R 비율 부족: 1:{ts.suggested_rr_ratio:.2f} < 1:{cfg.min_rr_ratio:.2f}")

        # ── 3. 최대 동시 포지션 검증 ──────────────────
        if (ts.side == OrderSide.BUY
            and cfg.current_positions >= cfg.max_concurrent_positions):
            return self._reject(ts, VetoReason.MAX_POSITION_EXCEEDED,
                f"동시 포지션 한도 도달: {cfg.current_positions}/{cfg.max_concurrent_positions}")

        # ── 4. 최대 낙폭 검증 ─────────────────────────
        if cfg.current_drawdown_pct >= cfg.max_drawdown_pct:
            return self._reject(ts, VetoReason.DRAWDOWN_LIMIT,
                f"포트폴리오 낙폭 한도 도달: {cfg.current_drawdown_pct:.1%} >= {cfg.max_drawdown_pct:.1%}")

        # ── 5. 포지션 사이징 ──────────────────────────
        position = self._calculate_position_size(ts)

        if position is None:
            return self._reject(ts, VetoReason.CAPITAL_INSUFFICIENT,
                "포지션 사이징 실패: 자본금 부족 또는 손절 간격 0")

        # ── 6. 1회 거래 리스크 최종 검증 ──────────────
        if position.risk_pct > cfg.max_risk_per_trade_pct * 100:
            # 수량 축소 시도
            position = self._adjust_position_for_risk(ts, position)
            if position is None:
                return self._reject(ts, VetoReason.RISK_TOO_HIGH,
                    f"리스크 조정 후에도 자본의 {cfg.max_risk_per_trade_pct:.1%} 초과")

        # ── 7. 확정 손절/익절 라인 ────────────────────
        final_sl = ts.suggested_stop_loss
        final_tp = ts.suggested_take_profit
        final_rr = ts.suggested_rr_ratio

        max_loss = position.risk_per_trade
        risk_score = self._calculate_risk_score(ts, position)

        commentary = self._build_commentary(ts, position, risk_score)

        self._logger.info(
            "리스크 검증 승인",
            ticker=ts.ticker,
            shares=position.shares,
            risk_pct=f"{position.risk_pct:.2f}%",
            rr_ratio=f"1:{final_rr}",
        )

        return RiskApproval(
            trade_signal=ts,
            approved=True,
            veto_reason=VetoReason.APPROVED,
            position_size=position,
            final_stop_loss=final_sl,
            final_take_profit=final_tp,
            final_rr_ratio=final_rr,
            max_loss_amount=max_loss,
            risk_score=risk_score,
            risk_commentary=commentary,
        )

    def execute_batch(
        self,
        signals: list[TradeSignal],
    ) -> list[RiskApproval]:
        """복수 시그널 일괄 리스크 검증"""
        approvals = []
        for signal in signals:
            approval = self.execute(signal)
            approvals.append(approval)
            # 승인된 매수 시그널이면 포지션 카운트 증가
            if approval.approved and signal.side == OrderSide.BUY:
                self.config.current_positions += 1
        return approvals

    # ── 포지션 사이징 ────────────────────────────────────

    def _calculate_position_size(
        self,
        ts: TradeSignal,
    ) -> Optional[PositionSize]:
        """투자 비중 및 매매 수량 산출"""
        cfg = self.config
        method = cfg.sizing_method

        if method == "kelly":
            return self._kelly_sizing(ts)
        elif method == "equal_weight":
            return self._equal_weight_sizing(ts)
        else:
            return self._fixed_ratio_sizing(ts)

    def _fixed_ratio_sizing(self, ts: TradeSignal) -> Optional[PositionSize]:
        """
        고정 비율 포지션 사이징

        공식: 매매 수량 = (총 자본 × 최대 리스크 비율) / 주당 리스크
        """
        cfg = self.config
        price = ts.current_price

        if price <= 0 or ts.suggested_stop_loss <= 0:
            return None

        # 주당 리스크 = |진입가 - 손절가|
        risk_per_share = abs(price - ts.suggested_stop_loss)
        if risk_per_share < 1e-6:
            return None

        # 최대 리스크 금액 = 총 자본 × 리스크 비율
        max_risk_amount = cfg.total_capital * cfg.max_risk_per_trade_pct

        # 매매 수량 계산
        shares = int(max_risk_amount / risk_per_share)
        if shares <= 0:
            return None

        # 최대 포지션 금액 제한
        max_position_value = cfg.total_capital * cfg.max_position_pct
        max_shares_by_position = int(max_position_value / price)
        shares = min(shares, max_shares_by_position)

        if shares <= 0:
            return None

        position_value = shares * price
        risk_amount = shares * risk_per_share

        return PositionSize(
            shares=shares,
            position_value=round(position_value, 2),
            position_pct=round(position_value / cfg.total_capital * 100, 2),
            risk_per_trade=round(risk_amount, 2),
            risk_pct=round(risk_amount / cfg.total_capital * 100, 2),
            sizing_method="fixed_ratio",
        )

    def _kelly_sizing(self, ts: TradeSignal) -> Optional[PositionSize]:
        """
        켈리 공식 기반 포지션 사이징

        Kelly% = W - [(1 - W) / R]
        W = 승률, R = 평균 이익/손실 비율

        full Kelly의 일부(kelly_fraction)만 적용하여 보수적으로 운용
        """
        cfg = self.config
        price = ts.current_price

        if price <= 0 or ts.suggested_stop_loss <= 0:
            return None

        w = cfg.kelly_win_rate
        r = cfg.kelly_avg_win_loss_ratio

        kelly_pct = w - ((1 - w) / r)
        kelly_pct = max(0, kelly_pct) * cfg.kelly_fraction

        # 최대 포지션 비율로 상한 적용
        kelly_pct = min(kelly_pct, cfg.max_position_pct)

        position_value = cfg.total_capital * kelly_pct
        shares = int(position_value / price)
        if shares <= 0:
            return None

        risk_per_share = abs(price - ts.suggested_stop_loss)
        risk_amount = shares * risk_per_share

        return PositionSize(
            shares=shares,
            position_value=round(shares * price, 2),
            position_pct=round(kelly_pct * 100, 2),
            risk_per_trade=round(risk_amount, 2),
            risk_pct=round(risk_amount / cfg.total_capital * 100, 2),
            sizing_method=f"kelly({kelly_pct:.1%})",
        )

    def _equal_weight_sizing(self, ts: TradeSignal) -> Optional[PositionSize]:
        """균등 비중 포지션 사이징"""
        cfg = self.config
        price = ts.current_price

        if price <= 0:
            return None

        weight = 1.0 / max(cfg.max_concurrent_positions, 1)
        position_value = cfg.total_capital * weight
        shares = int(position_value / price)

        if shares <= 0:
            return None

        risk_per_share = abs(price - ts.suggested_stop_loss) if ts.suggested_stop_loss > 0 else price * 0.03
        risk_amount = shares * risk_per_share

        return PositionSize(
            shares=shares,
            position_value=round(shares * price, 2),
            position_pct=round(weight * 100, 2),
            risk_per_trade=round(risk_amount, 2),
            risk_pct=round(risk_amount / cfg.total_capital * 100, 2),
            sizing_method="equal_weight",
        )

    def _adjust_position_for_risk(
        self,
        ts: TradeSignal,
        original: PositionSize,
    ) -> Optional[PositionSize]:
        """리스크 초과 시 수량 축소"""
        cfg = self.config
        price = ts.current_price
        risk_per_share = abs(price - ts.suggested_stop_loss)

        if risk_per_share < 1e-6:
            return None

        max_risk = cfg.total_capital * cfg.max_risk_per_trade_pct
        adjusted_shares = int(max_risk / risk_per_share)

        if adjusted_shares <= 0:
            return None

        risk_amount = adjusted_shares * risk_per_share

        return PositionSize(
            shares=adjusted_shares,
            position_value=round(adjusted_shares * price, 2),
            position_pct=round(adjusted_shares * price / cfg.total_capital * 100, 2),
            risk_per_trade=round(risk_amount, 2),
            risk_pct=round(risk_amount / cfg.total_capital * 100, 2),
            sizing_method=f"{original.sizing_method}(조정)",
        )

    # ── 리스크 평가 유틸 ─────────────────────────────────

    @staticmethod
    def _calculate_risk_score(
        ts: TradeSignal,
        position: PositionSize,
    ) -> float:
        """
        리스크 점수 산출 (0~100, 높을수록 위험)

        구성 요소:
          - 포지션 비중 (30%)
          - R/R 비율 역수 (30%)
          - 신호 불확실성 (20%)
          - 리스크 비율 (20%)
        """
        # 포지션 비중 점수 (0~30): 비중 높을수록 위험
        pos_score = min(position.position_pct / 20 * 30, 30)

        # R/R 역수 점수 (0~30): R/R 낮을수록 위험
        rr = max(ts.suggested_rr_ratio, 0.1)
        rr_score = min(30 / rr, 30)

        # 신호 불확실성 (0~20): |점수| 낮을수록 불확실
        signal_uncertainty = max(0, 20 - abs(ts.composite_score) / 5)

        # 리스크 비율 (0~20)
        risk_pct_score = min(position.risk_pct / 2 * 20, 20)

        return round(pos_score + rr_score + signal_uncertainty + risk_pct_score, 1)

    def _build_commentary(
        self,
        ts: TradeSignal,
        position: PositionSize,
        risk_score: float,
    ) -> str:
        """리스크 평가 코멘터리 생성"""
        risk_level = (
            "낮음" if risk_score < 30 else
            "보통" if risk_score < 60 else
            "높음"
        )

        return (
            f"리스크 수준: {risk_level} ({risk_score:.0f}/100) | "
            f"매매 수량: {position.shares:,}주 | "
            f"투자 금액: {position.position_value:,.0f}원 ({position.position_pct:.1f}%) | "
            f"최대 손실: {position.risk_per_trade:,.0f}원 ({position.risk_pct:.2f}%) | "
            f"포지션 사이징: {position.sizing_method}"
        )

    def _reject(
        self,
        ts: TradeSignal,
        reason: VetoReason,
        detail: str,
    ) -> RiskApproval:
        """시그널 거부"""
        self._logger.warning(
            "리스크 거부 (Veto)",
            ticker=ts.ticker,
            reason=reason.value,
            detail=detail,
        )
        return RiskApproval(
            trade_signal=ts,
            approved=False,
            veto_reason=reason,
            risk_commentary=f"거부 사유: {detail}",
        )
