"""
tests/test_value.py
가치 투자 5단계 분석 모듈 단위 테스트
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd
import pytest

from ta_trader.models.base import CheckItem, StageResult, StageStatus
from ta_trader.models.value import (
    ValueFundamentals, ValueGrade, ValueAnalysisResult,
)
from ta_trader.constants.value import (
    GRADE_STRONG_BUY, GRADE_BUY, GRADE_CONDITIONAL, GRADE_WATCH,
    PER_LOW_THRESHOLD, PBR_LOW_THRESHOLD,
    ROE_EXCELLENT, ROE_GOOD,
    DEBT_EQUITY_SAFE, DEBT_EQUITY_OK,
    SCORE_VALUATION_MAX, SCORE_PROFITABILITY_MAX,
    SCORE_FINANCIAL_MAX, SCORE_MARGIN_MAX, SCORE_ENTRY_MAX,
)
from ta_trader.formatters.value import format_value_result, format_value_report


# ── 모델 테스트 ───────────────────────────────────────────

class TestValueGrade:
    """ValueGrade Enum 테스트"""

    def test_stars(self) -> None:
        assert ValueGrade.STRONG_BUY.stars == "★★★★★"
        assert ValueGrade.UNFIT.stars == "★☆☆☆☆"

    def test_emoji(self) -> None:
        assert ValueGrade.STRONG_BUY.emoji == "🟢"
        assert ValueGrade.UNFIT.emoji == "🔴"

    def test_values(self) -> None:
        assert ValueGrade.STRONG_BUY.value == "적극매수"
        assert ValueGrade.BUY.value == "매수"
        assert ValueGrade.CONDITIONAL.value == "조건부매수"
        assert ValueGrade.WATCH.value == "관심관망"
        assert ValueGrade.UNFIT.value == "부적합"


class TestStageStatus:
    def test_values(self) -> None:
        assert StageStatus.PASS.value == "통과"
        assert StageStatus.NO_DATA.value == "데이터없음"


class TestCheckItem:
    def test_basic_creation(self) -> None:
        item = CheckItem(name="PER", passed=True, value=10.5, threshold=15.0, score=8.0)
        assert item.name == "PER"
        assert item.passed is True
        assert item.score == 8.0

    def test_defaults(self) -> None:
        item = CheckItem(name="test", passed=False)
        assert item.value is None
        assert item.score == 0.0
        assert item.description == ""


class TestStageResult:
    def test_pass_rate(self) -> None:
        checks = [
            CheckItem(name="a", passed=True),
            CheckItem(name="b", passed=True),
            CheckItem(name="c", passed=False),
        ]
        stage = StageResult(
            stage_num=1, stage_name="test",
            status=StageStatus.PARTIAL,
            score=15, max_score=25, checks=checks,
        )
        assert abs(stage.pass_rate - 2 / 3) < 0.01

    def test_score_pct(self) -> None:
        stage = StageResult(
            stage_num=1, stage_name="test",
            status=StageStatus.PASS,
            score=20, max_score=25,
        )
        assert abs(stage.score_pct - 80.0) < 0.01

    def test_empty_checks(self) -> None:
        stage = StageResult(
            stage_num=1, stage_name="test",
            status=StageStatus.NO_DATA,
            score=0, max_score=25,
        )
        assert stage.pass_rate == 0.0


class TestValueFundamentals:
    def test_has_valuation_data(self) -> None:
        f = ValueFundamentals(trailing_pe=15.0)
        assert f.has_valuation_data is True

    def test_no_valuation_data(self) -> None:
        f = ValueFundamentals()
        assert f.has_valuation_data is False

    def test_has_profitability_data(self) -> None:
        f = ValueFundamentals(roe=0.15)
        assert f.has_profitability_data is True

    def test_fcf_yield(self) -> None:
        f = ValueFundamentals(free_cashflow=100_000_000, market_cap=2_000_000_000)
        assert abs(f.fcf_yield - 0.05) < 0.001

    def test_fcf_yield_none(self) -> None:
        f = ValueFundamentals()
        assert f.fcf_yield is None

    def test_cash_conversion_ratio(self) -> None:
        f = ValueFundamentals(free_cashflow=120, net_income=100)
        assert abs(f.cash_conversion_ratio - 1.2) < 0.001

    def test_net_cash(self) -> None:
        f = ValueFundamentals(total_cash=500, total_debt=300)
        assert f.net_cash == 200

    def test_net_cash_negative(self) -> None:
        f = ValueFundamentals(total_cash=200, total_debt=500)
        assert f.net_cash == -300


class TestValueAnalysisResult:
    def test_get_stage(self) -> None:
        stages = [
            StageResult(stage_num=1, stage_name="밸류에이션", status=StageStatus.PASS, score=20, max_score=25),
            StageResult(stage_num=2, stage_name="수익성", status=StageStatus.PARTIAL, score=15, max_score=25),
        ]
        result = ValueAnalysisResult(
            ticker="AAPL", name="Apple", date="2025-01-01",
            current_price=150.0, stages=stages,
        )
        assert result.get_stage(1).stage_name == "밸류에이션"
        assert result.get_stage(2).stage_name == "수익성"
        assert result.get_stage(3) is None

    def test_to_dict(self) -> None:
        result = ValueAnalysisResult(
            ticker="AAPL", name="Apple", date="2025-01-01",
            current_price=150.0,
            total_score=65.0,
            grade=ValueGrade.BUY,
            margin_of_safety=0.25,
            fundamentals=ValueFundamentals(
                trailing_pe=15.0, pbr=3.5, roe=0.20, dividend_yield=0.015,
            ),
        )
        d = result.to_dict()
        assert d["Ticker"] == "AAPL"
        assert d["Score"] == 65.0
        assert d["MoS"] == "25%"
        assert d["PER"] == "15.0"


# ── 포매터 테스트 ─────────────────────────────────────────

class TestFormatter:
    def _make_result(
        self,
        ticker: str = "AAPL",
        score: float = 70.0,
        grade: ValueGrade = ValueGrade.BUY,
    ) -> ValueAnalysisResult:
        stages = [
            StageResult(stage_num=i, stage_name=f"S{i}",
                        status=StageStatus.PASS, score=score / 5, max_score=25)
            for i in range(1, 6)
        ]
        return ValueAnalysisResult(
            ticker=ticker, name="Test Corp", date="2025-01-01",
            current_price=100.0,
            stages=stages,
            total_score=score,
            grade=grade,
            fundamentals=ValueFundamentals(trailing_pe=12.0, pbr=1.5, roe=0.15),
            margin_of_safety=0.20,
            stop_loss=90.0,
            take_profit=125.0,
            risk_reward=2.5,
        )

    def test_single_result_contains_key_info(self) -> None:
        r = self._make_result()
        output = format_value_result(r)
        assert "AAPL" in output
        assert "가치 투자 분석 보고서" in output
        assert "안전마진" in output
        assert "5단계" in output

    def test_report_contains_table(self) -> None:
        results = [
            self._make_result("AAPL", 80, ValueGrade.STRONG_BUY),
            self._make_result("MSFT", 55, ValueGrade.CONDITIONAL),
            self._make_result("TSLA", 25, ValueGrade.UNFIT),
        ]
        output = format_value_report(results)
        assert "Value 종목 추천 보고서" in output
        assert "매수 추천 종목" in output
        assert "부적합 종목" in output
        assert "면책 조항" in output

    def test_empty_report(self) -> None:
        output = format_value_report([])
        assert "분석 결과가 없습니다" in output


# ── 상수 검증 테스트 ──────────────────────────────────────

class TestConstants:
    def test_score_sum_equals_100(self) -> None:
        total = (
            SCORE_VALUATION_MAX
            + SCORE_PROFITABILITY_MAX
            + SCORE_FINANCIAL_MAX
            + SCORE_MARGIN_MAX
            + SCORE_ENTRY_MAX
        )
        assert total == 100.0, f"점수 합계가 100이 아닙니다: {total}"

    def test_grade_thresholds_order(self) -> None:
        assert GRADE_STRONG_BUY > GRADE_BUY > GRADE_CONDITIONAL > GRADE_WATCH
