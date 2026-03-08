"""
ta_trader/analyzers/short_analyzer.py
ShortTermAnalyzer - 전체 분석 파사드(Facade)
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from ta_trader.base.base_analyzer import BaseAnalyzer
from ta_trader.indicators.adx import ADXAnalyzer
from ta_trader.indicators.bollinger import BollingerAnalyzer
from ta_trader.indicators.calculator import IndicatorCalculator
from ta_trader.indicators.macd import MACDAnalyzer
from ta_trader.indicators.rsi import RSIAnalyzer
from ta_trader.models import TradingDecision, TradingStyle
from ta_trader.risk.manager import RiskManager
from ta_trader.signals.composer import SignalComposer
from ta_trader.style_config import StyleConfig, get_style_config
from ta_trader.utils.logger import get_logger

if TYPE_CHECKING:
    from ta_trader.models.llm_models import LLMAnalysis

logger = get_logger(__name__)

_SIGNAL_SUMMARY = {
    "강력매수":  "강한 매수 신호입니다. 포지션 진입을 적극 고려하세요.",
    "매수":      "매수 신호입니다. 부분 진입 후 추가 확인을 권장합니다.",
    "중립":      "신호가 혼재합니다. 관망하며 추가 확인이 필요합니다.",
    "매도":      "매도 신호입니다. 보유 포지션 일부 청산을 고려하세요.",
    "강력매도":  "강한 매도 신호입니다. 포지션 청산을 강력히 권장합니다.",
}


class ShortTermAnalyzer(BaseAnalyzer[TradingDecision]):
    """
    1개월 단위 기술적 분석 트레이딩 시스템 파사드.

    사용 예:
        analyzer = ShortTermAnalyzer("005930.KS")
        decision = analyzer.analyze()

        analyzer = ShortTermAnalyzer("AAPL", trading_style=TradingStyle.POSITION)
        decision = analyzer.analyze()  # 포지션 트레이딩
    """

    @property
    def name(self) -> str:
        return "데이터 분석 에이전트"

    @property
    def role(self) -> str:
        return "시장 데이터 수집 및 기술적 지표 연산"

    def analyze(self) -> TradingDecision:
        """전체 분석 파이프라인 실행 후 TradingDecision 반환"""
        sc = self._style_config

        # 1. 데이터 수집
        #name, raw_df = self._fetcher.fetch(self.ticker)
        self._fetch_data()

        # 2. 지표 계산
        #self._calc = IndicatorCalculator(raw_df)
        df         = self._calc.dataframe
        latest     = self._calc.latest()
        prev       = self._calc.previous()

        # 3. 개별 지표 신호
        adx_result  = ADXAnalyzer().analyze(latest)
        rsi_result  = RSIAnalyzer().analyze(latest)
        macd_result = MACDAnalyzer().analyze(latest, prev)
        bb_result   = BollingerAnalyzer().analyze(latest)

        # 4. 복합 신호 합산 (스타일 설정 전파)
        composer = SignalComposer()
        score, signal, regime_ctx = composer.compose_with_strategy(
            adx_result, rsi_result, macd_result, bb_result,
            row=latest,
            prev_row=prev,
            prev_rows=df,
            style_config=sc,
        )

        # 5. 리스크 관리 (스타일별 ATR 배수 적용)
        price   = float(latest["Close"])
        risk    = RiskManager(sc).calculate(price, latest, signal)
        date    = str(df.index[-1].date())
        summary = (
            f"매매 스타일: {self.trading_style.value} | "
            f"시장 국면: {regime_ctx.regime.value} | "
            f"적용 전략: {regime_ctx.strategy.value} | "
            f"복합 점수: {score:+.1f} | "
            f"최종 신호: {signal.value} | RR: 1:{risk.risk_reward_ratio} | "
            f"{_SIGNAL_SUMMARY[signal.value]}"
        )

        logger.info(
            "분석 완료",
            ticker=self.ticker,
            name=self.name,
            signal=signal.value,
            score=score,
            style=self.trading_style.value,
            regime=regime_ctx.regime.value,
            strategy=regime_ctx.strategy.value,
        )

        return TradingDecision(
            ticker          = self.ticker,
            name            = self.name,
            date            = date,
            current_price   = price,
            market_regime   = regime_ctx.regime,
            strategy_type   = regime_ctx.strategy,
            composite_score = score,
            final_signal    = signal,
            trading_style   = self.trading_style,
            indicators      = [adx_result, rsi_result, macd_result, bb_result],
            risk            = risk,
            summary         = summary,
            regime_detail   = regime_ctx.detail,
        )

    """
    @property
    def calculator(self) -> IndicatorCalculator | None:
        "analyze() 호출 후 사용 가능한 IndicatorCalculator"
        return self._calc
    """

    def analyze_with_llm(
        self,
        provider:    str | None = None,
        api_key:     str | None = None,
        model:       str | None = None,
        recent_days: int = 10,
        stream:      bool = False,
    ) -> TradingDecision:
        """
        기술적 분석 실행 후 LLM 해석을 추가하여 반환합니다.
        analyze() 를 내부적으로 먼저 호출하므로 별도 호출 불필요.

        Args:
            provider:    'anthropic' | 'google' | None (None이면 환경변수/자동감지)
            api_key:     Anthropic API 키 (None이면 환경변수 ANTHROPIC_API_KEY 사용)
            model:       LLM 모델명 (None이면 환경변수 TA_LLM_MODEL 또는 기본값 사용)
            recent_days: 가격 추이 요약에 사용할 최근 일수
            stream:      True 이면 스트리밍으로 LLM 응답을 출력하고 결과 반환

        Returns:
            llm_analysis 필드가 채워진 TradingDecision
        """
        from ta_trader.llm.factory import create_llm_analyzer

        # 기술적 분석이 아직 실행되지 않았으면 실행
        decision = self.analyze()
        df = self._calc.dataframe

        llm = create_llm_analyzer(provider=provider, api_key=api_key, model=model)

        if stream:
            print(f"\n{'─'*60}")
            print(f"  🤖 LLM 분석 중 [{self.ticker}] ...")
            print(f"{'─'*60}\n")
            full_text = ""
            for chunk in llm.analyze_stream(decision, df, recent_days):
                print(chunk, end="", flush=True)
                full_text += chunk
            print()
            llm_result = llm._parse_response(full_text, llm._model)
        else:
            llm_result = llm.analyze(decision, df, recent_days)

        decision.llm_analysis = llm_result
        logger.info("LLM 분석 결과 첨부 완료",
                    ticker=self.ticker,
                    name=self.name,
                    provider=llm_result.provider,
                    confidence=llm_result.confidence)
        return decision
