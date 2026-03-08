"""
tests/test_llm.py
LLM 분석 모듈 단위 테스트 (Anthropic API 모킹)
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from ta_trader.llm.analyzer import LLMAnalyzer
from ta_trader.models.llm_models import LLMAnalysis
from ta_trader.llm.prompt_builder import PromptBuilder
from ta_trader.models.short_models import (
    IndicatorResult, MarketRegime, RiskLevels, Signal, TradingDecision,
)


# ── 픽스처 ──────────────────────────────────────────────

@pytest.fixture()
def sample_decision() -> TradingDecision:
    return TradingDecision(
        ticker          = "005930.KS",
        date            = "2024-12-31",
        current_price   = 62000.0,
        market_regime   = MarketRegime.STRONG_TREND,
        composite_score = 55.0,
        final_signal    = Signal.BUY,
        indicators      = [
            IndicatorResult("ADX",              28.0, Signal.BUY,        40.0, "ADX=28.0"),
            IndicatorResult("RSI",              45.0, Signal.NEUTRAL,     0.0, "RSI=45.0"),
            IndicatorResult("MACD",              0.3, Signal.BUY,        35.0, "MACD=0.3"),
            IndicatorResult("Bollinger Bands",   0.4, Signal.NEUTRAL,     0.0, "BB%=40.0%"),
        ],
        risk = RiskLevels(stop_loss=59000.0, take_profit=66000.0, risk_reward_ratio=2.0),
    )


@pytest.fixture()
def sample_df() -> pd.DataFrame:
    import numpy as np
    rng   = np.random.default_rng(0)
    dates = pd.date_range("2024-07-01", periods=60, freq="B")
    close = 60000 + np.cumsum(rng.normal(0, 300, 60))
    return pd.DataFrame({
        "Close":  close,
        "Volume": rng.integers(5_000_000, 15_000_000, 60),
    }, index=dates)


_VALID_LLM_RESPONSE = json.dumps({
    "overall_assessment": "삼성전자는 강한 추세를 보이고 있습니다.",
    "signal_rationale":   "ADX 28로 추세가 확인되고 MACD가 양전환했습니다.",
    "key_risks":          ["반도체 업황 불확실성", "원/달러 환율 리스크"],
    "opportunities":      ["AI 수요 증가", "HBM 점유율 확대"],
    "action_plan":        "62,000원 진입, 59,000원 손절, 66,000원 목표.",
    "confidence":         0.78,
}, ensure_ascii=False)


# ── PromptBuilder 테스트 ────────────────────────────────

class TestPromptBuilder:
    def test_prompt_contains_ticker(self, sample_decision, sample_df):
        prompt = PromptBuilder().build(sample_decision, sample_df)
        assert "005930.KS" in prompt

    def test_prompt_contains_signal(self, sample_decision, sample_df):
        prompt = PromptBuilder().build(sample_decision, sample_df)
        assert "매수" in prompt

    def test_prompt_contains_risk_levels(self, sample_decision, sample_df):
        prompt = PromptBuilder().build(sample_decision, sample_df)
        assert "59,000" in prompt or "59000" in prompt

    def test_prompt_contains_json_schema(self, sample_decision, sample_df):
        prompt = PromptBuilder().build(sample_decision, sample_df)
        assert "overall_assessment" in prompt
        assert "key_risks" in prompt

    def test_prompt_contains_price_trend(self, sample_decision, sample_df):
        prompt = PromptBuilder().build(sample_decision, sample_df, recent_days=10)
        assert "최근 10일" in prompt


# ── LLMAnalyzer 파싱 테스트 ────────────────────────────

class TestLLMAnalyzerParsing:
    def test_parse_valid_json(self):
        result = LLMAnalyzer._parse_response(_VALID_LLM_RESPONSE, "test-model")
        assert result.overall_assessment == "삼성전자는 강한 추세를 보이고 있습니다."
        assert len(result.key_risks) == 2
        assert result.confidence == pytest.approx(0.78)
        assert result.model == "test-model"

    def test_parse_with_markdown_fences(self):
        wrapped = f"```json\n{_VALID_LLM_RESPONSE}\n```"
        result  = LLMAnalyzer._parse_response(wrapped, "test-model")
        assert result.overall_assessment != ""

    def test_parse_invalid_json_fallback(self):
        result = LLMAnalyzer._parse_response("이건 JSON이 아닙니다.", "test-model")
        assert "JSON 파싱 실패" in result.signal_rationale
        assert result.raw_response == "이건 JSON이 아닙니다."

    def test_parse_opportunities(self):
        result = LLMAnalyzer._parse_response(_VALID_LLM_RESPONSE, "test-model")
        assert "AI 수요 증가" in result.opportunities


# ── LLMAnalyzer API 호출 모킹 테스트 ───────────────────

class TestLLMAnalyzerMocked:
    def _make_mock_message(self, text: str) -> MagicMock:
        msg              = MagicMock()
        content_block    = MagicMock()
        content_block.text = text
        msg.content      = [content_block]
        msg.usage        = MagicMock(input_tokens=500, output_tokens=200)
        return msg

    @patch("ta_trader.llm.analyzer.anthropic.Anthropic")
    def test_analyze_returns_llm_analysis(self, mock_anthropic, sample_decision, sample_df):
        mock_client = MagicMock()
        mock_anthropic.return_value = mock_client
        mock_client.messages.create.return_value = self._make_mock_message(_VALID_LLM_RESPONSE)

        llm    = LLMAnalyzer(api_key="test-key")
        result = llm.analyze(sample_decision, sample_df)

        assert isinstance(result, LLMAnalysis)
        assert result.confidence == pytest.approx(0.78)
        assert len(result.key_risks) == 2

    @patch("ta_trader.llm.analyzer.anthropic.Anthropic")
    def test_analyze_calls_api_once(self, mock_anthropic, sample_decision, sample_df):
        mock_client = MagicMock()
        mock_anthropic.return_value = mock_client
        mock_client.messages.create.return_value = self._make_mock_message(_VALID_LLM_RESPONSE)

        llm = LLMAnalyzer(api_key="test-key")
        llm.analyze(sample_decision, sample_df)

        mock_client.messages.create.assert_called_once()

    def test_missing_api_key_raises(self, monkeypatch):
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        from ta_trader.exceptions import TATraderError
        with pytest.raises(TATraderError, match="ANTHROPIC_API_KEY"):
            LLMAnalyzer(api_key=None)


# ── LLMAnalysis 모델 테스트 ────────────────────────────

class TestLLMAnalysisModel:
    def test_to_dict_keys(self):
        analysis = LLMAnalysis(
            overall_assessment = "판단",
            signal_rationale   = "근거",
            key_risks          = ["R1"],
            opportunities      = ["O1"],
            action_plan        = "플랜",
            confidence         = 0.9,
            model              = "claude-sonnet",
        )
        d = analysis.to_dict()
        assert "overall_assessment" in d
        assert "confidence" in d
        assert d["confidence"] == pytest.approx(0.9)
