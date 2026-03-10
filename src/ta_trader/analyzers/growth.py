"""
ta_trader/analyzers/growth.py
GrowthMomentumAnalyzer — 100% 상승 후보 발굴 6단계 분석 엔진

프로세스:
  [1단계] 이익 가속 필터   → EPS/매출 성장률 (yfinance info)
  [2단계] 촉매 확인        → 섹터/산업 정보 (수동 확인 플래그)
  [3단계] 스테이지 판별    → 이평선 정배열, 52주 위치, 상대강도
  [4단계] 기술적 진입 조건 → ADX/MACD/BB/RSI + 거래량
  [5단계] 리스크 관리      → ATR 기반 손절/익절, R:R 비율
  [6단계] 보유 관리        → 추세 건강도 모니터링

사용 예:
    analyzer = GrowthMomentumAnalyzer("AAPL")
    result = analyzer.analyze()
    print(f"{result.grade.stars} {result.total_score:.1f}점")
"""

from __future__ import annotations

from typing import Optional

import numpy as np
import pandas as pd

from ta_trader.base.analyzer import BaseAnalyzer
from ta_trader.data.fetcher import DataFetcher
from ta_trader.indicators.adx import ADXAnalyzer
from ta_trader.indicators.bollinger import BollingerAnalyzer
from ta_trader.indicators.calculator import IndicatorCalculator
from ta_trader.indicators.macd import MACDAnalyzer
from ta_trader.indicators.rsi import RSIAnalyzer
from ta_trader.utils.logger import get_logger

from ta_trader.growth.constants import (
    # 1단계
    EPS_GROWTH_MIN, REVENUE_GROWTH_MIN, PROFIT_MARGIN_MIN,
    SCORE_EPS_GROWTH, SCORE_REVENUE_GROWTH,
    SCORE_PROFIT_MARGIN, SCORE_EARNINGS_SURPRISE, SCORE_EARNINGS_MAX,
    # 3단계
    SMA_150_WINDOW, SMA_200_WINDOW, SMA_50_WINDOW,
    SEPA_ABOVE_52W_LOW_PCT, SEPA_NEAR_52W_HIGH_PCT,
    SMA200_UPTREND_DAYS,
    SCORE_MA_ALIGNMENT, SCORE_SMA200_UPTREND,
    SCORE_52W_POSITION, SCORE_RS_RANK, SCORE_STAGE_MAX,
    # 4단계
    VOLUME_BREAKOUT_RATIO, VOLUME_AVG_WINDOW,
    ADX_RISING_MIN, ADX_ENTRY_IDEAL, ADX_LATE_ENTRY,
    MACD_ZERO_CROSS, RSI_BULLISH_MIN, RSI_OVERHEAT,
    BB_BREAKOUT_UPPER, BB_SQUEEZE_THRESHOLD,
    SCORE_ADX_GATE, SCORE_MACD_DIRECTION, SCORE_BB_BREAKOUT,
    SCORE_RSI_ZONE, SCORE_VOLUME_CONFIRM, SCORE_TECHNICAL_MAX,
    # 5단계
    GROWTH_ATR_SL_MULTIPLIER, GROWTH_ATR_TP_MULTIPLIER,
    GROWTH_DEFAULT_SL_PCT, GROWTH_DEFAULT_TP_PCT,
    GROWTH_MIN_RR_RATIO, GROWTH_IDEAL_RR_RATIO,
    SCORE_RR_ADEQUATE, SCORE_RR_IDEAL, SCORE_RISK_MAX,
    # 6단계
    HOLD_ADX_HEALTHY, HOLD_MACD_POSITIVE, HOLD_RSI_BULLISH, HOLD_DI_MARGIN,
    SCORE_ADX_HEALTH, SCORE_MACD_HEALTH, SCORE_DI_HEALTH,
    SCORE_RSI_HEALTH, SCORE_HOLD_MAX,
    # 종합
    GRADE_STRONG_BUY, GRADE_BUY, GRADE_CONDITIONAL, GRADE_WATCH,
    GROWTH_DEFAULT_PERIOD, GROWTH_MIN_DATA_ROWS,
)
from ta_trader.models.base import CheckItem, StageResult, StageStatus
from ta_trader.models.growth import (
    FundamentalData, GrowthGrade, GrowthScreenResult,
)

logger = get_logger(__name__)


class GrowthMomentumAnalyzer(BaseAnalyzer[GrowthScreenResult]):
    """
    100% 상승 후보 발굴을 위한 6단계 분석 엔진.

    ShortTermAnalyzer가 '현재 시점의 매매 신호'를 분석한다면,
    GrowthMomentumAnalyzer는 '향후 1년 내 대폭 상승할 잠재력'을 평가합니다.

    사용 예:
        analyzer = GrowthMomentumAnalyzer("NVDA")
        result = analyzer.analyze()

        analyzer = GrowthMomentumAnalyzer("005930.KS", period="2y")
        result = analyzer.analyze()
    """

    @property
    def name(self) -> str:
        return "데이터 분석 에이전트"

    @property
    def role(self) -> str:
        return "시장 데이터 수집 및 기술적 지표 연산"

    def analyze(self) -> GrowthScreenResult:
        """6단계 전체 분석 파이프라인 실행"""
        # 0. 데이터 수집
        self._fetch_data()

        # 추가 컬럼: SMA 150/200/50, 거래량 평균
        close = self._df["Close"]
        self._df["sma_50"]  = close.rolling(window=min(SMA_50_WINDOW, len(close))).mean()
        self._df["sma_150"] = close.rolling(window=min(SMA_150_WINDOW, len(close))).mean()
        self._df["sma_200"] = close.rolling(window=min(SMA_200_WINDOW, len(close))).mean()

        if "Volume" in self._df.columns:
            self._df["vol_avg_50"] = (
                self._df["Volume"]
                .rolling(window=min(VOLUME_AVG_WINDOW, len(self._df)))
                .mean()
            )

        # 6단계 순차 실행
        s1 = self._stage1_earnings()
        s2 = self._stage2_catalyst()
        s3 = self._stage3_stage_analysis()
        s4 = self._stage4_technical_entry()
        s5 = self._stage5_risk_management()
        s6 = self._stage6_hold_health()

        stages = [s1, s2, s3, s4, s5, s6]

        # 종합 점수 (2단계는 수동이므로 점수 미포함)
        total = sum(s.score for s in stages)
        grade = self._score_to_grade(total)
        action = self._determine_action(grade, stages)
        warnings = self._collect_warnings(stages)

        # 가격 위치 정보
        latest = self._calc.latest()
        price = float(latest["Close"])

        result = GrowthScreenResult(
            ticker        = self.ticker,
            name          = self._name,
            date          = str(self._df.index[-1].date()),
            current_price = price,
            stages        = stages,
            total_score   = round(total, 1),
            grade         = grade,
            fundamentals  = self._extract_fundamentals(),
            stop_loss     = s5.checks[0].value if s5.checks else None,
            take_profit   = s5.checks[1].value if len(s5.checks) > 1 else None,
            risk_reward   = s5.checks[2].value if len(s5.checks) > 2 else None,
            high_52w      = self._get_52w_high(),
            low_52w       = self._get_52w_low(),
            sma_150       = self._get_sma(SMA_150_WINDOW),
            sma_200       = self._get_sma(SMA_200_WINDOW),
            warnings      = warnings,
            action        = action,
        )

        logger.info(
            "Growth 분석 완료",
            ticker=self.ticker, name=self._name,
            score=total, grade=grade.value,
        )
        return result

    def analyze_with_llm(
        self,
        provider:    str | None = None,
        api_key:     str | None = None,
        model:       str | None = None,
        recent_days: int = 10,
        stream:      bool = False,
    ) -> GrowthScreenResult:
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
            llm_analysis 필드가 채워진 GrowthScreenResult
        """
        from ta_trader.llm.factory import create_llm_analyzer

        # 기술적 분석이 아직 실행되지 않았으면 실행
        result = self.analyze()
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

        result.llm_analysis = llm_result

        return result

    # ── 1단계: 이익 가속 필터 ────────────────────────────

    def _stage1_earnings(self) -> StageResult:
        """yfinance info에서 EPS/매출 성장률, 이익률, 서프라이즈 확인"""
        checks: list[CheckItem] = []
        score = 0.0
        info = self._info

        # EPS 성장률
        eps_g = info.get("earningsQuarterlyGrowth") or info.get("earningsGrowth")
        if eps_g is not None:
            passed = eps_g >= EPS_GROWTH_MIN
            pts = SCORE_EPS_GROWTH if passed else SCORE_EPS_GROWTH * max(0, eps_g / EPS_GROWTH_MIN)
            score += pts
            checks.append(CheckItem(
                name="EPS 성장률", passed=passed,
                value=eps_g, threshold=EPS_GROWTH_MIN,
                score=round(pts, 1),
                description=f"EPS 성장률 {eps_g:.1%} {'≥' if passed else '<'} {EPS_GROWTH_MIN:.0%}",
            ))
        else:
            checks.append(CheckItem(
                name="EPS 성장률", passed=False,
                description="데이터 없음 (수동 확인 필요)",
            ))

        # 매출 성장률
        rev_g = info.get("revenueGrowth")
        if rev_g is not None:
            passed = rev_g >= REVENUE_GROWTH_MIN
            pts = SCORE_REVENUE_GROWTH if passed else SCORE_REVENUE_GROWTH * max(0, rev_g / REVENUE_GROWTH_MIN)
            score += pts
            checks.append(CheckItem(
                name="매출 성장률", passed=passed,
                value=rev_g, threshold=REVENUE_GROWTH_MIN,
                score=round(pts, 1),
                description=f"매출 성장률 {rev_g:.1%} {'≥' if passed else '<'} {REVENUE_GROWTH_MIN:.0%}",
            ))
        else:
            checks.append(CheckItem(
                name="매출 성장률", passed=False,
                description="데이터 없음 (수동 확인 필요)",
            ))

        # 영업이익률
        margin = info.get("operatingMargins") or info.get("profitMargins")
        if margin is not None:
            passed = margin > PROFIT_MARGIN_MIN
            pts = SCORE_PROFIT_MARGIN if passed else 0.0
            score += pts
            checks.append(CheckItem(
                name="영업이익률", passed=passed,
                value=margin, threshold=PROFIT_MARGIN_MIN,
                score=round(pts, 1),
                description=f"영업이익률 {margin:.1%} {'> 0' if passed else '≤ 0'}",
            ))
        else:
            checks.append(CheckItem(
                name="영업이익률", passed=False,
                description="데이터 없음 (수동 확인 필요)",
            ))

        # 어닝 서프라이즈 (추정)
        target_price = info.get("targetMeanPrice")
        current = info.get("currentPrice") or info.get("regularMarketPrice")
        if target_price and current and target_price > current:
            pts = SCORE_EARNINGS_SURPRISE
            score += pts
            checks.append(CheckItem(
                name="애널리스트 목표가", passed=True,
                value=target_price, threshold=current,
                score=round(pts, 1),
                description=f"목표가 {target_price:,.0f} > 현재가 {current:,.0f} (상방 여력)",
            ))
        else:
            checks.append(CheckItem(
                name="애널리스트 목표가", passed=False,
                description="목표가 데이터 없음 또는 하방",
            ))

        score = min(score, SCORE_EARNINGS_MAX)
        status = self._classify_status(checks)

        return StageResult(
            stage_num=1, stage_name="이익 가속 필터",
            status=status, score=round(score, 1),
            max_score=SCORE_EARNINGS_MAX, checks=checks,
            description=self._stage1_summary(checks),
        )

    # ── 2단계: 촉매 확인 (수동) ──────────────────────────

    def _stage2_catalyst(self) -> StageResult:
        """섹터/산업 정보 제공, 실질적 판단은 수동"""
        checks: list[CheckItem] = []
        info = self._info

        sector = info.get("sector", "N/A")
        industry = info.get("industry", "N/A")
        summary = info.get("longBusinessSummary", "")

        checks.append(CheckItem(
            name="섹터/산업", passed=True,
            description=f"{sector} > {industry}",
        ))

        # 사업 요약 (120자 이내)
        if summary:
            checks.append(CheckItem(
                name="사업 요약", passed=True,
                description=summary[:120] + ("..." if len(summary) > 120 else ""),
            ))

        # 시가총액 규모
        mcap = info.get("marketCap")
        if mcap:
            if mcap < 2e9:
                cap_label = "소형주 (2배 상승 빈도 높음)"
            elif mcap < 10e9:
                cap_label = "중형주"
            elif mcap < 100e9:
                cap_label = "대형주 (2배 상승 난이도 높음)"
            else:
                cap_label = "초대형주 (2배 상승 매우 어려움)"
            checks.append(CheckItem(
                name="시가총액", passed=mcap < 100e9,
                value=mcap,
                description=f"${mcap/1e9:.1f}B — {cap_label}",
            ))

        return StageResult(
            stage_num=2, stage_name="촉매 확인",
            status=StageStatus.MANUAL,
            score=0.0, max_score=0.0,
            checks=checks,
            description="정성적 판단 필요: 신제품/신시장/산업구조변화/규제변화 확인",
        )

    # ── 3단계: 스테이지 판별 ─────────────────────────────

    def _stage3_stage_analysis(self) -> StageResult:
        """미너비니 SEPA 기준 + 스테이지 분석"""
        checks: list[CheckItem] = []
        score = 0.0
        df = self._df
        latest = df.iloc[-1]
        price = float(latest["Close"])

        # (A) 이평선 정배열: 현재가 > SMA150 > SMA200
        sma150 = self._get_sma(SMA_150_WINDOW)
        sma200 = self._get_sma(SMA_200_WINDOW)

        if sma150 is not None and sma200 is not None:
            aligned = price > sma150 > sma200
            pts = SCORE_MA_ALIGNMENT if aligned else 0.0
            score += pts
            checks.append(CheckItem(
                name="이평선 정배열", passed=aligned, score=round(pts, 1),
                description=(
                    f"현재가 {price:,.0f} {'>' if price > sma150 else '≤'} "
                    f"150일 {sma150:,.0f} {'>' if sma150 > sma200 else '≤'} "
                    f"200일 {sma200:,.0f}"
                ),
            ))
        else:
            checks.append(CheckItem(
                name="이평선 정배열", passed=False,
                description="데이터 부족 (200거래일 미만)",
            ))

        # (B) 200일선 상승 지속 (최근 22거래일)
        if sma200 is not None and len(df) >= SMA200_UPTREND_DAYS + 1:
            sma200_series = df["sma_200"].dropna()
            if len(sma200_series) >= SMA200_UPTREND_DAYS:
                recent_sma200 = sma200_series.tail(SMA200_UPTREND_DAYS)
                uptrend = float(recent_sma200.iloc[-1]) > float(recent_sma200.iloc[0])
                pts = SCORE_SMA200_UPTREND if uptrend else 0.0
                score += pts
                change_pct = (float(recent_sma200.iloc[-1]) / float(recent_sma200.iloc[0]) - 1)
                checks.append(CheckItem(
                    name="200일선 상승", passed=uptrend, score=round(pts, 1),
                    value=change_pct,
                    description=f"200일선 최근 1개월 변화: {change_pct:+.2%} ({'상승' if uptrend else '하락'})",
                ))
            else:
                checks.append(CheckItem(
                    name="200일선 상승", passed=False,
                    description="데이터 부족",
                ))
        else:
            checks.append(CheckItem(
                name="200일선 상승", passed=False,
                description="데이터 부족",
            ))

        # (C) 52주 고/저 위치
        high_52w = self._get_52w_high()
        low_52w = self._get_52w_low()

        if high_52w and low_52w and low_52w > 0:
            above_low = (price - low_52w) / low_52w
            below_high = (high_52w - price) / high_52w

            above_ok = above_low >= SEPA_ABOVE_52W_LOW_PCT
            near_high = below_high <= SEPA_NEAR_52W_HIGH_PCT
            both_ok = above_ok and near_high
            pts = SCORE_52W_POSITION if both_ok else (SCORE_52W_POSITION * 0.5 if above_ok else 0.0)
            score += pts
            checks.append(CheckItem(
                name="52주 위치", passed=both_ok, score=round(pts, 1),
                description=(
                    f"52주 저가 대비 +{above_low:.1%} ({'✓' if above_ok else '✗'} ≥+30%) | "
                    f"52주 고가 대비 -{below_high:.1%} ({'✓' if near_high else '✗'} ≤-25%)"
                ),
            ))
        else:
            checks.append(CheckItem(
                name="52주 위치", passed=False,
                description="52주 고/저 데이터 부족",
            ))

        # (D) 상대강도 (RS) — 6개월 수익률 기준 단순 평가
        if len(df) >= 126:
            ret_6m = (price / float(df["Close"].iloc[-126])) - 1
            # RS > 0 이면 최소 시장 평균 이상 (간이 판정)
            strong = ret_6m > 0.10  # 6개월 +10% 이상
            pts = SCORE_RS_RANK if strong else (SCORE_RS_RANK * 0.5 if ret_6m > 0 else 0.0)
            score += pts
            checks.append(CheckItem(
                name="상대강도 (6개월 수익률)", passed=strong,
                value=ret_6m, score=round(pts, 1),
                description=f"6개월 수익률 {ret_6m:+.1%} ({'강세' if strong else '약세/보통'})",
            ))
        else:
            checks.append(CheckItem(
                name="상대강도", passed=False,
                description="데이터 부족 (6개월 미만)",
            ))

        score = min(score, SCORE_STAGE_MAX)
        status = self._classify_status(checks)

        # 스테이지 판별
        stage_label = self._determine_stage(checks, price, sma150, sma200)

        return StageResult(
            stage_num=3, stage_name="스테이지 판별",
            status=status, score=round(score, 1),
            max_score=SCORE_STAGE_MAX, checks=checks,
            description=stage_label,
        )

    # ── 4단계: 기술적 진입 조건 ──────────────────────────

    def _stage4_technical_entry(self) -> StageResult:
        """ADX/MACD/BB/RSI + 거래량으로 기반 패턴 돌파 확인"""
        checks: list[CheckItem] = []
        score = 0.0
        latest = self._calc.latest()
        prev = self._calc.previous()

        # (A) ADX 게이트 — 상승 전환 중 25~40 구간
        adx = float(latest["adx"])
        adx_rising = prev is not None and adx > float(prev["adx"])

        if adx >= ADX_ENTRY_IDEAL and adx < ADX_LATE_ENTRY:
            pts = SCORE_ADX_GATE
            desc = f"ADX={adx:.1f} (강한 추세, 이상적 진입)"
            passed = True
        elif adx >= ADX_RISING_MIN and adx_rising:
            pts = SCORE_ADX_GATE * 0.7
            desc = f"ADX={adx:.1f} (상승 전환 중, 추세 형성 초기)"
            passed = True
        elif adx >= ADX_LATE_ENTRY:
            pts = SCORE_ADX_GATE * 0.3
            desc = f"ADX={adx:.1f} (추세 후반, 신규 진입 위험)"
            passed = False
        else:
            pts = 0.0
            desc = f"ADX={adx:.1f} (추세 미약, 진입 부적합)"
            passed = False

        score += pts
        checks.append(CheckItem(
            name="ADX 게이트", passed=passed, value=adx,
            threshold=ADX_ENTRY_IDEAL, score=round(pts, 1),
            description=desc,
        ))

        # (B) MACD 방향 + 제로라인 위치
        macd_val = float(latest["macd"])
        macd_diff = float(latest["macd_diff"])  # 히스토그램
        macd_above_zero = macd_val > MACD_ZERO_CROSS
        hist_positive = macd_diff > 0
        hist_expanding = (
            prev is not None and macd_diff > float(prev["macd_diff"])
        )

        if macd_above_zero and hist_positive:
            pts = SCORE_MACD_DIRECTION
            if hist_expanding:
                desc = f"MACD={macd_val:.2f} > 0, 히스토그램 확대 중 (가속)"
            else:
                desc = f"MACD={macd_val:.2f} > 0, 히스토그램 양 (모멘텀 유지)"
            passed = True
        elif macd_above_zero:
            pts = SCORE_MACD_DIRECTION * 0.5
            desc = f"MACD={macd_val:.2f} > 0이나 히스토그램 음전환 (둔화)"
            passed = True
        elif hist_positive and hist_expanding:
            pts = SCORE_MACD_DIRECTION * 0.4
            desc = f"MACD={macd_val:.2f} < 0이나 히스토그램 양전환 (반등 시도)"
            passed = False
        else:
            pts = 0.0
            desc = f"MACD={macd_val:.2f} 약세"
            passed = False

        score += pts
        checks.append(CheckItem(
            name="MACD 방향", passed=passed, value=macd_val,
            score=round(pts, 1), description=desc,
        ))

        # (C) BB 돌파/스퀴즈
        bb_pct = float(latest["bb_pct"])
        bb_width = float(latest["bb_width"])

        if bb_pct >= BB_BREAKOUT_UPPER:
            pts = SCORE_BB_BREAKOUT
            desc = f"BB %B={bb_pct:.2f} — 상단 돌파! BW={bb_width:.1f}%"
            passed = True
        elif bb_width <= BB_SQUEEZE_THRESHOLD:
            pts = SCORE_BB_BREAKOUT * 0.6
            desc = f"BW={bb_width:.1f}% — 스퀴즈(에너지 압축), 돌파 대기"
            passed = True
        elif bb_pct >= 0.7:
            pts = SCORE_BB_BREAKOUT * 0.4
            desc = f"BB %B={bb_pct:.2f} — 상단 근접 (강세 위치)"
            passed = True
        else:
            pts = 0.0
            desc = f"BB %B={bb_pct:.2f}, BW={bb_width:.1f}% — 중립/하단"
            passed = False

        score += pts
        checks.append(CheckItem(
            name="BB 상태", passed=passed, value=bb_pct,
            score=round(pts, 1), description=desc,
        ))

        # (D) RSI 강세 구간
        rsi = float(latest["rsi"])
        if RSI_BULLISH_MIN <= rsi < RSI_OVERHEAT:
            pts = SCORE_RSI_ZONE
            desc = f"RSI={rsi:.1f} — 강세 구간 (50~80)"
            passed = True
        elif rsi >= RSI_OVERHEAT:
            pts = SCORE_RSI_ZONE * 0.3
            desc = f"RSI={rsi:.1f} — 과열 (단기 조정 가능성)"
            passed = False
        else:
            pts = 0.0
            desc = f"RSI={rsi:.1f} — 약세 구간 (<50)"
            passed = False

        score += pts
        checks.append(CheckItem(
            name="RSI 구간", passed=passed, value=rsi,
            score=round(pts, 1), description=desc,
        ))

        # (E) 거래량 확인
        if "Volume" in latest.index and "vol_avg_50" in latest.index:
            vol = float(latest["Volume"])
            vol_avg = float(latest["vol_avg_50"])
            if vol_avg > 0:
                vol_ratio = vol / vol_avg
                passed = vol_ratio >= VOLUME_BREAKOUT_RATIO
                pts = SCORE_VOLUME_CONFIRM if passed else (SCORE_VOLUME_CONFIRM * 0.3 if vol_ratio >= 1.0 else 0.0)
                score += pts
                checks.append(CheckItem(
                    name="거래량 확인", passed=passed, value=vol_ratio,
                    threshold=VOLUME_BREAKOUT_RATIO, score=round(pts, 1),
                    description=f"금일/50일평균 = {vol_ratio:.1f}배 ({'돌파 확인' if passed else '보통'})",
                ))
            else:
                checks.append(CheckItem(name="거래량 확인", passed=False, description="평균 거래량 0"))
        else:
            checks.append(CheckItem(name="거래량 확인", passed=False, description="거래량 데이터 없음"))

        score = min(score, SCORE_TECHNICAL_MAX)
        status = self._classify_status(checks)

        return StageResult(
            stage_num=4, stage_name="기술적 진입 조건",
            status=status, score=round(score, 1),
            max_score=SCORE_TECHNICAL_MAX, checks=checks,
            description=self._stage4_summary(checks, adx, macd_val),
        )

    # ── 5단계: 리스크 관리 ───────────────────────────────

    def _stage5_risk_management(self) -> StageResult:
        """ATR 기반 손절/익절/R:R 산출"""
        checks: list[CheckItem] = []
        score = 0.0
        latest = self._calc.latest()
        price = float(latest["Close"])

        # ATR 근사 (BB 기반)
        bb_upper = float(latest["bb_upper"])
        bb_lower = float(latest["bb_lower"])
        atr_proxy = (bb_upper - bb_lower) / 4.0

        # 손절가
        sl = max(bb_lower, price - atr_proxy * GROWTH_ATR_SL_MULTIPLIER)
        sl = round(sl, 2)
        sl_pct = (price - sl) / price

        checks.append(CheckItem(
            name="손절가", passed=True, value=sl,
            description=f"손절가 {sl:,.2f} (현재가 대비 -{sl_pct:.1%}, ATR×{GROWTH_ATR_SL_MULTIPLIER})",
        ))

        # 익절가
        tp = min(bb_upper * 1.5, price + atr_proxy * GROWTH_ATR_TP_MULTIPLIER)
        tp = round(tp, 2)
        tp_pct = (tp - price) / price

        checks.append(CheckItem(
            name="목표가", passed=True, value=tp,
            description=f"목표가 {tp:,.2f} (현재가 대비 +{tp_pct:.1%}, ATR×{GROWTH_ATR_TP_MULTIPLIER})",
        ))

        # R:R 비율
        risk = abs(price - sl)
        reward = abs(tp - price)
        rr = round(reward / risk, 2) if risk > 1e-6 else 0.0

        if rr >= GROWTH_IDEAL_RR_RATIO:
            pts = SCORE_RR_ADEQUATE + SCORE_RR_IDEAL
            desc = f"R:R = 1:{rr} (이상적 ≥1:{GROWTH_IDEAL_RR_RATIO:.0f})"
            passed = True
        elif rr >= GROWTH_MIN_RR_RATIO:
            pts = SCORE_RR_ADEQUATE
            desc = f"R:R = 1:{rr} (적정 ≥1:{GROWTH_MIN_RR_RATIO:.0f})"
            passed = True
        else:
            pts = 0.0
            desc = f"R:R = 1:{rr} (부족 <1:{GROWTH_MIN_RR_RATIO:.0f}, 진입 비권장)"
            passed = False

        score += pts
        checks.append(CheckItem(
            name="위험보상비율", passed=passed, value=rr,
            threshold=GROWTH_MIN_RR_RATIO, score=round(pts, 1),
            description=desc,
        ))

        score = min(score, SCORE_RISK_MAX)

        return StageResult(
            stage_num=5, stage_name="리스크 관리",
            status=StageStatus.PASS if passed else StageStatus.FAIL,
            score=round(score, 1), max_score=SCORE_RISK_MAX,
            checks=checks,
            description=f"손절 {sl:,.0f} → 목표 {tp:,.0f} (R:R 1:{rr})",
        )

    # ── 6단계: 보유 관리 (추세 건강도) ───────────────────

    def _stage6_hold_health(self) -> StageResult:
        """현재 추세의 건강 상태 모니터링"""
        checks: list[CheckItem] = []
        score = 0.0
        latest = self._calc.latest()

        # ADX 건강도
        adx = float(latest["adx"])
        passed = adx >= HOLD_ADX_HEALTHY
        pts = SCORE_ADX_HEALTH if passed else 0.0
        score += pts
        checks.append(CheckItem(
            name="ADX 건강도", passed=passed, value=adx,
            threshold=HOLD_ADX_HEALTHY, score=round(pts, 1),
            description=f"ADX={adx:.1f} {'≥' if passed else '<'} {HOLD_ADX_HEALTHY} ({'추세 유지' if passed else '추세 약화'})",
        ))

        # MACD 건강도
        macd_val = float(latest["macd"])
        passed = macd_val > HOLD_MACD_POSITIVE
        pts = SCORE_MACD_HEALTH if passed else 0.0
        score += pts
        checks.append(CheckItem(
            name="MACD 건강도", passed=passed, value=macd_val,
            score=round(pts, 1),
            description=f"MACD={macd_val:.2f} {'> 0 (양)' if passed else '≤ 0 (음)'}",
        ))

        # DI 건강도
        di_pos = float(latest["adx_pos"])
        di_neg = float(latest["adx_neg"])
        di_gap = di_pos - di_neg
        passed = di_gap >= HOLD_DI_MARGIN
        pts = SCORE_DI_HEALTH if passed else 0.0
        score += pts
        checks.append(CheckItem(
            name="DI 방향", passed=passed, value=di_gap,
            threshold=HOLD_DI_MARGIN, score=round(pts, 1),
            description=f"+DI={di_pos:.1f} -DI={di_neg:.1f} 격차={di_gap:+.1f} ({'상승우위' if passed else '중립/역전'})",
        ))

        # RSI 건강도
        rsi = float(latest["rsi"])
        passed = rsi > HOLD_RSI_BULLISH
        pts = SCORE_RSI_HEALTH if passed else 0.0
        score += pts
        checks.append(CheckItem(
            name="RSI 강세", passed=passed, value=rsi,
            threshold=HOLD_RSI_BULLISH, score=round(pts, 1),
            description=f"RSI={rsi:.1f} {'> 50 (강세)' if passed else '≤ 50 (약세)'}",
        ))

        score = min(score, SCORE_HOLD_MAX)
        status = self._classify_status(checks)
        warnings_count = sum(1 for c in checks if not c.passed)

        if warnings_count == 0:
            desc = "추세 건강: 모든 지표 정상"
        elif warnings_count <= 1:
            desc = f"추세 건강: 경고 {warnings_count}개 — 주시"
        elif warnings_count <= 2:
            desc = f"추세 약화: 경고 {warnings_count}개 — 분할 청산 고려"
        else:
            desc = f"추세 위험: 경고 {warnings_count}개 — 청산 권장"

        return StageResult(
            stage_num=6, stage_name="보유 관리 (추세 건강도)",
            status=status, score=round(score, 1),
            max_score=SCORE_HOLD_MAX, checks=checks,
            description=desc,
        )

    # ── 유틸리티 ─────────────────────────────────────────

    def _get_52w_high(self) -> Optional[float]:
        if self._df is not None and len(self._df) >= 252:
            return float(self._df["High"].tail(252).max())
        elif self._df is not None:
            return float(self._df["High"].max())
        return self._info.get("fiftyTwoWeekHigh")

    def _get_52w_low(self) -> Optional[float]:
        if self._df is not None and len(self._df) >= 252:
            return float(self._df["Low"].tail(252).min())
        elif self._df is not None:
            return float(self._df["Low"].min())
        return self._info.get("fiftyTwoWeekLow")

    def _get_sma(self, window: int) -> Optional[float]:
        col = f"sma_{window}"
        if self._df is not None and col in self._df.columns:
            val = self._df[col].iloc[-1]
            if pd.notna(val):
                return round(float(val), 2)
        return None

    def _extract_fundamentals(self) -> FundamentalData:
        info = self._info
        return FundamentalData(
            eps_growth=info.get("earningsQuarterlyGrowth") or info.get("earningsGrowth"),
            revenue_growth=info.get("revenueGrowth"),
            profit_margin=info.get("operatingMargins") or info.get("profitMargins"),
            sector=info.get("sector", ""),
            industry=info.get("industry", ""),
            market_cap=info.get("marketCap"),
            forward_pe=info.get("forwardPE"),
            peg_ratio=info.get("pegRatio"),
        )

    @staticmethod
    def _classify_status(checks: list[CheckItem]) -> StageStatus:
        if not checks:
            return StageStatus.FAIL
        passed = sum(1 for c in checks if c.passed)
        total = len(checks)
        if passed == total:
            return StageStatus.PASS
        if passed >= total * 0.5:
            return StageStatus.PARTIAL
        return StageStatus.FAIL

    @staticmethod
    def _score_to_grade(score: float) -> GrowthGrade:
        if score >= GRADE_STRONG_BUY:
            return GrowthGrade.STRONG_BUY
        if score >= GRADE_BUY:
            return GrowthGrade.BUY
        if score >= GRADE_CONDITIONAL:
            return GrowthGrade.CONDITIONAL
        if score >= GRADE_WATCH:
            return GrowthGrade.WATCH
        return GrowthGrade.UNFIT

    @staticmethod
    def _determine_action(grade: GrowthGrade, stages: list[StageResult]) -> str:
        s3 = next((s for s in stages if s.stage_num == 3), None)
        s4 = next((s for s in stages if s.stage_num == 4), None)
        s5 = next((s for s in stages if s.stage_num == 5), None)

        if grade == GrowthGrade.STRONG_BUY:
            return "적극 매수 진입. 피라미딩 전략 준비."
        if grade == GrowthGrade.BUY:
            return "매수 진입 고려. 펀더멘털 수동 확인 후 진입."
        if grade == GrowthGrade.CONDITIONAL:
            if s3 and s3.status == StageStatus.PASS:
                return "기반 패턴 형성 중. 기술적 돌파 대기."
            return "조건 부족. 관심 종목 등록 후 재확인."
        if grade == GrowthGrade.WATCH:
            return "관심 종목으로 등록. 스테이지 전환 모니터링."
        return "현재 부적합. 다른 종목 탐색 권장."

    @staticmethod
    def _collect_warnings(stages: list[StageResult]) -> list[str]:
        warnings = []
        for s in stages:
            for c in s.checks:
                if not c.passed and c.description and "데이터 없음" not in c.description:
                    warnings.append(f"[S{s.stage_num}] {c.name}: {c.description}")
        return warnings

    @staticmethod
    def _stage1_summary(checks: list[CheckItem]) -> str:
        passed = sum(1 for c in checks if c.passed)
        total = len(checks)
        if passed == total:
            return "이익 가속 확인: 모든 펀더멘털 조건 충족"
        if passed > 0:
            return f"이익 부분 충족: {passed}/{total} 항목 통과 (수동 확인 권장)"
        return "이익 데이터 부족: 수동으로 EPS/매출 성장률 확인 필요"

    @staticmethod
    def _stage4_summary(checks: list[CheckItem], adx: float, macd: float) -> str:
        passed = sum(1 for c in checks if c.passed)
        if passed >= 4:
            return f"기술적 조건 우수: ADX={adx:.0f} MACD={macd:+.1f} — 진입 적합"
        if passed >= 2:
            return f"기술적 조건 부분 충족: {passed}/5 — 추가 확인 후 진입"
        return "기술적 조건 미충족: 관망"

    def _determine_stage(
        self,
        checks: list[CheckItem],
        price: float,
        sma150: Optional[float],
        sma200: Optional[float],
    ) -> str:
        """제시 스타인 4단계 중 현재 위치 판별"""
        if sma200 is None:
            return "스테이지 판별 불가 (데이터 부족)"

        ma_aligned = checks[0].passed if checks else False  # 정배열
        sma200_up = checks[1].passed if len(checks) > 1 else False

        if ma_aligned and sma200_up:
            return "★ 2단계 (상승 추세) — 매수 적합 구간"
        if price > sma200 and not sma200_up:
            return "2~3단계 전환 구간 — 200일선 상승 둔화 주시"
        if price < sma200 and sma150 and price > sma150:
            return "1~2단계 전환 구간 — 200일선 돌파 대기"
        if price < sma200:
            return "4단계 (하락 추세) 또는 1단계 (기반 형성) — 매수 금지"
        return "약한 2단계 — 이평선 정배열 미완성"
