"""
ta_trader/value/analyzer.py
ValueInvestingAnalyzer — 가치 투자 5단계 분석 엔진

프로세스:
  [1단계] 밸류에이션 필터    → PER, PBR, PSR, EV/EBITDA
  [2단계] 수익성 분석        → ROE, 영업이익률, FCF Yield, Cash Conversion
  [3단계] 재무 건전성        → 부채비율, 유동비율, 이자보상배율, 이익 안정성
  [4단계] 안전마진 산출      → 비교 밸류에이션 기반 내재가치, 배당, PEG
  [5단계] 기술적 진입 타이밍 → 이평선 지지, RSI 과매도, 52주 위치, R:R

사용 예:
    analyzer = ValueInvestingAnalyzer("AAPL")
    result = analyzer.analyze()
    print(f"{result.grade.stars} {result.total_score:.1f}점")
"""

from __future__ import annotations

from typing import Optional

import numpy as np
import pandas as pd

from ta_trader.base.base_analyzer import BaseAnalyzer
from ta_trader.data.fetcher import DataFetcher
from ta_trader.indicators.calculator import IndicatorCalculator
from ta_trader.indicators.rsi import RSIAnalyzer
from ta_trader.utils.logger import get_logger

from ta_trader.value.constants import (
    # 1단계 밸류에이션
    PER_LOW_THRESHOLD, PER_HIGH_THRESHOLD,
    PBR_LOW_THRESHOLD, PBR_DEEP_VALUE,
    PSR_LOW_THRESHOLD, PSR_HIGH_THRESHOLD,
    EV_EBITDA_LOW, EV_EBITDA_HIGH, EV_EBITDA_MANDA,
    SCORE_PER, SCORE_PBR, SCORE_PSR, SCORE_EV_EBITDA, SCORE_VALUATION_MAX,
    # 2단계 수익성
    ROE_EXCELLENT, ROE_GOOD, ROE_MIN,
    OPERATING_MARGIN_EXCELLENT, OPERATING_MARGIN_GOOD, OPERATING_MARGIN_MIN,
    FCF_YIELD_ATTRACTIVE, FCF_YIELD_MIN,
    CASH_CONVERSION_GOOD, CASH_CONVERSION_MIN,
    SCORE_ROE, SCORE_OPERATING_MARGIN, SCORE_FCF_YIELD,
    SCORE_CASH_CONVERSION, SCORE_PROFITABILITY_MAX,
    # 3단계 재무 건전성
    DEBT_EQUITY_SAFE, DEBT_EQUITY_OK, DEBT_EQUITY_DANGER,
    CURRENT_RATIO_GOOD, CURRENT_RATIO_MIN,
    INTEREST_COVERAGE_SAFE, INTEREST_COVERAGE_MIN,
    SCORE_DEBT_EQUITY, SCORE_CURRENT_RATIO,
    SCORE_INTEREST_COVERAGE, SCORE_EARNINGS_STABILITY, SCORE_FINANCIAL_MAX,
    # 4단계 안전마진
    MARGIN_OF_SAFETY_STRONG, MARGIN_OF_SAFETY_GOOD, MARGIN_OF_SAFETY_MIN,
    DIVIDEND_YIELD_ATTRACTIVE, DIVIDEND_YIELD_HIGH,
    PAYOUT_RATIO_SAFE_MAX, PAYOUT_RATIO_DANGER,
    PEG_UNDERVALUED, PEG_FAIR,
    SCORE_INTRINSIC_VALUE, SCORE_DIVIDEND, SCORE_PEG, SCORE_BUYBACK,
    SCORE_MARGIN_MAX,
    # 5단계 기술적 진입
    SMA_200_WINDOW, SMA_50_WINDOW, SMA_20_WINDOW,
    RSI_OVERSOLD, RSI_NEUTRAL_LOW, RSI_OVERBOUGHT,
    NEAR_52W_LOW_PCT,
    VALUE_ATR_SL_MULTIPLIER, VALUE_ATR_TP_MULTIPLIER,
    VALUE_DEFAULT_SL_PCT, VALUE_DEFAULT_TP_PCT, VALUE_MIN_RR_RATIO,
    SCORE_MA_SUPPORT, SCORE_RSI_ENTRY, SCORE_52W_ENTRY,
    SCORE_RISK_REWARD, SCORE_ENTRY_MAX,
    # 종합
    GRADE_STRONG_BUY, GRADE_BUY, GRADE_CONDITIONAL, GRADE_WATCH,
    VALUE_DEFAULT_PERIOD, VALUE_MIN_DATA_ROWS,
)
from ta_trader.models.base_models import CheckItem, StageResult, StageStatus
from ta_trader.models.value_models import (
    ValueFundamentals, ValueGrade, ValueScreenResult,
)

logger = get_logger(__name__)


class ValueInvestingAnalyzer(BaseAnalyzer[ValueScreenResult]):
    """
    가치 투자 5단계 분석 엔진.

    GrowthMomentumAnalyzer가 '향후 급등 잠재력'을 분석한다면,
    ValueInvestingAnalyzer는 '내재가치 대비 저평가 수준'을 종합 평가합니다.

    사용 예:
        analyzer = ValueInvestingAnalyzer("AAPL")
        result = analyzer.analyze()

        analyzer = ValueInvestingAnalyzer("005930.KS", period="3y")
        result = analyzer.analyze()
    """

    @property
    def name(self) -> str:
        return "데이터 분석 에이전트"

    @property
    def role(self) -> str:
        return "시장 데이터 수집 및 기술적 지표 연산"

    # ── 공개 API ──────────────────────────────────────────

    def analyze(self) -> ValueScreenResult:
        """5단계 가치 투자 분석 실행 → ValueScreenResult 반환"""
        logger.info("가치 투자 분석 시작", ticker=self.ticker)

        self._fetch_data()

        if len(self._df) < VALUE_MIN_DATA_ROWS:
            logger.warning(
                "데이터 부족",
                ticker=self.ticker,
                rows=len(self._df),
                required=VALUE_MIN_DATA_ROWS,
            )

        stages = [
            self._stage1_valuation(),
            self._stage2_profitability(),
            self._stage3_financial_health(),
            self._stage4_margin_of_safety(),
            self._stage5_technical_entry(),
        ]

        total_score = sum(s.score for s in stages)
        grade = self._score_to_grade(total_score)
        fundamentals = self._extract_fundamentals()

        # 내재가치·안전마진 계산
        intrinsic = self._estimate_intrinsic_value()
        mos = None
        if intrinsic and intrinsic > 0:
            current = self._current_price()
            mos = (intrinsic - current) / intrinsic if current < intrinsic else 0.0

        # 52주 정보
        high_52 = self._get_52w_high()
        low_52 = self._get_52w_low()
        sma200 = self._get_sma(SMA_200_WINDOW)

        # 손절/익절 (5단계에서 계산된 값)
        s5 = stages[4]
        sl_check = next((c for c in s5.checks if c.name == "손절가"), None)
        tp_check = next((c for c in s5.checks if c.name == "목표가"), None)
        rr_check = next((c for c in s5.checks if c.name == "R:R 비율"), None)

        result = ValueScreenResult(
            ticker=self.ticker,
            name=self._name,
            date=self._df.index[-1].strftime("%Y-%m-%d") if self._df is not None else "",
            current_price=self._current_price(),
            stages=stages,
            total_score=total_score,
            grade=grade,
            fundamentals=fundamentals,
            stop_loss=sl_check.value if sl_check else None,
            take_profit=tp_check.value if tp_check else None,
            risk_reward=rr_check.value if rr_check else None,
            high_52w=high_52,
            low_52w=low_52,
            sma_200=sma200,
            intrinsic_value=intrinsic,
            margin_of_safety=mos,
            warnings=self._collect_warnings(stages),
            action=self._determine_action(grade, stages),
        )
        logger.info(
            "가치 투자 분석 완료",
            ticker=self.ticker,
            grade=grade.value,
            score=total_score,
        )
        return result

    def analyze_with_llm(
        self,
        provider:    str | None = None,
        api_key:     str | None = None,
        model:       str | None = None,
        recent_days: int = 10,
        stream:      bool = False,
    ) -> ValueScreenResult:
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

    def _current_price(self) -> float:
        """최신 종가"""
        if self._df is not None and not self._df.empty:
            return float(self._df["Close"].iloc[-1])
        return 0.0

    # ── 1단계: 밸류에이션 필터 ────────────────────────────

    def _stage1_valuation(self) -> StageResult:
        """PER, PBR, PSR, EV/EBITDA 기반 밸류에이션 평가"""
        checks: list[CheckItem] = []

        # PER
        trailing_pe = self._info.get("trailingPE")
        forward_pe = self._info.get("forwardPE")
        pe = forward_pe if forward_pe else trailing_pe
        pe_score = 0.0
        pe_desc = "데이터 없음"
        pe_passed = False

        if pe is not None and pe > 0:
            if pe <= PER_LOW_THRESHOLD:
                pe_score = SCORE_PER
                pe_desc = f"PER {pe:.1f} ≤ {PER_LOW_THRESHOLD} → 저평가"
                pe_passed = True
            elif pe <= PER_HIGH_THRESHOLD:
                ratio = 1.0 - (pe - PER_LOW_THRESHOLD) / (PER_HIGH_THRESHOLD - PER_LOW_THRESHOLD)
                pe_score = SCORE_PER * max(ratio, 0.3)
                pe_desc = f"PER {pe:.1f} 적정 범위"
                pe_passed = True
            else:
                pe_score = SCORE_PER * 0.1
                pe_desc = f"PER {pe:.1f} > {PER_HIGH_THRESHOLD} → 고평가"
        elif pe is not None and pe < 0:
            pe_desc = f"PER {pe:.1f} → 적자 기업 (PSR 참조)"

        checks.append(CheckItem(
            name="PER", passed=pe_passed,
            value=pe, threshold=PER_LOW_THRESHOLD,
            score=pe_score, description=pe_desc,
        ))

        # PBR
        pbr = self._info.get("priceToBook")
        pbr_score = 0.0
        pbr_desc = "데이터 없음"
        pbr_passed = False

        if pbr is not None and pbr > 0:
            if pbr <= PBR_DEEP_VALUE:
                pbr_score = SCORE_PBR
                pbr_desc = f"PBR {pbr:.2f} ≤ {PBR_DEEP_VALUE} → 심각한 저평가"
                pbr_passed = True
            elif pbr <= PBR_LOW_THRESHOLD:
                pbr_score = SCORE_PBR * 0.8
                pbr_desc = f"PBR {pbr:.2f} ≤ {PBR_LOW_THRESHOLD} → 자산가치 이하"
                pbr_passed = True
            elif pbr <= 2.0:
                pbr_score = SCORE_PBR * 0.4
                pbr_desc = f"PBR {pbr:.2f} 적정 수준"
                pbr_passed = True
            else:
                pbr_score = SCORE_PBR * 0.1
                pbr_desc = f"PBR {pbr:.2f} → 프리미엄 반영"

        checks.append(CheckItem(
            name="PBR", passed=pbr_passed,
            value=pbr, threshold=PBR_LOW_THRESHOLD,
            score=pbr_score, description=pbr_desc,
        ))

        # PSR
        psr = self._info.get("priceToSalesTrailing12Months")
        psr_score = 0.0
        psr_desc = "데이터 없음"
        psr_passed = False

        if psr is not None and psr > 0:
            if psr <= PSR_LOW_THRESHOLD:
                psr_score = SCORE_PSR
                psr_desc = f"PSR {psr:.2f} ≤ {PSR_LOW_THRESHOLD} → 저평가"
                psr_passed = True
            elif psr <= PSR_HIGH_THRESHOLD:
                psr_score = SCORE_PSR * 0.5
                psr_desc = f"PSR {psr:.2f} 적정 범위"
                psr_passed = True
            else:
                psr_score = SCORE_PSR * 0.1
                psr_desc = f"PSR {psr:.2f} > {PSR_HIGH_THRESHOLD} → 고평가"

        checks.append(CheckItem(
            name="PSR", passed=psr_passed,
            value=psr, threshold=PSR_LOW_THRESHOLD,
            score=psr_score, description=psr_desc,
        ))

        # EV/EBITDA
        ev_ebitda = self._info.get("enterpriseToEbitda")
        ev_score = 0.0
        ev_desc = "데이터 없음"
        ev_passed = False

        if ev_ebitda is not None and ev_ebitda > 0:
            if ev_ebitda <= EV_EBITDA_MANDA:
                ev_score = SCORE_EV_EBITDA
                ev_desc = f"EV/EBITDA {ev_ebitda:.1f} ≤ {EV_EBITDA_MANDA} → M&A 매력 수준"
                ev_passed = True
            elif ev_ebitda <= EV_EBITDA_LOW:
                ev_score = SCORE_EV_EBITDA * 0.8
                ev_desc = f"EV/EBITDA {ev_ebitda:.1f} → 저평가"
                ev_passed = True
            elif ev_ebitda <= EV_EBITDA_HIGH:
                ratio = 1.0 - (ev_ebitda - EV_EBITDA_LOW) / (EV_EBITDA_HIGH - EV_EBITDA_LOW)
                ev_score = SCORE_EV_EBITDA * max(ratio * 0.6, 0.2)
                ev_desc = f"EV/EBITDA {ev_ebitda:.1f} 적정 범위"
                ev_passed = True
            else:
                ev_score = SCORE_EV_EBITDA * 0.1
                ev_desc = f"EV/EBITDA {ev_ebitda:.1f} > {EV_EBITDA_HIGH} → 고평가"

        checks.append(CheckItem(
            name="EV/EBITDA", passed=ev_passed,
            value=ev_ebitda, threshold=EV_EBITDA_LOW,
            score=ev_score, description=ev_desc,
        ))

        total = sum(c.score for c in checks)
        status = self._classify_status(checks)

        return StageResult(
            stage_num=1,
            stage_name="밸류에이션 필터",
            status=status,
            score=min(total, SCORE_VALUATION_MAX),
            max_score=SCORE_VALUATION_MAX,
            checks=checks,
            description=self._stage1_summary(checks),
        )

    # ── 2단계: 수익성 분석 ────────────────────────────────

    def _stage2_profitability(self) -> StageResult:
        """ROE, 영업이익률, FCF Yield, Cash Conversion 평가"""
        checks: list[CheckItem] = []
        info = self._info

        # ROE
        roe = info.get("returnOnEquity")
        roe_score = 0.0
        roe_desc = "데이터 없음"
        roe_passed = False

        if roe is not None:
            if roe >= ROE_EXCELLENT:
                roe_score = SCORE_ROE
                roe_desc = f"ROE {roe:.1%} ≥ {ROE_EXCELLENT:.0%} → 우수"
                roe_passed = True
            elif roe >= ROE_GOOD:
                roe_score = SCORE_ROE * 0.7
                roe_desc = f"ROE {roe:.1%} ≥ {ROE_GOOD:.0%} → 양호"
                roe_passed = True
            elif roe >= ROE_MIN:
                roe_score = SCORE_ROE * 0.3
                roe_desc = f"ROE {roe:.1%} → 보통"
                roe_passed = True
            else:
                roe_desc = f"ROE {roe:.1%} < {ROE_MIN:.0%} → 저조"

        checks.append(CheckItem(
            name="ROE", passed=roe_passed,
            value=roe, threshold=ROE_GOOD,
            score=roe_score, description=roe_desc,
        ))

        # 영업이익률
        op_margin = info.get("operatingMargins")
        opm_score = 0.0
        opm_desc = "데이터 없음"
        opm_passed = False

        if op_margin is not None:
            if op_margin >= OPERATING_MARGIN_EXCELLENT:
                opm_score = SCORE_OPERATING_MARGIN
                opm_desc = f"영업이익률 {op_margin:.1%} → 우수"
                opm_passed = True
            elif op_margin >= OPERATING_MARGIN_GOOD:
                opm_score = SCORE_OPERATING_MARGIN * 0.7
                opm_desc = f"영업이익률 {op_margin:.1%} → 양호"
                opm_passed = True
            elif op_margin >= OPERATING_MARGIN_MIN:
                opm_score = SCORE_OPERATING_MARGIN * 0.3
                opm_desc = f"영업이익률 {op_margin:.1%} → 보통"
                opm_passed = True
            else:
                opm_desc = f"영업이익률 {op_margin:.1%} → 저조"

        checks.append(CheckItem(
            name="영업이익률", passed=opm_passed,
            value=op_margin, threshold=OPERATING_MARGIN_GOOD,
            score=opm_score, description=opm_desc,
        ))

        # FCF Yield
        fcf = info.get("freeCashflow")
        mcap = info.get("marketCap")
        fcf_yield = None
        fcfy_score = 0.0
        fcfy_desc = "데이터 없음"
        fcfy_passed = False

        if fcf is not None and mcap and mcap > 0:
            fcf_yield = fcf / mcap
            if fcf_yield >= FCF_YIELD_ATTRACTIVE:
                fcfy_score = SCORE_FCF_YIELD
                fcfy_desc = f"FCF Yield {fcf_yield:.1%} ≥ {FCF_YIELD_ATTRACTIVE:.0%} → 매력적"
                fcfy_passed = True
            elif fcf_yield >= FCF_YIELD_MIN:
                fcfy_score = SCORE_FCF_YIELD * 0.6
                fcfy_desc = f"FCF Yield {fcf_yield:.1%} → 적정"
                fcfy_passed = True
            elif fcf_yield > 0:
                fcfy_score = SCORE_FCF_YIELD * 0.2
                fcfy_desc = f"FCF Yield {fcf_yield:.1%} → 낮음"
            else:
                fcfy_desc = f"FCF Yield {fcf_yield:.1%} → 음수 (현금 소진)"

        checks.append(CheckItem(
            name="FCF Yield", passed=fcfy_passed,
            value=fcf_yield, threshold=FCF_YIELD_MIN,
            score=fcfy_score, description=fcfy_desc,
        ))

        # Cash Conversion Ratio
        net_income = info.get("netIncomeToCommon")
        ccr = None
        ccr_score = 0.0
        ccr_desc = "데이터 없음"
        ccr_passed = False

        if fcf is not None and net_income and net_income > 0:
            ccr = fcf / net_income
            if ccr >= CASH_CONVERSION_GOOD:
                ccr_score = SCORE_CASH_CONVERSION
                ccr_desc = f"Cash Conversion {ccr:.2f} ≥ {CASH_CONVERSION_GOOD} → 이익 질 우수"
                ccr_passed = True
            elif ccr >= CASH_CONVERSION_MIN:
                ccr_score = SCORE_CASH_CONVERSION * 0.5
                ccr_desc = f"Cash Conversion {ccr:.2f} → 양호"
                ccr_passed = True
            else:
                ccr_desc = f"Cash Conversion {ccr:.2f} → 이익 질 의문"

        checks.append(CheckItem(
            name="Cash Conversion", passed=ccr_passed,
            value=ccr, threshold=CASH_CONVERSION_MIN,
            score=ccr_score, description=ccr_desc,
        ))

        total = sum(c.score for c in checks)
        status = self._classify_status(checks)

        return StageResult(
            stage_num=2,
            stage_name="수익성 분석",
            status=status,
            score=min(total, SCORE_PROFITABILITY_MAX),
            max_score=SCORE_PROFITABILITY_MAX,
            checks=checks,
            description=self._stage2_summary(checks),
        )

    # ── 3단계: 재무 건전성 ────────────────────────────────

    def _stage3_financial_health(self) -> StageResult:
        """부채비율, 유동비율, 이자보상배율, 이익 안정성 평가"""
        checks: list[CheckItem] = []
        info = self._info

        # 부채비율 (D/E Ratio)
        de = info.get("debtToEquity")
        # yfinance debtToEquity는 % 단위일 수 있음 (ex: 150 = 150%)
        if de is not None and de > 10:
            de = de / 100.0  # 비율로 정규화
        de_score = 0.0
        de_desc = "데이터 없음"
        de_passed = False

        if de is not None:
            if de <= DEBT_EQUITY_SAFE:
                de_score = SCORE_DEBT_EQUITY
                de_desc = f"D/E {de:.1%} ≤ {DEBT_EQUITY_SAFE:.0%} → 안전"
                de_passed = True
            elif de <= DEBT_EQUITY_OK:
                de_score = SCORE_DEBT_EQUITY * 0.6
                de_desc = f"D/E {de:.1%} → 적정"
                de_passed = True
            elif de <= DEBT_EQUITY_DANGER:
                de_score = SCORE_DEBT_EQUITY * 0.2
                de_desc = f"D/E {de:.1%} → 높음"
            else:
                de_desc = f"D/E {de:.1%} > {DEBT_EQUITY_DANGER:.0%} → 위험"

        checks.append(CheckItem(
            name="부채비율(D/E)", passed=de_passed,
            value=de, threshold=DEBT_EQUITY_OK,
            score=de_score, description=de_desc,
        ))

        # 유동비율
        cr = info.get("currentRatio")
        cr_score = 0.0
        cr_desc = "데이터 없음"
        cr_passed = False

        if cr is not None:
            if cr >= CURRENT_RATIO_GOOD:
                cr_score = SCORE_CURRENT_RATIO
                cr_desc = f"유동비율 {cr:.2f} ≥ {CURRENT_RATIO_GOOD} → 양호"
                cr_passed = True
            elif cr >= CURRENT_RATIO_MIN:
                cr_score = SCORE_CURRENT_RATIO * 0.5
                cr_desc = f"유동비율 {cr:.2f} → 적정"
                cr_passed = True
            else:
                cr_desc = f"유동비율 {cr:.2f} < {CURRENT_RATIO_MIN} → 주의"

        checks.append(CheckItem(
            name="유동비율", passed=cr_passed,
            value=cr, threshold=CURRENT_RATIO_MIN,
            score=cr_score, description=cr_desc,
        ))

        # 이자보상배율 (EBIT / Interest Expense)
        # yfinance에서 직접 제공하지 않으므로 EBITDA / totalDebt로 근사
        ebitda = info.get("ebitda")
        total_debt = info.get("totalDebt")
        icr = None
        icr_score = 0.0
        icr_desc = "데이터 없음"
        icr_passed = False

        if ebitda and total_debt and total_debt > 0:
            # 간이 이자보상배율: EBITDA / (총부채 * 추정금리 5%)
            est_interest = total_debt * 0.05
            if est_interest > 0:
                icr = ebitda / est_interest
                if icr >= INTEREST_COVERAGE_SAFE:
                    icr_score = SCORE_INTEREST_COVERAGE
                    icr_desc = f"이자보상배율(추정) {icr:.1f}x ≥ {INTEREST_COVERAGE_SAFE}x → 안전"
                    icr_passed = True
                elif icr >= INTEREST_COVERAGE_MIN:
                    icr_score = SCORE_INTEREST_COVERAGE * 0.5
                    icr_desc = f"이자보상배율(추정) {icr:.1f}x → 적정"
                    icr_passed = True
                else:
                    icr_desc = f"이자보상배율(추정) {icr:.1f}x → 주의"
        elif ebitda and (total_debt is None or total_debt == 0):
            icr_score = SCORE_INTEREST_COVERAGE
            icr_desc = "무차입 또는 부채 매우 적음 → 안전"
            icr_passed = True

        checks.append(CheckItem(
            name="이자보상배율", passed=icr_passed,
            value=icr, threshold=INTEREST_COVERAGE_MIN,
            score=icr_score, description=icr_desc,
        ))

        # 이익 안정성 (최근 데이터 기반 매출 성장 지속 여부)
        rev_growth = info.get("revenueGrowth")
        earn_growth = info.get("earningsGrowth")
        stab_score = 0.0
        stab_desc = "데이터 없음"
        stab_passed = False

        if rev_growth is not None and earn_growth is not None:
            if rev_growth > 0 and earn_growth > 0:
                stab_score = SCORE_EARNINGS_STABILITY
                stab_desc = (
                    f"매출 성장 {rev_growth:.1%}, 이익 성장 {earn_growth:.1%} → 안정적 성장"
                )
                stab_passed = True
            elif rev_growth > 0:
                stab_score = SCORE_EARNINGS_STABILITY * 0.5
                stab_desc = f"매출 성장 중이나 이익 감소 ({earn_growth:.1%})"
                stab_passed = True
            else:
                stab_desc = f"매출 역성장 ({rev_growth:.1%}) → 주의"
        elif rev_growth is not None:
            if rev_growth > 0:
                stab_score = SCORE_EARNINGS_STABILITY * 0.4
                stab_desc = f"매출 성장 {rev_growth:.1%} (이익 데이터 없음)"
                stab_passed = True

        checks.append(CheckItem(
            name="이익 안정성", passed=stab_passed,
            value=rev_growth, threshold=0.0,
            score=stab_score, description=stab_desc,
        ))

        total = sum(c.score for c in checks)
        status = self._classify_status(checks)

        return StageResult(
            stage_num=3,
            stage_name="재무 건전성",
            status=status,
            score=min(total, SCORE_FINANCIAL_MAX),
            max_score=SCORE_FINANCIAL_MAX,
            checks=checks,
            description=self._stage3_summary(checks),
        )

    # ── 4단계: 안전마진 산출 ──────────────────────────────

    def _stage4_margin_of_safety(self) -> StageResult:
        """비교 밸류에이션 기반 내재가치, 배당, PEG 평가"""
        checks: list[CheckItem] = []
        info = self._info

        # 내재가치 대비 할인율 (안전마진)
        intrinsic = self._estimate_intrinsic_value()
        current = self._current_price()
        mos = None
        mos_score = 0.0
        mos_desc = "내재가치 추정 불가"
        mos_passed = False

        if intrinsic and intrinsic > 0 and current > 0:
            mos = (intrinsic - current) / intrinsic
            if mos >= MARGIN_OF_SAFETY_STRONG:
                mos_score = SCORE_INTRINSIC_VALUE
                mos_desc = f"안전마진 {mos:.0%} ≥ {MARGIN_OF_SAFETY_STRONG:.0%} → 강력 매수 영역"
                mos_passed = True
            elif mos >= MARGIN_OF_SAFETY_GOOD:
                mos_score = SCORE_INTRINSIC_VALUE * 0.7
                mos_desc = f"안전마진 {mos:.0%} → 매수 고려"
                mos_passed = True
            elif mos >= MARGIN_OF_SAFETY_MIN:
                mos_score = SCORE_INTRINSIC_VALUE * 0.4
                mos_desc = f"안전마진 {mos:.0%} → 최소 수준"
                mos_passed = True
            elif mos >= 0:
                mos_score = SCORE_INTRINSIC_VALUE * 0.1
                mos_desc = f"안전마진 {mos:.0%} → 부족 (적정가 부근)"
            else:
                mos_desc = f"안전마진 {mos:.0%} → 고평가 (내재가치 이상)"

        checks.append(CheckItem(
            name="안전마진", passed=mos_passed,
            value=mos, threshold=MARGIN_OF_SAFETY_GOOD,
            score=mos_score, description=mos_desc,
        ))

        # 배당 매력도
        div_yield = info.get("dividendYield")
        payout = info.get("payoutRatio")
        div_score = 0.0
        div_desc = "배당 없음 또는 데이터 없음"
        div_passed = False

        if div_yield is not None and div_yield > 0:
            payout_safe = payout is None or payout <= PAYOUT_RATIO_SAFE_MAX
            if div_yield >= DIVIDEND_YIELD_HIGH and payout_safe:
                div_score = SCORE_DIVIDEND
                payout_str = f", 배당성향 {payout:.0%}" if payout else ""
                div_desc = f"배당수익률 {div_yield:.1%}{payout_str} → 고배당 + 지속 가능"
                div_passed = True
            elif div_yield >= DIVIDEND_YIELD_ATTRACTIVE and payout_safe:
                div_score = SCORE_DIVIDEND * 0.7
                div_desc = f"배당수익률 {div_yield:.1%} → 매력적"
                div_passed = True
            elif div_yield > 0:
                div_score = SCORE_DIVIDEND * 0.3
                div_desc = f"배당수익률 {div_yield:.1%}"
                div_passed = True

            if payout and payout > PAYOUT_RATIO_DANGER:
                div_score *= 0.5
                div_desc += f" ⚠ 배당성향 {payout:.0%} 과다"

        checks.append(CheckItem(
            name="배당 매력도", passed=div_passed,
            value=div_yield, threshold=DIVIDEND_YIELD_ATTRACTIVE,
            score=div_score, description=div_desc,
        ))

        # PEG Ratio
        peg = info.get("pegRatio")
        peg_score = 0.0
        peg_desc = "데이터 없음"
        peg_passed = False

        if peg is not None and peg > 0:
            if peg <= PEG_UNDERVALUED:
                peg_score = SCORE_PEG
                peg_desc = f"PEG {peg:.2f} ≤ {PEG_UNDERVALUED} → 성장 대비 저평가"
                peg_passed = True
            elif peg <= PEG_FAIR:
                peg_score = SCORE_PEG * 0.5
                peg_desc = f"PEG {peg:.2f} → 적정"
                peg_passed = True
            else:
                peg_desc = f"PEG {peg:.2f} > {PEG_FAIR} → 성장 대비 고평가"

        checks.append(CheckItem(
            name="PEG Ratio", passed=peg_passed,
            value=peg, threshold=PEG_UNDERVALUED,
            score=peg_score, description=peg_desc,
        ))

        # 주주환원 (자사주 매입 여부 — shares outstanding 감소로 추정)
        shares = info.get("sharesOutstanding")
        prev_shares = info.get("floatShares")
        buyback_score = 0.0
        buyback_desc = "데이터 없음"
        buyback_passed = False

        # 단순히 배당과 FCF 존재 여부로 주주환원 점수 부여
        fcf = info.get("freeCashflow")
        if fcf and fcf > 0 and div_yield and div_yield > 0:
            buyback_score = SCORE_BUYBACK
            buyback_desc = "양(+) FCF + 배당 지급 → 주주환원 활발"
            buyback_passed = True
        elif fcf and fcf > 0:
            buyback_score = SCORE_BUYBACK * 0.5
            buyback_desc = "양(+) FCF 확보 (배당 미지급)"
            buyback_passed = True

        checks.append(CheckItem(
            name="주주환원", passed=buyback_passed,
            value=None, threshold=None,
            score=buyback_score, description=buyback_desc,
        ))

        total = sum(c.score for c in checks)
        status = self._classify_status(checks)

        return StageResult(
            stage_num=4,
            stage_name="안전마진 산출",
            status=status,
            score=min(total, SCORE_MARGIN_MAX),
            max_score=SCORE_MARGIN_MAX,
            checks=checks,
            description=self._stage4_summary(checks, mos),
        )

    # ── 5단계: 기술적 진입 타이밍 ─────────────────────────

    def _stage5_technical_entry(self) -> StageResult:
        """이평선 지지, RSI, 52주 위치, R:R 비율"""
        checks: list[CheckItem] = []
        df = self._df
        current = self._current_price()

        # 이동평균선 지지
        sma200 = self._get_sma(SMA_200_WINDOW)
        sma50 = self._get_sma(SMA_50_WINDOW)
        ma_score = 0.0
        ma_desc = "데이터 없음"
        ma_passed = False

        if sma200 is not None and current > 0:
            above_200 = current >= sma200
            near_200 = abs(current - sma200) / sma200 <= 0.05  # 5% 이내
            if near_200 and above_200:
                ma_score = SCORE_MA_SUPPORT
                ma_desc = f"200일선({sma200:,.0f}) 부근 지지 → 최적 진입"
                ma_passed = True
            elif above_200:
                ma_score = SCORE_MA_SUPPORT * 0.7
                ma_desc = f"200일선({sma200:,.0f}) 위 → 상승 추세 중"
                ma_passed = True
            elif not above_200 and sma50 and current >= sma50:
                ma_score = SCORE_MA_SUPPORT * 0.4
                ma_desc = f"200일선 하회, 50일선({sma50:,.0f}) 지지"
                ma_passed = True
            else:
                ma_desc = f"200일선({sma200:,.0f}) 하회 → 하락 추세 주의"

        checks.append(CheckItem(
            name="이평선 지지", passed=ma_passed,
            value=sma200, threshold=None,
            score=ma_score, description=ma_desc,
        ))

        # RSI 과매도 여부
        rsi_val = None
        rsi_score = 0.0
        rsi_desc = "데이터 없음"
        rsi_passed = False

        if self._calc is not None:
            try:
                rsi_analyzer = RSIAnalyzer(self._calc)
                rsi_result = rsi_analyzer.analyze()
                rsi_val = rsi_result.raw_value
            except Exception:
                rsi_val = None

        if rsi_val is not None:
            if rsi_val <= RSI_OVERSOLD:
                rsi_score = SCORE_RSI_ENTRY
                rsi_desc = f"RSI {rsi_val:.1f} ≤ {RSI_OVERSOLD} → 과매도 (매수 기회)"
                rsi_passed = True
            elif rsi_val <= RSI_NEUTRAL_LOW:
                rsi_score = SCORE_RSI_ENTRY * 0.7
                rsi_desc = f"RSI {rsi_val:.1f} → 저평가 영역"
                rsi_passed = True
            elif rsi_val <= RSI_OVERBOUGHT:
                rsi_score = SCORE_RSI_ENTRY * 0.3
                rsi_desc = f"RSI {rsi_val:.1f} → 중립 구간"
                rsi_passed = True
            else:
                rsi_desc = f"RSI {rsi_val:.1f} > {RSI_OVERBOUGHT} → 과매수 (진입 주의)"

        checks.append(CheckItem(
            name="RSI 진입", passed=rsi_passed,
            value=rsi_val, threshold=RSI_NEUTRAL_LOW,
            score=rsi_score, description=rsi_desc,
        ))

        # 52주 위치
        low_52 = self._get_52w_low()
        high_52 = self._get_52w_high()
        pos_score = 0.0
        pos_desc = "데이터 없음"
        pos_passed = False

        if low_52 and high_52 and current > 0 and high_52 > low_52:
            pct_from_low = (current - low_52) / low_52
            pct_range = (current - low_52) / (high_52 - low_52)

            if pct_from_low <= NEAR_52W_LOW_PCT:
                pos_score = SCORE_52W_ENTRY
                pos_desc = f"52주 저가 대비 +{pct_from_low:.0%} → 저점 매수 영역"
                pos_passed = True
            elif pct_range <= 0.3:
                pos_score = SCORE_52W_ENTRY * 0.6
                pos_desc = f"52주 범위 하단 30% 위치"
                pos_passed = True
            elif pct_range <= 0.6:
                pos_score = SCORE_52W_ENTRY * 0.3
                pos_desc = f"52주 범위 중단 위치"
                pos_passed = True
            else:
                pos_desc = f"52주 범위 상단 위치 (고점 대비 {1-pct_range:.0%} 하락)"

        checks.append(CheckItem(
            name="52주 위치", passed=pos_passed,
            value=low_52, threshold=None,
            score=pos_score, description=pos_desc,
        ))

        # 손절/익절/R:R 계산
        sl_price, tp_price, rr_ratio = self._calc_risk_levels(current)
        rr_score = 0.0
        rr_desc = "계산 불가"
        rr_passed = False

        if rr_ratio and rr_ratio >= VALUE_MIN_RR_RATIO:
            rr_score = SCORE_RISK_REWARD
            rr_desc = f"R:R 1:{rr_ratio:.1f} → 적정"
            rr_passed = True
        elif rr_ratio:
            rr_score = SCORE_RISK_REWARD * 0.3
            rr_desc = f"R:R 1:{rr_ratio:.1f} → 최소 기준 미달"

        checks.append(CheckItem(
            name="R:R 비율", passed=rr_passed,
            value=rr_ratio, threshold=VALUE_MIN_RR_RATIO,
            score=rr_score, description=rr_desc,
        ))

        # 손절/목표가 (보고서용)
        checks.append(CheckItem(
            name="손절가", passed=True,
            value=sl_price, description=f"손절가: {sl_price:,.0f}" if sl_price else "N/A",
        ))
        checks.append(CheckItem(
            name="목표가", passed=True,
            value=tp_price, description=f"목표가: {tp_price:,.0f}" if tp_price else "N/A",
        ))

        # 점수 합산 (손절/목표가 항목은 정보성이므로 score 제외)
        total = ma_score + rsi_score + pos_score + rr_score
        scored_checks = [c for c in checks if c.name not in ("손절가", "목표가")]
        status = self._classify_status(scored_checks)

        return StageResult(
            stage_num=5,
            stage_name="기술적 진입 타이밍",
            status=status,
            score=min(total, SCORE_ENTRY_MAX),
            max_score=SCORE_ENTRY_MAX,
            checks=checks,
            description=self._stage5_summary(checks),
        )

    # ── 내재가치 추정 ─────────────────────────────────────

    def _estimate_intrinsic_value(self) -> Optional[float]:
        """
        비교 밸류에이션 기반 내재가치 추정
        Graham Number + Earnings Power Value 방식의 앙상블
        """
        info = self._info
        eps = info.get("trailingEps")
        bps = info.get("bookValue")

        estimates: list[float] = []

        # Graham Number: sqrt(22.5 × EPS × BPS)
        if eps and eps > 0 and bps and bps > 0:
            graham = (22.5 * eps * bps) ** 0.5
            estimates.append(graham)

        # Forward PE 기반 적정가: Forward EPS × 업종 평균 PER (15배 가정)
        forward_eps = info.get("forwardEps")
        if forward_eps and forward_eps > 0:
            fair_pe_value = forward_eps * 15.0
            estimates.append(fair_pe_value)

        # BPS 기반 적정가: BPS × 적정 PBR (ROE에 연동)
        roe = info.get("returnOnEquity")
        if bps and bps > 0 and roe:
            # 이론적 PBR ≈ ROE / 할인율(10%)
            fair_pbr = max(roe / 0.10, 0.5)  # 최소 0.5배
            fair_pbr = min(fair_pbr, 5.0)     # 최대 5배 상한
            bps_value = bps * fair_pbr
            estimates.append(bps_value)

        if estimates:
            return float(np.median(estimates))
        return None

    # ── 리스크 수준 계산 ──────────────────────────────────

    def _calc_risk_levels(
        self, current: float,
    ) -> tuple[Optional[float], Optional[float], Optional[float]]:
        """ATR 기반 손절/익절/R:R 계산"""
        if self._df is None or len(self._df) < 14 or current <= 0:
            # 기본값
            sl = current * (1 - VALUE_DEFAULT_SL_PCT)
            tp = current * (1 + VALUE_DEFAULT_TP_PCT)
            rr = VALUE_DEFAULT_TP_PCT / VALUE_DEFAULT_SL_PCT if VALUE_DEFAULT_SL_PCT > 0 else None
            return sl, tp, rr

        try:
            df = self._df.copy()
            high = df["High"]
            low = df["Low"]
            close = df["Close"]
            tr = pd.concat([
                high - low,
                (high - close.shift(1)).abs(),
                (low - close.shift(1)).abs(),
            ], axis=1).max(axis=1)
            atr = tr.rolling(14).mean().iloc[-1]

            if np.isnan(atr) or atr <= 0:
                atr = current * 0.02

            sl = current - atr * VALUE_ATR_SL_MULTIPLIER
            tp = current + atr * VALUE_ATR_TP_MULTIPLIER

            # 안전마진 기반 목표가 조정
            intrinsic = self._estimate_intrinsic_value()
            if intrinsic and intrinsic > current:
                tp = max(tp, intrinsic)

            risk = current - sl
            reward = tp - current
            rr = reward / risk if risk > 0 else None

            return round(sl, 2), round(tp, 2), round(rr, 2) if rr else None
        except Exception:
            sl = current * (1 - VALUE_DEFAULT_SL_PCT)
            tp = current * (1 + VALUE_DEFAULT_TP_PCT)
            rr = VALUE_DEFAULT_TP_PCT / VALUE_DEFAULT_SL_PCT
            return sl, tp, rr

    # ── 유틸리티 ──────────────────────────────────────────

    def _get_52w_high(self) -> Optional[float]:
        if self._df is not None and len(self._df) >= 200:
            return float(self._df["High"].tail(252).max())
        return self._info.get("fiftyTwoWeekHigh")

    def _get_52w_low(self) -> Optional[float]:
        if self._df is not None and len(self._df) >= 200:
            return float(self._df["Low"].tail(252).min())
        return self._info.get("fiftyTwoWeekLow")

    def _get_sma(self, window: int) -> Optional[float]:
        if self._df is not None and len(self._df) >= window:
            return float(self._df["Close"].rolling(window).mean().iloc[-1])
        return None

    def _extract_fundamentals(self) -> ValueFundamentals:
        """yfinance info에서 ValueFundamentals 추출"""
        info = self._info
        de = info.get("debtToEquity")
        if de is not None and de > 10:
            de = de / 100.0

        return ValueFundamentals(
            trailing_pe=info.get("trailingPE"),
            forward_pe=info.get("forwardPE"),
            pbr=info.get("priceToBook"),
            psr=info.get("priceToSalesTrailing12Months"),
            ev_ebitda=info.get("enterpriseToEbitda"),
            peg_ratio=info.get("pegRatio"),
            roe=info.get("returnOnEquity"),
            operating_margin=info.get("operatingMargins"),
            profit_margin=info.get("profitMargins"),
            revenue_growth=info.get("revenueGrowth"),
            earnings_growth=info.get("earningsGrowth"),
            debt_to_equity=de,
            current_ratio=info.get("currentRatio"),
            total_cash=info.get("totalCash"),
            total_debt=info.get("totalDebt"),
            free_cashflow=info.get("freeCashflow"),
            operating_cashflow=info.get("operatingCashflow"),
            net_income=info.get("netIncomeToCommon"),
            dividend_yield=info.get("dividendYield"),
            payout_ratio=info.get("payoutRatio"),
            sector=info.get("sector", ""),
            industry=info.get("industry", ""),
            market_cap=info.get("marketCap"),
            enterprise_value=info.get("enterpriseValue"),
            ebitda=info.get("ebitda"),
        )

    # ── 분류/등급 헬퍼 ────────────────────────────────────

    @staticmethod
    def _classify_status(checks: list[CheckItem]) -> StageStatus:
        if not checks:
            return StageStatus.NO_DATA
        passed = sum(1 for c in checks if c.passed)
        total = len(checks)
        if passed == total:
            return StageStatus.PASS
        if passed >= total * 0.5:
            return StageStatus.PARTIAL
        if all(c.value is None for c in checks):
            return StageStatus.NO_DATA
        return StageStatus.FAIL

    @staticmethod
    def _score_to_grade(score: float) -> ValueGrade:
        if score >= GRADE_STRONG_BUY:
            return ValueGrade.STRONG_BUY
        if score >= GRADE_BUY:
            return ValueGrade.BUY
        if score >= GRADE_CONDITIONAL:
            return ValueGrade.CONDITIONAL
        if score >= GRADE_WATCH:
            return ValueGrade.WATCH
        return ValueGrade.UNFIT

    @staticmethod
    def _determine_action(grade: ValueGrade, stages: list[StageResult]) -> str:
        if grade == ValueGrade.STRONG_BUY:
            return "적극 매수: 밸류에이션·재무·안전마진 모두 우수. 분할 매수 추천"
        if grade == ValueGrade.BUY:
            return "매수 고려: 가치 투자 기준 충족. 추가 리서치 후 진입"
        if grade == ValueGrade.CONDITIONAL:
            weak = [s for s in stages if s.status == StageStatus.FAIL]
            weak_names = ", ".join(s.stage_name for s in weak[:2])
            return f"조건부 매수: {weak_names} 개선 시 재평가"
        if grade == ValueGrade.WATCH:
            return "관심 관망: 밸류에이션 추가 하락 시 재검토"
        return "부적합: 현재 가치 투자 기준 미충족"

    @staticmethod
    def _collect_warnings(stages: list[StageResult]) -> list[str]:
        warnings = []
        for s in stages:
            for c in s.checks:
                if not c.passed and c.value is not None and "위험" in c.description:
                    warnings.append(f"[{s.stage_name}] {c.description}")
        return warnings

    # ── 단계별 요약 ───────────────────────────────────────

    @staticmethod
    def _stage1_summary(checks: list[CheckItem]) -> str:
        descs = [c.description for c in checks if c.description != "데이터 없음"]
        return " | ".join(descs) if descs else "밸류에이션 데이터 부족"

    @staticmethod
    def _stage2_summary(checks: list[CheckItem]) -> str:
        descs = [c.description for c in checks if c.description != "데이터 없음"]
        return " | ".join(descs) if descs else "수익성 데이터 부족"

    @staticmethod
    def _stage3_summary(checks: list[CheckItem]) -> str:
        descs = [c.description for c in checks if c.description != "데이터 없음"]
        return " | ".join(descs) if descs else "재무 데이터 부족"

    @staticmethod
    def _stage4_summary(checks: list[CheckItem], mos: Optional[float] = None) -> str:
        if mos is not None and mos > 0:
            return f"안전마진 {mos:.0%} 확보"
        elif mos is not None:
            return f"안전마진 부족 ({mos:.0%})"
        return "안전마진 산출 불가"

    @staticmethod
    def _stage5_summary(checks: list[CheckItem]) -> str:
        scored = [c for c in checks if c.name not in ("손절가", "목표가")]
        descs = [c.description for c in scored if c.description != "데이터 없음"]
        return " | ".join(descs) if descs else "기술적 데이터 부족"
