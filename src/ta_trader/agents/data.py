"""
ta_trader/agents/data.py
Data & Analysis Agent — 시장의 모든 정보를 수집하고 정량적/정성적 지표로 가공하는 눈과 귀

역할:
  시장 데이터를 수집하고 분석하여 현재 시장의 '상태'를 정의합니다.

주요 기능:
  - 데이터 수집: 가격 데이터, 거래량 (yfinance)
  - 기술적 지표 연산: RSI, MACD, 볼린저 밴드, ADX, 이동평균선 등
  - 시장 국면 판별: ADX + BandWidth 결합 체제 분류
  - 센티먼트 분석: LLM 기반 시장 심리 수치화 (선택적)
  - 펀더멘털 수집: yfinance info 기반 재무 데이터

출력물:
  MarketDataReport — 정제된 데이터 포인트 및 시장 동향 요약 리포트
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import pandas as pd

from ta_trader.base.agent import BaseAgent
from ta_trader.models.agent import MarketDataReport
from ta_trader.data.fetcher import DataFetcher
from ta_trader.indicators.adx import ADXAnalyzer
from ta_trader.indicators.bollinger import BollingerAnalyzer
from ta_trader.indicators.calculator import IndicatorCalculator
from ta_trader.indicators.macd import MACDAnalyzer
from ta_trader.indicators.rsi import RSIAnalyzer
from ta_trader.models import IndicatorResult, TradingStyle
from ta_trader.signals.regime import detect_regime, RegimeContext
from ta_trader.config.style_config import StyleConfig, get_style_config
from ta_trader.constants.short import MIN_DATA_ROWS

@dataclass
class DataAgentInput:
    """DataAgent 입력 파라미터"""
    ticker: str
    period: str = "6mo"
    interval: str = "1d"
    trading_style: TradingStyle = TradingStyle.SWING
    include_fundamentals: bool = True
    include_sentiment: bool = False
    llm_provider: Optional[str] = None
    llm_model: Optional[str] = None


class DataAgent(BaseAgent[DataAgentInput, MarketDataReport]):
    """
    Data & Analysis Agent

    시장 데이터를 수집·가공하여 정제된 MarketDataReport를 생성합니다.
    이 에이전트는 어떤 매매 판단도 하지 않으며,
    오직 데이터의 수집과 정량화에만 집중합니다.
    """

    @property
    def name(self) -> str:
        return "데이터 분석 에이전트"

    @property
    def role(self) -> str:
        return "시장 데이터 수집 및 기술적 지표 연산"

    def execute(self, input_data: DataAgentInput) -> MarketDataReport:
        """
        데이터 수집 → 지표 계산 → 시장 국면 판별 파이프라인 실행

        Args:
            input_data: DataAgentInput (ticker, period, interval 등)

        Returns:
            MarketDataReport: 정제된 시장 데이터 및 지표 분석 결과
        """
        self._logger.info(
            "데이터 수집 시작",
            ticker=input_data.ticker,
            period=input_data.period,
        )

        style_config = get_style_config(input_data.trading_style)

        # 1. 데이터 수집 ─────────────────────────────────
        self._fetch_data(
            ticker=input_data.ticker,
            period=input_data.period,
            interval=input_data.interval,
        )

        # 2. 기술적 지표 계산 ─────────────────────────────        
        df = self._calc.dataframe
        latest = self._calc.latest()
        prev = self._calc.previous()

        # 3. 개별 지표 분석 ───────────────────────────────
        indicator_results = self._analyze_indicators(latest, prev)

        # 4. 시장 국면 판별 ───────────────────────────────
        regime_ctx = self._detect_regime(latest, df, style_config)

        # 5. 펀더멘털 수집 (선택적) ───────────────────────
        fundamentals = {}
        if input_data.include_fundamentals:
            fundamentals = self._info

        # 6. 센티먼트 분석 (선택적) ───────────────────────
        sentiment = ""
        if input_data.include_sentiment and input_data.llm_provider:
            sentiment = self._analyze_sentiment(input_data, df)

        self._logger.info(
            "데이터 분석 완료",
            ticker=input_data.ticker,
            name=self._name,
            regime=regime_ctx.regime.value if regime_ctx else "미판별",
            indicators=len(indicator_results),
            rows=len(df),
        )

        return MarketDataReport(
            ticker=input_data.ticker,
            name=self._name,
            date=str(df.index[-1].date()),
            current_price=float(latest["Close"]),
            ohlcv_df=df,
            latest_row=latest,
            prev_row=prev,
            indicator_results=indicator_results,
            regime_context=regime_ctx,
            fundamentals=fundamentals,
            sentiment_summary=sentiment,
            data_quality_score=self._assess_data_quality(df),
            data_rows=len(df),
        )

    # ── 내부 메서드 ──────────────────────────────────────

    @staticmethod
    def _analyze_indicators(
        latest: pd.Series,
        prev: Optional[pd.Series],
    ) -> list[IndicatorResult]:
        """개별 기술적 지표 신호 분석"""
        return [
            ADXAnalyzer().analyze(latest),
            RSIAnalyzer().analyze(latest),
            MACDAnalyzer().analyze(latest, prev),
            BollingerAnalyzer().analyze(latest),
        ]

    @staticmethod
    def _detect_regime(
        latest: pd.Series,
        df: pd.DataFrame,
        style_config: StyleConfig,
    ) -> RegimeContext:
        """ADX + BandWidth 결합 시장 국면 판별"""
        return detect_regime(
            latest,
            df,
            adx_strong=style_config.adx_strong_trend,
            adx_weak=style_config.adx_weak_trend,
        )

    @staticmethod
    def _fetch_fundamentals(
        ticker: str,
        fetcher: DataFetcher,
    ) -> dict:
        """yfinance 펀더멘털 데이터 수집"""
        try:
            _, info = fetcher.info(ticker)
            return info
        except Exception:
            return {}

    @staticmethod
    def _analyze_sentiment(
        input_data: DataAgentInput,
        df: pd.DataFrame,
    ) -> str:
        """LLM 기반 시장 센티먼트 분석 (선택적)"""
        try:
            from ta_trader.llm.factory import create_llm_analyzer
            llm = create_llm_analyzer(
                provider=input_data.llm_provider,
                model=input_data.llm_model,
            )
            # 간단한 가격 추이 요약을 LLM에 전달
            recent = df["Close"].tail(10)
            pct_change = (recent.iloc[-1] / recent.iloc[0] - 1) * 100
            prompt = (
                f"종목 {input_data.ticker}의 최근 10일 가격 변동률: {pct_change:+.2f}%. "
                f"현재 시장 심리를 한 문장으로 요약하세요."
            )
            from ta_trader.llm.prompt_builder import SYSTEM_PROMPT
            return llm._call_api(SYSTEM_PROMPT, prompt)
        except Exception:
            return ""

    @staticmethod
    def _assess_data_quality(df: pd.DataFrame) -> float:
        """데이터 품질 점수 산출 (0.0~1.0)"""
        if df.empty:
            return 0.0

        # NaN 비율 기반
        nan_ratio = df.isnull().sum().sum() / (df.shape[0] * df.shape[1])
        quality = 1.0 - min(nan_ratio, 1.0)

        # 최소 데이터 행 수 반영
        if len(df) < MIN_DATA_ROWS:
            quality *= len(df) / MIN_DATA_ROWS

        return round(quality, 3)
