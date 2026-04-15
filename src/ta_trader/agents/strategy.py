"""
ta_trader/agents/strategy.py
Strategy & Decision Agent — 분석된 데이터를 바탕으로 매매 전략을 수립하는 브레인

역할:
  Data Agent가 넘겨준 데이터를 바탕으로 언제, 어떤 종목을 살지/팔지 결정합니다.

주요 기능:
  - 시그널 생성: 스윙, 포지션, 가치 투자 등 사전 정의된 전략 알고리즘 +
                  LLM 추론을 바탕으로 매수(Buy), 매도(Sell), 관망(Hold) 시그널 생성
  - 종목 스크리닝: 가장 유리한 위험 대비 보상 비율(Risk/Reward Ratio)을 가진 종목 타겟팅

출력물:
  TradeSignal — 명확한 매매 방향성 및 타겟 종목, 목표 진입가
  StrategyReport — 복수 종목 스크리닝 결과
"""

from __future__ import annotations

from typing import Optional

from ta_trader.models import OrderSide
from ta_trader.base.agent import BaseAgent
from ta_trader.models.agent import (
    MarketDataReport, StrategyReport, TradeSignal,
)
from ta_trader.models import Signal, TradingStyle
from ta_trader.risk.manager import RiskManager
from ta_trader.signals.composer import SignalComposer
from ta_trader.config.style_config import StyleConfig, get_style_config


# ── 시그널 → 매매 방향 매핑 ────────────────────────────────

_SIGNAL_SIDE_MAP = {
    Signal.STRONG_BUY: OrderSide.BUY,
    Signal.BUY: OrderSide.BUY,
    Signal.NEUTRAL: OrderSide.HOLD,
    Signal.SELL: OrderSide.SELL,
    Signal.STRONG_SELL: OrderSide.SELL,
}

_SIGNAL_SUMMARY = {
    "강력매수": "강한 매수 신호입니다. 포지션 진입을 적극 고려하세요.",
    "매수":     "매수 신호입니다. 부분 진입 후 추가 확인을 권장합니다.",
    "중립":     "신호가 혼재합니다. 관망하며 추가 확인이 필요합니다.",
    "매도":     "매도 신호입니다. 보유 포지션 일부 청산을 고려하세요.",
    "강력매도": "강한 매도 신호입니다. 포지션 청산을 강력히 권장합니다.",
}


class StrategyAgent(BaseAgent[MarketDataReport, TradeSignal]):
    """
    Strategy & Decision Agent

    MarketDataReport를 받아 복합 전략 분석을 수행하고
    매매 시그널(TradeSignal)을 생성합니다.

    내부적으로 기존 SignalComposer + Strategy 모듈을 활용하되,
    에이전트 파이프라인에 맞는 출력 형식으로 변환합니다.

    사용 예:
        agent = StrategyAgent(trading_style=TradingStyle.SWING)
        signal = agent.execute(market_data_report)
    """

    def __init__(
        self,
        trading_style: TradingStyle = TradingStyle.SWING,
        use_llm: bool = False,
        llm_provider: Optional[str] = None,
        llm_model: Optional[str] = None,
        llm_stream: bool = False,
    ) -> None:
        super().__init__()
        self.trading_style = trading_style
        self._style_config = get_style_config(trading_style)
        self._composer = SignalComposer()
        self._risk_calc = RiskManager(self._style_config)
        self._use_llm = use_llm
        self._llm_provider = llm_provider
        self._llm_model = llm_model
        self._llm_stream = llm_stream

    @property
    def name(self) -> str:
        return "전략 의사결정 에이전트"

    @property
    def role(self) -> str:
        return "매매 전략 수립 및 시그널 생성"

    def execute(self, input_data: MarketDataReport) -> TradeSignal:
        """
        MarketDataReport → TradeSignal 변환 파이프라인

        1. 복합 신호 합산 (체제별 전략 자동 전환)
        2. 손절/익절 예비 산출
        3. LLM 분석 추가 (선택적)
        4. TradeSignal 생성

        Args:
            input_data: DataAgent의 출력물

        Returns:
            TradeSignal: 매매 방향성, 타겟 진입가, 근거
        """
        self._logger.info(
            "전략 분석 시작",
            ticker=input_data.ticker,
            style=self.trading_style.value,
        )

        md = input_data

        # 1. 복합 신호 합산 (스타일 설정 전파) ──────────
        score, signal, regime_ctx = self._composer.compose_with_strategy(
            *md.indicator_results,
            row=md.latest_row,
            prev_row=md.prev_row,
            prev_rows=md.ohlcv_df,
            style_config=self._style_config,
        )

        # 2. 예비 손절/익절 산출 ────────────────────────
        price = md.current_price
        risk_levels = self._risk_calc.calculate(price, md.latest_row, signal)

        # 3. 시그널 근거 생성 ──────────────────────────
        rationale = self._build_rationale(
            md, score, signal, regime_ctx, risk_levels,
        )

        # 4. LLM 분석 (선택적) ─────────────────────────
        llm_result = None
        if self._use_llm:
            llm_result = self._run_llm_analysis(md, score, signal, risk_levels)

        # 5. 매매 방향 결정 ────────────────────────────
        side = _SIGNAL_SIDE_MAP.get(signal, OrderSide.HOLD)

        trade_signal = TradeSignal(
            ticker=md.ticker,
            name=md.name,
            date=md.date,
            current_price=price,
            side=side,
            signal=signal,
            composite_score=score,
            trading_style=self.trading_style,
            market_regime=regime_ctx.regime,
            strategy_type=regime_ctx.strategy,
            regime_detail=regime_ctx.detail,
            target_entry_price=price,
            suggested_stop_loss=risk_levels.stop_loss,
            suggested_take_profit=risk_levels.take_profit,
            suggested_rr_ratio=risk_levels.risk_reward_ratio,
            indicator_results=md.indicator_results,
            signal_rationale=rationale,
            market_data=md,
            llm_analysis=llm_result,
        )

        self._logger.info(
            "전략 분석 완료",
            ticker=md.ticker,
            signal=signal.value,
            score=score,
            side=side.value,
        )

        return trade_signal

    def execute_batch(
        self,
        market_data_list: list[MarketDataReport],
    ) -> StrategyReport:
        """
        복수 종목 스크리닝: 가장 유리한 R/R 비율 종목 타겟팅

        Args:
            market_data_list: 복수 종목의 MarketDataReport 리스트

        Returns:
            StrategyReport: 정렬된 시그널 + 상위 추천 + 회피 목록
        """
        self._logger.info(
            "배치 전략 분석 시작",
            count=len(market_data_list),
            style=self.trading_style.value,
        )

        signals: list[TradeSignal] = []
        for md in market_data_list:
            try:
                signal = self.execute(md)
                signals.append(signal)
            except Exception as e:
                self._logger.error(
                    "종목 분석 실패",
                    ticker=md.ticker,
                    error=str(e),
                )

        # R/R 비율 + 점수 기준 정렬
        signals.sort(
            key=lambda s: (s.suggested_rr_ratio, s.composite_score),
            reverse=True,
        )

        # 매수 추천 vs 회피 분류
        top_picks = [
            s for s in signals
            if s.side == OrderSide.BUY and s.suggested_rr_ratio >= 1.5
        ]
        avoid_list = [
            s for s in signals
            if s.side == OrderSide.SELL
        ]

        date = signals[0].date if signals else ""

        return StrategyReport(
            date=date,
            trading_style=self.trading_style,
            signals=signals,
            top_picks=top_picks,
            avoid_list=avoid_list,
        )

    # ── 내부 메서드 ──────────────────────────────────────

    def _build_rationale(
        self,
        md: MarketDataReport,
        score: float,
        signal: Signal,
        regime_ctx,
        risk_levels,
    ) -> str:
        """시그널 근거 문자열 생성"""
        return (
            f"매매 스타일: {self.trading_style.value} | "
            f"시장 국면: {regime_ctx.regime.value} | "
            f"적용 전략: {regime_ctx.strategy.value} | "
            f"복합 점수: {score:+.1f} | "
            f"최종 신호: {signal.value} | "
            f"RR: 1:{risk_levels.risk_reward_ratio} | "
            f"{_SIGNAL_SUMMARY.get(signal.value, '')}"
        )

    def _run_llm_analysis(
        self,
        md: MarketDataReport,
        score: float,
        signal: Signal,
        risk_levels,
    ) -> Optional[object]:
        """LLM 기반 추가 분석 실행"""
        try:
            from ta_trader.llm.factory import create_llm_analyzer
            from ta_trader.models import RiskLevels, TradingDecision

            # LLM 분석을 위한 TradingDecision 임시 생성
            decision = TradingDecision(
                ticker=md.ticker,
                name=md.name,
                date=md.date,
                current_price=md.current_price,
                market_regime=md.regime_context.regime if md.regime_context else None,
                strategy_type=md.regime_context.strategy if md.regime_context else None,
                composite_score=score,
                final_signal=signal,
                trading_style=self.trading_style,
                indicators=md.indicator_results,
                risk=RiskLevels(
                    stop_loss=risk_levels.stop_loss,
                    take_profit=risk_levels.take_profit,
                    risk_reward_ratio=risk_levels.risk_reward_ratio,
                ),
                regime_detail=md.regime_context.detail if md.regime_context else "",
            )

            llm = create_llm_analyzer(
                provider=self._llm_provider,
                model=self._llm_model,
            )

            if self._llm_stream:
                print(f"\n{'─'*60}")
                print(f"  🤖 LLM 분석 중 [{md.ticker}] ...")
                print(f"{'─'*60}\n")
                full_text = ""
                for chunk in llm.analyze_stream(decision, md.ohlcv_df, 10):
                    print(chunk, end="", flush=True)
                    full_text += chunk
                print()
                return llm._parse_response(full_text, llm._model, llm.provider_name)
            else:
                return llm.analyze(decision, md.ohlcv_df, 10)

        except Exception as e:
            self._logger.warning("LLM 분석 실패", error=str(e))
            return None
