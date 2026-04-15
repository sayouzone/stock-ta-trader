"""
ta_trader/agents/execution.py
Execution Agent — 시장에 직접 주문을 넣고 관리하는 행동 대장

역할:
  Risk Agent를 통과한 최종 오더를 증권사 API를 통해
  실제 시장에 가장 효율적으로 체결합니다.

주요 기능:
  - 주문 전송 및 관리: 지정가(Limit), 시장가(Market), 조건부 주문 등을
    API를 통해 전송 (KIS OpenAPI, 시뮬레이션 등)
  - 슬리피지(Slippage) 최소화: 분할 매수/매도 TWAP/VWAP 알고리즘 적용
  - 상태 모니터링: 미체결 주문 추적, 체결 완료 시 결과 로깅

출력물:
  ExecutionResult — 실제 거래 체결 내역 및 결과 로깅

Note:
  현재 버전은 시뮬레이션(Dry-Run) 모드만 지원합니다.
  실제 API 연동은 ExecutionBackend 인터페이스를 구현하여 확장합니다.
"""

from __future__ import annotations

import math
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from ta_trader.models import OrderSide
from ta_trader.base.agent import BaseAgent
from ta_trader.models.agent import (
    ExecutionAlgorithm, ExecutionResult, OrderRequest,
    OrderStatus, OrderType, RiskApproval,
)


# ── 체결 백엔드 인터페이스 ──────────────────────────────────


class ExecutionBackend(ABC):
    """
    증권사 API 추상 인터페이스.

    구현체 예시:
      - DryRunBackend    : 시뮬레이션 (기본)
      - KISBackend       : 한국투자증권 OpenAPI
      - AlpacaBackend    : Alpaca API (미국 주식)
    """

    @abstractmethod
    def submit_order(self, order: OrderRequest) -> ExecutionResult:
        """주문 제출 및 체결 결과 반환"""

    @abstractmethod
    def cancel_order(self, order_id: str) -> bool:
        """미체결 주문 취소"""

    @abstractmethod
    def get_order_status(self, order_id: str) -> OrderStatus:
        """주문 상태 조회"""


class DryRunBackend(ExecutionBackend):
    """
    시뮬레이션 체결 백엔드 (Dry-Run)

    실제 주문을 전송하지 않고, 현재가 기준으로
    슬리피지를 시뮬레이션하여 체결 결과를 반환합니다.
    """

    def __init__(
        self,
        slippage_pct: float = 0.05,       # 기본 슬리피지 0.05%
        commission_pct: float = 0.015,     # 편도 수수료 0.015%
    ) -> None:
        self.slippage_pct = slippage_pct
        self.commission_pct = commission_pct

    def submit_order(self, order: OrderRequest) -> ExecutionResult:
        """시뮬레이션 체결"""
        expected = order.limit_price or 0.0

        # 슬리피지 시뮬레이션
        if order.side == OrderSide.BUY:
            filled_price = expected * (1 + self.slippage_pct / 100)
        else:
            filled_price = expected * (1 - self.slippage_pct / 100)

        filled_price = round(filled_price, 2)
        commission = round(filled_price * order.quantity * self.commission_pct / 100, 2)
        slippage = round((filled_price / expected - 1) * 100, 4) if expected > 0 else 0.0

        return ExecutionResult(
            risk_approval=None,  # 나중에 설정됨
            order=order,
            status=OrderStatus.FILLED,
            filled_quantity=order.quantity,
            filled_price=filled_price,
            fill_time=datetime.now().isoformat(),
            expected_price=expected,
            actual_slippage_pct=slippage,
            commission=commission,
            execution_log=[
                f"[DryRun] 주문 제출: {order.side.value} {order.ticker} × {order.quantity}",
                f"[DryRun] 체결: {filled_price:,.2f}원 (슬리피지: {slippage:+.4f}%)",
                f"[DryRun] 수수료: {commission:,.2f}원",
            ],
        )

    def cancel_order(self, order_id: str) -> bool:
        return True

    def get_order_status(self, order_id: str) -> OrderStatus:
        return OrderStatus.FILLED


# ── 체결 설정 ───────────────────────────────────────────────


@dataclass
class ExecutionConfig:
    """Execution Agent 설정"""
    # 기본 주문 유형
    default_order_type: OrderType = OrderType.LIMIT

    # 분할 매매 설정
    split_threshold: int = 100            # 이 수량 이상이면 분할 매매
    max_split_count: int = 5              # 최대 분할 횟수

    # 체결 알고리즘
    default_algorithm: ExecutionAlgorithm = ExecutionAlgorithm.IMMEDIATE

    # TWAP 설정
    twap_interval_minutes: int = 5         # TWAP 주문 간격 (분)

    # 가격 제한
    limit_price_offset_pct: float = 0.1    # 지정가 = 현재가 ± 0.1%

    # 시뮬레이션 모드
    dry_run: bool = True


# ── Execution Agent ─────────────────────────────────────────


class ExecutionAgent(BaseAgent[RiskApproval, ExecutionResult]):
    """
    Execution Agent

    Risk Agent를 통과한 승인된 시그널을 주문으로 변환하고,
    체결 백엔드를 통해 실행합니다.

    현재 버전은 DryRunBackend(시뮬레이션)을 기본으로 사용하며,
    실제 증권사 API 연동은 ExecutionBackend 구현체를 주입하여 확장합니다.

    사용 예:
        agent = ExecutionAgent()  # 시뮬레이션 모드
        result = agent.execute(risk_approval)

        # 실제 API 연동
        agent = ExecutionAgent(
            backend=KISBackend(api_key="..."),
            config=ExecutionConfig(dry_run=False),
        )
    """

    def __init__(
        self,
        backend: Optional[ExecutionBackend] = None,
        config: Optional[ExecutionConfig] = None,
    ) -> None:
        super().__init__()
        self.config = config or ExecutionConfig()
        self._backend = backend or DryRunBackend()

    @property
    def name(self) -> str:
        return "체결 실행 에이전트"

    @property
    def role(self) -> str:
        return "주문 실행 및 체결 관리"

    def execute(self, input_data: RiskApproval) -> ExecutionResult:
        """
        승인된 시그널 → 주문 생성 → 체결 실행

        Args:
            input_data: RiskAgent의 출력물 (RiskApproval)

        Returns:
            ExecutionResult: 체결 내역 및 로그
        """
        ra = input_data
        ts = ra.trade_signal

        self._logger.info(
            "주문 실행 시작",
            ticker=ts.ticker,
            side=ts.side.value,
            approved=ra.approved,
        )

        # ── 미승인 시그널 처리 ────────────────────────
        if not ra.approved:
            return ExecutionResult(
                risk_approval=ra,
                order=OrderRequest(
                    ticker=ts.ticker,
                    side=ts.side,
                    order_type=OrderType.MARKET,
                    quantity=0,
                ),
                status=OrderStatus.REJECTED,
                execution_log=[
                    f"주문 거부: {ra.veto_reason.value}",
                    f"사유: {ra.risk_commentary}",
                ],
            )

        # ── 관망 시그널 처리 ──────────────────────────
        if ts.side == OrderSide.HOLD:
            return ExecutionResult(
                risk_approval=ra,
                order=OrderRequest(
                    ticker=ts.ticker,
                    side=OrderSide.HOLD,
                    order_type=OrderType.MARKET,
                    quantity=0,
                ),
                status=OrderStatus.CANCELLED,
                execution_log=["관망 시그널 — 주문 없음"],
            )

        # ── 주문 생성 ────────────────────────────────
        quantity = ra.position_size.shares if ra.position_size else 0
        if quantity <= 0:
            return ExecutionResult(
                risk_approval=ra,
                order=OrderRequest(
                    ticker=ts.ticker,
                    side=ts.side,
                    order_type=OrderType.MARKET,
                    quantity=0,
                ),
                status=OrderStatus.REJECTED,
                execution_log=["매매 수량이 0 — 주문 불가"],
            )

        order = self._build_order(ts, ra, quantity)

        # ── 분할 매매 결정 ────────────────────────────
        if quantity >= self.config.split_threshold:
            return self._execute_split(ra, order)

        # ── 단일 주문 실행 ────────────────────────────
        result = self._backend.submit_order(order)
        result.risk_approval = ra

        self._log_execution(result)
        return result

    def execute_batch(
        self,
        approvals: list[RiskApproval],
    ) -> list[ExecutionResult]:
        """복수 승인 일괄 실행"""
        results = []
        for approval in approvals:
            result = self.execute(approval)
            results.append(result)
        return results

    # ── 내부 메서드 ──────────────────────────────────────

    def _build_order(
        self,
        ts: TradeSignal,
        ra: RiskApproval,
        quantity: int,
    ) -> OrderRequest:
        """주문 요청 객체 생성"""
        # 지정가 계산
        price = ts.current_price
        offset = self.config.limit_price_offset_pct / 100

        if ts.side == OrderSide.BUY:
            limit_price = round(price * (1 + offset), 2)
        else:
            limit_price = round(price * (1 - offset), 2)

        order_type = self.config.default_order_type
        algorithm = self.config.default_algorithm

        # 대량 주문 시 알고리즘 자동 선택
        if quantity >= self.config.split_threshold:
            algorithm = ExecutionAlgorithm.TWAP

        return OrderRequest(
            ticker=ts.ticker,
            side=ts.side,
            order_type=order_type,
            quantity=quantity,
            limit_price=limit_price,
            stop_price=ra.final_stop_loss if ra.final_stop_loss > 0 else None,
            algorithm=algorithm,
            split_count=self._calc_split_count(quantity),
        )

    def _execute_split(
        self,
        ra: RiskApproval,
        order: OrderRequest,
    ) -> ExecutionResult:
        """
        분할 매수/매도 실행 (TWAP 방식)

        대량 주문을 여러 작은 주문으로 나누어 체결 충격을 최소화합니다.
        """
        split_count = order.split_count
        base_qty = order.quantity // split_count
        remainder = order.quantity % split_count

        total_filled = 0
        total_value = 0.0
        total_commission = 0.0
        logs = [
            f"분할 매매 시작: 총 {order.quantity}주 → {split_count}회 분할",
        ]

        for i in range(split_count):
            qty = base_qty + (1 if i < remainder else 0)
            split_order = OrderRequest(
                ticker=order.ticker,
                side=order.side,
                order_type=order.order_type,
                quantity=qty,
                limit_price=order.limit_price,
                algorithm=ExecutionAlgorithm.IMMEDIATE,
            )

            result = self._backend.submit_order(split_order)
            total_filled += result.filled_quantity
            total_value += result.filled_price * result.filled_quantity
            total_commission += result.commission
            logs.append(
                f"  [{i+1}/{split_count}] {qty}주 → "
                f"{result.filled_price:,.2f}원 체결"
            )

        # 가중평균 체결가
        avg_price = total_value / total_filled if total_filled > 0 else 0.0
        expected = order.limit_price or 0.0
        slippage = (avg_price / expected - 1) * 100 if expected > 0 else 0.0

        logs.append(
            f"분할 매매 완료: 평균 체결가 {avg_price:,.2f}원 "
            f"(슬리피지: {slippage:+.4f}%)"
        )

        return ExecutionResult(
            risk_approval=ra,
            order=order,
            status=OrderStatus.FILLED,
            filled_quantity=total_filled,
            filled_price=round(avg_price, 2),
            fill_time=datetime.now().isoformat(),
            expected_price=expected,
            actual_slippage_pct=round(slippage, 4),
            commission=round(total_commission, 2),
            execution_log=logs,
        )

    def _calc_split_count(self, quantity: int) -> int:
        """분할 횟수 계산"""
        if quantity < self.config.split_threshold:
            return 1
        # 100주당 1분할, 최대 max_split_count
        count = math.ceil(quantity / self.config.split_threshold)
        return min(count, self.config.max_split_count)

    def _log_execution(self, result: ExecutionResult) -> None:
        """체결 결과 로깅"""
        self._logger.info(
            "체결 완료",
            ticker=result.order.ticker,
            status=result.status.value,
            filled_qty=result.filled_quantity,
            filled_price=result.filled_price,
            slippage=f"{result.actual_slippage_pct:+.4f}%",
            commission=result.commission,
        )
