"""
tests/test_recommend.py
종목 추천 엔진 테스트

테스트 범위:
  - Grade: 등급 속성
  - Rationale: 근거 모델
  - RecommendationEngine: 다차원 평가 로직
    - 추세 분석 (강한 상승/하락/횡보)
    - 모멘텀 분석 (골든크로스/데드크로스/히스토그램)
    - 가격 위치 (과매도 반등/과매수 경고)
    - 변동성 (스퀴즈/극단적 변동성)
    - 전략 합치도 (복수 매수/매도 신호)
    - 등급 결정 로직
  - Report: 보고서 포매팅
"""

from __future__ import annotations

import pytest

from ta_trader.models.short import (
    IndicatorResult, MarketRegime, RiskLevels, Signal, StrategyType, TradingDecision,
)
from ta_trader.models.recommend import (
    Grade, Rationale, Recommendation, RecommendationReport
)
from ta_trader.recommend.engine import RecommendationEngine
from ta_trader.recommend.report import format_recommendation_report


# ── 헬퍼 팩토리 ──────────────────────────────────────────

def _make_indicator(
    name: str, raw_value: float, signal: Signal,
    score: float, description: str,
) -> IndicatorResult:
    return IndicatorResult(
        name=name, raw_value=raw_value,
        signal=signal, score=score, description=description,
    )


def _make_decision(
    ticker: str = "TEST",
    price: float = 100.0,
    score: float = 0.0,
    signal: Signal = Signal.NEUTRAL,
    regime: MarketRegime = MarketRegime.SIDEWAYS,
    strategy: StrategyType = StrategyType.MEAN_REVERSION,
    adx_desc: str = "ADX=15.0 (+DI=12.0, -DI=14.0) [횡보]",
    adx_val: float = 15.0,
    adx_signal: Signal = Signal.NEUTRAL,
    adx_score: float = 0.0,
    rsi_val: float = 50.0,
    rsi_signal: Signal = Signal.NEUTRAL,
    rsi_score: float = 0.0,
    macd_desc: str = "MACD=0.100 Signal=0.050 Hist=0.050",
    macd_val: float = 0.05,
    macd_signal: Signal = Signal.BUY,
    macd_score: float = 20.0,
    bb_val: float = 0.5,
    bb_signal: Signal = Signal.NEUTRAL,
    bb_score: float = 0.0,
    bb_desc: str = "BB%=50.0% (상단=110.00 중간=100.00 하단=90.00) 밴드폭=8.0%",
    stop_loss: float = 95.0,
    take_profit: float = 110.0,
    rr: float = 2.0,
) -> TradingDecision:
    return TradingDecision(
        ticker=ticker,
        name=f"{ticker} Inc",
        date="2024-06-01",
        current_price=price,
        market_regime=regime,
        strategy_type=strategy,
        composite_score=score,
        final_signal=signal,
        indicators=[
            _make_indicator("ADX", adx_val, adx_signal, adx_score, adx_desc),
            _make_indicator("RSI", rsi_val, rsi_signal, rsi_score, f"RSI={rsi_val:.1f} [중립구간]"),
            _make_indicator("MACD", macd_val, macd_signal, macd_score, macd_desc),
            _make_indicator("Bollinger Bands", bb_val, bb_signal, bb_score, bb_desc),
        ],
        risk=RiskLevels(stop_loss=stop_loss, take_profit=take_profit, risk_reward_ratio=rr),
        summary="test",
        regime_detail="test detail",
    )


# ── Grade 테스트 ──────────────────────────────────────────

class TestGrade:
    def test_emoji(self):
        assert Grade.STRONG_BUY.emoji == "🟢"
        assert Grade.AVOID.emoji == "🔴"

    def test_values(self):
        assert Grade.STRONG_BUY.value == "적극매수"
        assert Grade.WATCH.value == "관망"


# ── 추세 분석 테스트 ──────────────────────────────────────

class TestTrendAnalysis:
    def test_strong_uptrend_generates_bullish(self):
        """ADX=50 + +DI 우위 → 긍정 요인"""
        dec = _make_decision(
            score=17.0, signal=Signal.BUY,
            regime=MarketRegime.STRONG_TREND,
            strategy=StrategyType.TREND_FOLLOWING,
            adx_val=50.0, adx_signal=Signal.STRONG_BUY, adx_score=50.0,
            adx_desc="ADX=50.0 (+DI=35.0, -DI=11.0) [강한추세]",
        )
        engine = RecommendationEngine()
        rec = engine._evaluate_single(dec)
        trend_bullish = [r for r in rec.bullish_factors if r.category == "추세"]
        assert len(trend_bullish) >= 1
        assert "강한 상승 추세" in trend_bullish[0].summary

    def test_strong_downtrend_generates_bearish(self):
        """ADX=35 + -DI 우위 → 부정 요인"""
        dec = _make_decision(
            score=-20.0, signal=Signal.SELL,
            regime=MarketRegime.STRONG_TREND,
            strategy=StrategyType.TREND_FOLLOWING,
            adx_val=35.0, adx_signal=Signal.STRONG_SELL, adx_score=-35.0,
            adx_desc="ADX=35.0 (+DI=10.0, -DI=28.0) [강한추세]",
        )
        engine = RecommendationEngine()
        rec = engine._evaluate_single(dec)
        trend_bearish = [r for r in rec.bearish_factors if r.category == "추세"]
        assert len(trend_bearish) >= 1
        assert "하락 추세" in trend_bearish[0].summary

    def test_sideways_generates_risk(self):
        """ADX=12 → 추세 부재 리스크"""
        dec = _make_decision(adx_val=12.0, adx_desc="ADX=12.0 (+DI=10.0, -DI=11.0) [횡보]")
        engine = RecommendationEngine()
        rec = engine._evaluate_single(dec)
        trend_risks = [r for r in rec.risk_factors if r.category == "추세"]
        assert len(trend_risks) >= 1
        assert "횡보" in trend_risks[0].summary


# ── 모멘텀 분석 테스트 ────────────────────────────────────

class TestMomentumAnalysis:
    def test_golden_cross(self):
        """MACD 골든크로스 → 긍정 요인"""
        dec = _make_decision(
            macd_desc="MACD=0.500 Signal=0.400 Hist=0.100 [크로스 발생!]",
            macd_val=0.1, macd_signal=Signal.STRONG_BUY, macd_score=60.0,
        )
        engine = RecommendationEngine()
        rec = engine._evaluate_single(dec)
        momentum = [r for r in rec.bullish_factors if r.category == "모멘텀"]
        assert len(momentum) >= 1
        assert "골든크로스" in momentum[0].summary

    def test_dead_cross(self):
        """MACD 데드크로스 → 부정 요인"""
        dec = _make_decision(
            macd_desc="MACD=-0.500 Signal=-0.300 Hist=-0.200 [크로스 발생!]",
            macd_val=-0.2, macd_signal=Signal.STRONG_SELL, macd_score=-60.0,
        )
        engine = RecommendationEngine()
        rec = engine._evaluate_single(dec)
        momentum = [r for r in rec.bearish_factors if r.category == "모멘텀"]
        assert len(momentum) >= 1
        assert "데드크로스" in momentum[0].summary

    def test_histogram_turning_positive(self):
        """히스토그램 양전환(MACD 라인 음수) → 반전 초기 신호"""
        dec = _make_decision(
            macd_desc="MACD=-1.000 Signal=-1.200 Hist=0.200",
            macd_val=0.2, macd_signal=Signal.BUY, macd_score=15.0,
        )
        engine = RecommendationEngine()
        rec = engine._evaluate_single(dec)
        momentum = [r for r in rec.bullish_factors if r.category == "모멘텀"]
        assert len(momentum) >= 1
        assert "양전환" in momentum[0].summary or "모멘텀" in momentum[0].summary


# ── 가격 위치 분석 테스트 ─────────────────────────────────

class TestPricePosition:
    def test_oversold_bb_rsi_combo(self):
        """RSI 과매도 + BB 하단 → 강한 반등 후보"""
        dec = _make_decision(
            rsi_val=25.0, rsi_signal=Signal.STRONG_BUY, rsi_score=80.0,
            bb_val=0.1, bb_signal=Signal.BUY, bb_score=50.0,
        )
        engine = RecommendationEngine()
        rec = engine._evaluate_single(dec)
        price_bullish = [r for r in rec.bullish_factors if r.category == "가격위치"]
        assert len(price_bullish) >= 1
        assert "반등" in price_bullish[0].summary

    def test_overbought_bb_rsi_combo(self):
        """RSI 과매수 + BB 상단 → 과열 경고"""
        dec = _make_decision(
            rsi_val=78.0, rsi_signal=Signal.STRONG_SELL, rsi_score=-80.0,
            bb_val=0.9, bb_signal=Signal.SELL, bb_score=-40.0,
        )
        engine = RecommendationEngine()
        rec = engine._evaluate_single(dec)
        price_bearish = [r for r in rec.bearish_factors if r.category == "가격위치"]
        assert len(price_bearish) >= 1
        assert "과열" in price_bearish[0].summary or "과매수" in price_bearish[0].summary

    def test_rsi_overbought_in_trend(self):
        """강한 추세에서 RSI 과매수 → 부정이 아닌 리스크 (추세 지속 가능)"""
        dec = _make_decision(
            regime=MarketRegime.STRONG_TREND,
            strategy=StrategyType.TREND_FOLLOWING,
            adx_val=35.0, adx_desc="ADX=35.0 (+DI=30.0, -DI=10.0) [강한추세]",
            adx_signal=Signal.STRONG_BUY, adx_score=35.0,
            rsi_val=72.0, rsi_signal=Signal.STRONG_SELL, rsi_score=-80.0,
            bb_val=0.65, bb_signal=Signal.NEUTRAL, bb_score=0.0,
        )
        engine = RecommendationEngine()
        rec = engine._evaluate_single(dec)
        # 추세장 RSI 과매수는 bearish가 아닌 risk로 분류
        rsi_risk = [r for r in rec.risk_factors if "과매수" in r.summary and "추세장" in r.summary]
        rsi_bear = [r for r in rec.bearish_factors if "과매수" in r.summary]
        # 추세장에서는 risk로 분류되어야 함
        assert len(rsi_risk) >= 1 or len(rsi_bear) == 0


# ── 변동성 분석 테스트 ────────────────────────────────────

class TestVolatilityAnalysis:
    def test_squeeze_detected(self):
        """밴드폭 3% → 스퀴즈 감지"""
        dec = _make_decision(
            bb_desc="BB%=50.0% (상단=102.00 중간=100.00 하단=98.00) 밴드폭=3.0%",
        )
        engine = RecommendationEngine()
        rec = engine._evaluate_single(dec)
        vol_bullish = [r for r in rec.bullish_factors if r.category == "변동성"]
        assert len(vol_bullish) >= 1
        assert "스퀴즈" in vol_bullish[0].summary

    def test_extreme_volatility(self):
        """밴드폭 40% → 극단적 변동성 리스크"""
        dec = _make_decision(
            bb_desc="BB%=50.0% (상단=140.00 중간=100.00 하단=60.00) 밴드폭=40.0%",
        )
        engine = RecommendationEngine()
        rec = engine._evaluate_single(dec)
        vol_risks = [r for r in rec.risk_factors if r.category == "변동성"]
        assert len(vol_risks) >= 1
        assert "극단적" in vol_risks[0].summary or "변동성" in vol_risks[0].summary


# ── 전략 합치도 테스트 ────────────────────────────────────

class TestConfluence:
    def test_all_bullish_high_confluence(self):
        """4개 지표 모두 매수 → 높은 합치도"""
        dec = _make_decision(
            adx_signal=Signal.BUY, rsi_signal=Signal.BUY,
            macd_signal=Signal.BUY, bb_signal=Signal.BUY,
        )
        engine = RecommendationEngine()
        rec = engine._evaluate_single(dec)
        confluence = [r for r in rec.bullish_factors if r.category == "전략합치"]
        assert len(confluence) >= 1
        assert "높은 합치도" in confluence[0].summary or "매수 우위" in confluence[0].summary

    def test_all_bearish_not_buyable(self):
        """4개 지표 모두 매도 → 매수 비적합"""
        dec = _make_decision(
            score=-30.0, signal=Signal.SELL,
            adx_signal=Signal.SELL, rsi_signal=Signal.SELL,
            macd_signal=Signal.SELL, bb_signal=Signal.SELL,
        )
        engine = RecommendationEngine()
        rec = engine._evaluate_single(dec)
        confluence = [r for r in rec.bearish_factors if r.category == "전략합치"]
        assert len(confluence) >= 1

    def test_mixed_signals_risk(self):
        """매수2/매도2 혼재 → 리스크"""
        dec = _make_decision(
            adx_signal=Signal.BUY, rsi_signal=Signal.SELL,
            macd_signal=Signal.BUY, bb_signal=Signal.SELL,
        )
        engine = RecommendationEngine()
        rec = engine._evaluate_single(dec)
        confluence = [r for r in rec.risk_factors if r.category == "전략합치"]
        assert len(confluence) >= 1
        assert "혼재" in confluence[0].summary


# ── 등급 결정 테스트 ──────────────────────────────────────

class TestGrading:
    def test_strong_buy_conditions(self):
        """높은 점수 + 강한 상승 추세 + 복수 매수 신호 → 적극매수"""
        dec = _make_decision(
            ticker="BULL", score=25.0, signal=Signal.BUY,
            regime=MarketRegime.STRONG_TREND,
            strategy=StrategyType.TREND_FOLLOWING,
            adx_val=40.0, adx_signal=Signal.STRONG_BUY, adx_score=40.0,
            adx_desc="ADX=40.0 (+DI=30.0, -DI=10.0) [강한추세]",
            rsi_val=55.0, rsi_signal=Signal.BUY, rsi_score=10.0,
            macd_desc="MACD=1.000 Signal=0.500 Hist=0.500 [크로스 발생!]",
            macd_val=0.5, macd_signal=Signal.STRONG_BUY, macd_score=70.0,
            bb_val=0.5, bb_signal=Signal.NEUTRAL, bb_score=0.0,
        )
        engine = RecommendationEngine()
        rec = engine._evaluate_single(dec)
        assert rec.grade in (Grade.STRONG_BUY, Grade.BUY)

    def test_avoid_conditions(self):
        """매도 신호 + 부정 요인 다수 → 비추천"""
        dec = _make_decision(
            ticker="BEAR", score=-25.0, signal=Signal.SELL,
            regime=MarketRegime.STRONG_TREND,
            strategy=StrategyType.TREND_FOLLOWING,
            adx_val=35.0, adx_signal=Signal.STRONG_SELL, adx_score=-35.0,
            adx_desc="ADX=35.0 (+DI=8.0, -DI=30.0) [강한추세]",
            rsi_val=72.0, rsi_signal=Signal.STRONG_SELL, rsi_score=-80.0,
            macd_desc="MACD=-2.000 Signal=-1.500 Hist=-0.500",
            macd_val=-0.5, macd_signal=Signal.SELL, macd_score=-40.0,
            bb_val=0.85, bb_signal=Signal.SELL, bb_score=-30.0,
        )
        engine = RecommendationEngine()
        rec = engine._evaluate_single(dec)
        assert rec.grade == Grade.AVOID

    def test_watch_conditions(self):
        """중립 점수 + 혼재 신호 → 관망"""
        dec = _make_decision(ticker="FLAT", score=-5.0, signal=Signal.NEUTRAL)
        engine = RecommendationEngine()
        rec = engine._evaluate_single(dec)
        assert rec.grade in (Grade.WATCH, Grade.CONDITIONAL)


# ── 복수 종목 분석 + 리포트 테스트 ────────────────────────

class TestMultiAnalysis:
    def test_ranking(self):
        """복수 종목 분석 시 등급·신뢰도 순 정렬"""
        decisions = [
            _make_decision(ticker="A", score=-20.0, signal=Signal.SELL,
                           adx_signal=Signal.SELL, macd_signal=Signal.SELL),
            _make_decision(ticker="B", score=25.0, signal=Signal.BUY,
                           adx_signal=Signal.STRONG_BUY,
                           adx_val=40.0, adx_desc="ADX=40.0 (+DI=30.0, -DI=10.0) [강한추세]",
                           regime=MarketRegime.STRONG_TREND,
                           strategy=StrategyType.TREND_FOLLOWING,
                           macd_signal=Signal.BUY, rsi_signal=Signal.BUY),
            _make_decision(ticker="C", score=5.0, signal=Signal.NEUTRAL),
        ]
        engine = RecommendationEngine()
        report = engine.analyze(decisions)

        assert len(report.recommendations) == 3
        # B가 1순위 (매수 신호 + 높은 점수)
        assert report.recommendations[0].ticker == "B"
        # 순위가 부여되어 있어야 함
        assert report.recommendations[0].rank == 1
        assert report.recommendations[1].rank == 2

    def test_report_categorization(self):
        """매수/관망/비추천 분류 검증"""
        decisions = [
            _make_decision(ticker="BUY1", score=20.0, signal=Signal.BUY,
                           adx_signal=Signal.BUY, macd_signal=Signal.BUY,
                           rsi_signal=Signal.BUY,
                           adx_val=30.0, adx_desc="ADX=30.0 (+DI=25.0, -DI=12.0) [강한추세]",
                           regime=MarketRegime.STRONG_TREND,
                           strategy=StrategyType.TREND_FOLLOWING),
            _make_decision(ticker="SELL1", score=-25.0, signal=Signal.SELL,
                           adx_signal=Signal.SELL, macd_signal=Signal.SELL,
                           rsi_signal=Signal.SELL, bb_signal=Signal.SELL),
        ]
        engine = RecommendationEngine()
        report = engine.analyze(decisions)

        assert len(report.buy_picks) >= 1
        assert report.buy_picks[0].ticker == "BUY1"
        assert len(report.avoid_list) >= 1
        assert report.avoid_list[0].ticker == "SELL1"


# ── Report 포매팅 테스트 ──────────────────────────────────

class TestReportFormat:
    def test_format_nonempty(self):
        decisions = [
            _make_decision(ticker="AAPL", score=15.0, signal=Signal.BUY,
                           adx_signal=Signal.BUY, macd_signal=Signal.BUY),
            _make_decision(ticker="TSLA", score=-10.0, signal=Signal.NEUTRAL),
        ]
        engine = RecommendationEngine()
        report = engine.analyze(decisions)
        text = format_recommendation_report(report)

        assert "AAPL" in text
        assert "TSLA" in text
        assert "추천" in text
        assert "긍정 요인" in text or "부정 요인" in text

    def test_format_empty(self):
        report = RecommendationReport(date="2024-01-01")
        text = format_recommendation_report(report)
        assert "추천 보고서" in text


# ── 진입 조건 / 행동 제안 테스트 ──────────────────────────

class TestActionPlan:
    def test_trend_entry_condition(self):
        dec = _make_decision(
            strategy=StrategyType.TREND_FOLLOWING,
            score=20.0, signal=Signal.BUY,
            adx_val=30.0, adx_desc="ADX=30.0 (+DI=25.0, -DI=12.0) [강한추세]",
            adx_signal=Signal.BUY, macd_signal=Signal.BUY,
            regime=MarketRegime.STRONG_TREND,
        )
        engine = RecommendationEngine()
        rec = engine._evaluate_single(dec)
        assert "+DI" in rec.entry_condition or "추세" in rec.entry_condition

    def test_avoid_action_plan(self):
        dec = _make_decision(
            score=-25.0, signal=Signal.SELL,
            adx_signal=Signal.SELL, macd_signal=Signal.SELL,
            rsi_signal=Signal.SELL, bb_signal=Signal.SELL,
        )
        engine = RecommendationEngine()
        rec = engine._evaluate_single(dec)
        assert "비추천" in rec.action_plan or "피하" in rec.action_plan
