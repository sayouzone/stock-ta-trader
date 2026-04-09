"""
tests/test_google.py
Gemini LLM 분석기 단위 테스트 (Google GenAI SDK 모킹)
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from ta_trader.exceptions import TATraderError
from ta_trader.llm.factory import create_llm_analyzer, list_providers
from ta_trader.analyzers.google import GoogleAnalyzer
from ta_trader.models.llm import LLMAnalysis
from ta_trader.models.short import (
    IndicatorResult, MarketRegime, RiskLevels, Signal, TradingDecision, StrategyType
)

# ── 픽스처 ──────────────────────────────────────────────

@pytest.fixture()
def sample_decision() -> TradingDecision:
    return TradingDecision(
        ticker          = "NVDA",
        name            = "Nvidia",
        date            = "2024-12-31",
        current_price   = 135.0,
        market_regime   = MarketRegime.STRONG_TREND,
        composite_score = 65.0,
        strategy_type    = StrategyType.TREND_FOLLOWING,
        final_signal    = Signal.STRONG_BUY,
        indicators      = [IndicatorResult("ADX", 30.0, Signal.STRONG_BUY, 55.0, "ADX=30.0")],
        risk            = RiskLevels(stop_loss=128.0, take_profit=148.0, risk_reward_ratio=1.85),
    )


@pytest.fixture()
def sample_df() -> pd.DataFrame:
    import numpy as np
    rng   = np.random.default_rng(1)
    dates = pd.date_range("2024-07-01", periods=60, freq="B")
    close = 120.0 + np.cumsum(rng.normal(0, 1.5, 60))
    return pd.DataFrame({
        "Close":  close,
        "Volume": rng.integers(30_000_000, 80_000_000, 60),
    }, index=dates)


_VALID_GEMINI_RESPONSE = json.dumps({
    "overall_assessment": "NVIDIA는 AI 수요 급증으로 강한 상승 추세를 유지하고 있습니다.",
    "signal_rationale":   "ADX 30의 강한 추세와 MACD 골든크로스가 매수를 지지합니다.",
    "key_risks":          ["밸류에이션 부담", "미중 반도체 규제"],
    "opportunities":      ["데이터센터 수요 확대", "자율주행 AI 칩"],
    "action_plan":        "135달러 진입, 128달러 손절, 148달러 목표.",
    "confidence":         0.82,
}, ensure_ascii=False)


# ── GoogleAnalyzer 테스트 ───────────────────────────────

class TestGoogleAnalyzer:

    def _make_mock_response(self, text: str) -> MagicMock:
        response             = MagicMock()
        response.text        = text
        candidate            = MagicMock()
        candidate.finish_reason = "FinishReason.STOP"
        response.candidates  = [candidate]
        return response

    @patch("ta_trader.analyzers.google.genai.Client")
    def test_analyze_returns_llm_analysis(self, mock_client_cls, sample_decision, sample_df):
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        mock_client.models.generate_content.return_value = self._make_mock_response(_VALID_GEMINI_RESPONSE)

        analyzer = GoogleAnalyzer(api_key="test-key")
        result   = analyzer.analyze(sample_decision, sample_df)

        assert isinstance(result, LLMAnalysis)
        assert result.provider == "google"
        assert result.confidence == pytest.approx(0.82)
        assert "AI 수요" in result.overall_assessment

    @patch("ta_trader.analyzers.google.genai.Client")
    def test_stream_yields_chunks(self, mock_client_cls, sample_decision, sample_df):
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client

        chunks = [MagicMock(text='{"overall'), MagicMock(text='_assessment": "테스트"}')]
        mock_client.models.generate_content_stream.return_value = iter(chunks)

        analyzer = GoogleAnalyzer(api_key="test-key")
        result   = list(analyzer.analyze_stream(sample_decision, sample_df))

        assert len(result) == 2
        assert result[0] == '{"overall'

    @patch("ta_trader.analyzers.google.genai.Client")
    def test_provider_name(self, mock_client_cls):
        mock_client_cls.return_value = MagicMock()
        analyzer = GoogleAnalyzer(api_key="test-key")
        assert analyzer.provider_name == "google"

    def test_missing_api_key_raises(self, monkeypatch):
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)
        with pytest.raises(TATraderError, match="GEMINI_API_KEY"):
            GoogleAnalyzer(api_key=None)

    @patch("ta_trader.analyzers.google.genai.Client")
    def test_safety_filter_blocked_raises(self, mock_client_cls, sample_decision, sample_df):
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        blocked_response = MagicMock()
        blocked_response.candidates = []   # Safety filter가 차단한 경우
        mock_client.models.generate_content.return_value = blocked_response

        analyzer = GoogleAnalyzer(api_key="test-key")
        with pytest.raises(TATraderError, match="Safety Filter"):
            analyzer.analyze(sample_decision, sample_df)


# ── Factory 테스트 ───────────────────────────────────────

class TestFactory:

    def test_list_providers(self):
        providers = list_providers()
        assert "anthropic" in providers
        assert "google" in providers

    @patch("ta_trader.analyzers.anthropic.anthropic.Anthropic")
    def test_create_anthropic(self, mock_cls, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
        mock_cls.return_value = MagicMock()
        from ta_trader.analyzers.anthropic import AnthropicAnalyzer
        analyzer = create_llm_analyzer(provider="anthropic")
        assert isinstance(analyzer, AnthropicAnalyzer)
        assert analyzer.provider_name == "anthropic"

    @patch("ta_trader.analyzers.google.genai.Client")
    def test_create_google(self, mock_cls, monkeypatch):
        monkeypatch.setenv("GEMINI_API_KEY", "test-key")
        mock_cls.return_value = MagicMock()
        analyzer = create_llm_analyzer(provider="google")
        assert isinstance(analyzer, GoogleAnalyzer)
        assert analyzer.provider_name == "google"

    def test_unknown_provider_raises(self):
        with pytest.raises(TATraderError, match="지원하지 않는"):
            create_llm_analyzer(provider="openai")

    def test_auto_detect_anthropic(self, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)
        with patch("ta_trader.analyzers.anthropic.anthropic.Anthropic") as mock_cls:
            mock_cls.return_value = MagicMock()
            analyzer = create_llm_analyzer()   # provider=None → 자동 감지
            assert analyzer.provider_name == "anthropic"

    def test_auto_detect_google(self, monkeypatch):
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        monkeypatch.setenv("GEMINI_API_KEY", "AIza-test")
        with patch("ta_trader.analyzers.google.genai.Client") as mock_cls:
            mock_cls.return_value = MagicMock()
            analyzer = create_llm_analyzer()
            assert analyzer.provider_name == "google"

    def test_no_api_key_raises(self, monkeypatch):
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)
        with pytest.raises(TATraderError, match="API 키"):
            create_llm_analyzer()


# ── Provider 공통 인터페이스 테스트 (Base 계약 검증) ──────

class TestProviderInterface:
    """두 Provider가 동일한 BaseLLMAnalyzer 인터페이스를 준수하는지 확인"""

    @patch("ta_trader.analyzers.anthropic.anthropic.Anthropic")
    def test_anthropic_has_provider_name(self, mock_cls):
        mock_cls.return_value = MagicMock()
        from ta_trader.analyzers.anthropic import AnthropicAnalyzer
        a = AnthropicAnalyzer(api_key="test")
        assert hasattr(a, "provider_name")
        assert hasattr(a, "analyze")
        assert hasattr(a, "analyze_stream")

    @patch("ta_trader.analyzers.google.genai.Client")
    def test_google_has_provider_name(self, mock_cls):
        mock_cls.return_value = MagicMock()
        g = GoogleAnalyzer(api_key="test")
        assert hasattr(g, "provider_name")
        assert hasattr(g, "analyze")
        assert hasattr(g, "analyze_stream")
