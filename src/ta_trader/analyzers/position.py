"""
ta_trader/analyzers/position.py
포지션 트레이딩 7단계 프로세스 분석기

7단계 프로세스:
  1. 시장 환경 판단  (200MA, ADX, 정배열, ATR%)
  2. 섹터/테마 선정  (섹터 RS, 자금 흐름)
  3. 종목 선정       (RS, Stage2, ADX, 52주 신고가)
  4. 매수 타이밍     (MA Pullback, Breakout, MACD, BB Squeeze)
  5. 리스크 관리     (ATR 손절/익절, 분할매수, 포지션 사이징)
  6. 보유 관리       (트레일링 스톱, 파라볼릭 SAR, 피라미딩)
  7. 매도/청산       (MA 이탈, 다이버전스, ADX 하락)
"""

from __future__ import annotations

from typing import Optional

import numpy as np
import pandas as pd

from ta_trader.base.analyzer import BaseAnalyzer
from ta_trader.data.fetcher import DataFetcher
from ta_trader.indicators.swing_calculator import SwingIndicatorCalculator
from ta_trader.indicators.atr import calc_atr_stop_loss, calc_atr_take_profit, calc_trailing_stop
from ta_trader.indicators.moving_avg import is_bullish_market, detect_ema_crossover
from ta_trader.indicators.fibonacci import (
    compute_fibonacci_levels, find_swing_points,
)

from ta_trader.constants.position import *
from ta_trader.models import OrderSide
from ta_trader.models.position import (
    PositionAnalysisResult,
    MarketEnvResult, PositionMarketEnv,
    SectorResult, SectorStrength,
    ScreeningResult, PositionScreenGrade,
    EntryResult, EntrySignalDetail,
    RiskManagementResult,
    HoldingManagementResult,
    ExitResult,
)
from ta_trader.utils.logger import get_logger

from ta_trader.llm.position_prompt_builder import PositionPromptBuilder

logger = get_logger(__name__)


class PositionTradingAnalyzer(BaseAnalyzer[PositionAnalysisResult]):
    """
    포지션 트레이딩 7단계 프로세스 분석기.

    사용 예:
        analyzer = PositionTradingAnalyzer("005930.KS")
        result = analyzer.analyze()

        analyzer = PositionTradingAnalyzer("AAPL", capital=50_000_000)
        result = analyzer.analyze()
    """

    def __init__(
        self,
        ticker: str,
        name: str = None,
        period: str = "1y",
        interval: str = "1d",
        capital: float = RISK_DEFAULT_CAPITAL,
        risk_pct: float = RISK_PER_TRADE_PCT,
        last_trading_day: str = None,
    ) -> None:
        super().__init__(ticker, period=period, interval=interval, last_trading_day=last_trading_day)
        self.capital = capital
        self.risk_pct = risk_pct

        self._name: str = ticker
        self._df: Optional[pd.DataFrame] = None
        self._calc: Optional[SwingIndicatorCalculator] = None
        self._info: dict = {}

    @property
    def name(self) -> str:
        return "포지션 트레이딩 분석 시스템"

    @property
    def role(self) -> str:
        return "포지션 매매 시장 환경 판단 및 진입/청산 신호 분석"

    @property
    def calculator(self) -> SwingIndicatorCalculator | None:
        return self._calc

    # ── 메인 분석 ─────────────────────────────────────────

    def analyze(self, df: pd.DataFrame | None = None) -> PositionAnalysisResult:
        """7단계 포지션 트레이딩 분석 실행"""

        # 0. 데이터 수집 & 지표 계산
        self._fetch_data()
        df = self._calc.dataframe
        latest = self._calc.latest()
        prev = self._calc.previous()
        price = float(latest["Close"])
        date = str(df.index[-1].date())

        # 1단계: 시장 환경 판단
        market_env = self._market_environment()

        # 2단계: 섹터/테마 선정
        sector = self._step2_sector_analysis()

        # 3단계: 종목 선정
        screening = self._screening()

        # 4단계: 매수 타이밍
        entry = self._entry_signal()

        # 5단계: 리스크 관리
        risk = self._step5_risk_management(entry)

        # 6단계: 보유 관리
        holding = self._step6_holding_management(risk)

        # 7단계: 매도/청산
        exit_strategy = self._exit_strategy(risk)

        # 종합 점수 & 신호
        overall_score = self._compute_overall_score(
            market_env, sector, screening, entry, risk, holding, exit_strategy,
        )
        overall_signal = self._compute_overall_signal(
            overall_score, market_env, screening, entry, exit_strategy,
        )

        summary = self._build_summary(
            market_env, sector, screening, entry, risk, holding, exit_strategy,
            overall_signal, overall_score,
        )

        result = PositionAnalysisResult(
            ticker=self.ticker,
            name=self._name,
            date=date,
            current_price=price,
            market_env=market_env,
            sector=sector,
            screening=screening,
            entry=entry,
            risk=risk,
            holding=holding,
            exit_strategy=exit_strategy,
            overall_signal=overall_signal,
            overall_score=round(overall_score, 1),
            summary=summary,
        )

        logger.info(
            "포지션 분석 완료",
            ticker=self.ticker,
            name=self._name,
            signal=overall_signal.value,
            score=overall_score,
        )

        return result

    def analyze_with_llm(
        self,
        df:          pd.DataFrame | None = None,
        provider:    str | None = None,
        api_key:     str | None = None,
        model:       str | None = None,
        recent_days: int = 10,
        stream:      bool = False,
    ) -> PositionAnalysisResult:
        """
        기술적 분석 실행 후 LLM 해석을 추가하여 반환합니다.
        analyze() 를 내부적으로 먼저 호출하므로 별도 호출 불필요.

        Args:
            provider:    'anthropic' | 'google' | None (None이면 환경변수/자동감지)
            api_key:     API 키 (None이면 환경변수 사용)
            model:       LLM 모델명 (None이면 환경변수 또는 기본값 사용)
            recent_days: 가격 추이 요약에 사용할 최근 일수
            stream:      True 이면 스트리밍으로 LLM 응답을 출력하고 결과 반환

        Returns:
            llm_analysis 필드가 채워진 SwingAnalysisResult
        """
        from ta_trader.llm.factory import create_llm_analyzer

        # 기술적 분석이 아직 실행되지 않았으면 실행
        result = self.analyze(df)
        df = self._calc.dataframe

        llm = create_llm_analyzer(provider=provider, api_key=api_key, model=model)

        prompt_builder = PositionPromptBuilder()
        prompt = prompt_builder.build(result, df, recent_days)

        if stream:
            print(f"\n{'─'*60}")
            print(f"  🤖 LLM 분석 중 [{self.ticker}] ...")
            print(f"{'─'*60}\n")
            full_text = ""
            for chunk in llm.analyze_stream(result.ticker, prompt):
                print(chunk, end="", flush=True)
                full_text += chunk
            print()
            llm_result = llm._parse_response(full_text, llm._model)
        else:
            llm_result = llm.analyze(result.ticker, prompt)

        result.llm_analysis = llm_result

        return result

    # ── 데이터 수집 ───────────────────────────────────────

    #def _fetch_data(self) -> None:
    #    fetcher = DataFetcher(period=self.period, interval=self.interval)
    #    self._name, self._df = fetcher.fetch(self.ticker)
    #    self._calc = SwingIndicatorCalculator(self._df)
    #    self._name, self._info = fetcher.info(self.ticker)

    # ── 1단계: 시장 환경 판단 ─────────────────────────────

    def _market_environment(self) -> MarketEnvResult:
        df = self._calc.dataframe
        row = self._calc.latest()

        adx_val = float(row["adx"])
        adx_trend = adx_val >= MARKET_ADX_TREND_THRESHOLD
        above_200 = is_bullish_market(row)
        ma_score = int(row.get("ma_trend_score", 2))
        atr_pct = float(row.get("atr_pct", 2.0))

        # SMA50 vs SMA200 (골든크로스 상태)
        sma50 = float(row.get("sma50", 0.0)) if pd.notna(row.get("sma50")) else 0.0
        sma200 = float(row.get("sma200", 0.0)) if pd.notna(row.get("sma200")) else 0.0
        sma50_above_200 = sma50 > sma200 if sma50 > 0 and sma200 > 0 else False

        # 환경 분류 (포지션 트레이딩은 더 보수적)
        if adx_trend and above_200 and ma_score >= MARKET_MA_TREND_MIN and sma50_above_200:
            env = PositionMarketEnv.STRONG_BULLISH
        elif above_200 and ma_score >= 2:
            env = PositionMarketEnv.BULLISH
        elif not above_200 and adx_trend:
            env = PositionMarketEnv.BEARISH
        elif atr_pct >= MARKET_ATR_PCT_HIGH:
            env = PositionMarketEnv.HIGH_VOLATILITY
        else:
            env = PositionMarketEnv.SIDEWAYS

        # 점수 산출
        score = 0.0
        if above_200:
            score += 25.0
        if adx_trend:
            score += 20.0
        if sma50_above_200:
            score += 15.0
        score += ma_score * 7.5     # 0~30
        if atr_pct < MARKET_VOLATILITY_STABLE_MAX:
            score += 10.0

        detail_parts = [
            f"ADX={adx_val:.1f}({'추세' if adx_trend else '비추세'})",
            f"SMA200{'위' if above_200 else '아래'}",
            f"SMA50{'>'if sma50_above_200 else '<'}SMA200",
            f"정배열={ma_score}/4",
            f"ATR%={atr_pct:.2f}%",
        ]

        return MarketEnvResult(
            environment=env,
            adx_value=adx_val,
            adx_trend_exists=adx_trend,
            above_sma200=above_200,
            ma_trend_score=ma_score,
            atr_pct=atr_pct,
            sma50_above_sma200=sma50_above_200,
            score=min(STEP_MAX_SCORE, round(score, 1)),
            detail=" | ".join(detail_parts),
        )

    # ── 2단계: 섹터/테마 선정 ─────────────────────────────

    def _step2_sector_analysis(self) -> SectorResult:
        """
        섹터 RS를 종목 자체의 시장 대비 상대강도로 대리 산출.
        (개별 종목 분석 시 섹터 데이터가 없으므로 종목 RS를 섹터 대리로 사용)
        """
        df = self._calc.dataframe
        row = self._calc.latest()

        lookback = min(SECTOR_RS_LOOKBACK_DAYS, len(df) - 1)
        if lookback > 0:
            rs_return = (
                float(df["Close"].iloc[-1]) / float(df["Close"].iloc[-lookback]) - 1
            ) * 100
        else:
            rs_return = 0.0

        # 거래량 추세
        vol_trend = float(row.get("vol_trend", 1.0))

        # 섹터 강도 분류
        if rs_return >= 15.0 and vol_trend >= 1.2:
            strength = SectorStrength.LEADING
        elif rs_return >= SECTOR_RS_MIN_SCORE:
            strength = SectorStrength.STRONG
        elif rs_return >= 0.0:
            strength = SectorStrength.NEUTRAL
        elif rs_return >= -10.0:
            strength = SectorStrength.WEAK
        else:
            strength = SectorStrength.LAGGING

        # 점수 산출
        score = 0.0
        # RS 기여 (최대 60점)
        score += max(0.0, min(60.0, rs_return * 3.0))
        # 거래량 추세 기여 (최대 40점)
        if vol_trend >= 1.3:
            score += 40.0
        elif vol_trend >= 1.1:
            score += 25.0
        elif vol_trend >= 0.9:
            score += 15.0

        detail = f"RS(60일)={rs_return:+.1f}% | 거래량추세={vol_trend:.2f}"

        return SectorResult(
            strength=strength,
            rs_vs_market=round(rs_return, 2),
            volume_trend=round(vol_trend, 2),
            score=min(STEP_MAX_SCORE, round(score, 1)),
            detail=detail,
        )

    # ── 3단계: 종목 선정 ──────────────────────────────────

    def _screening(self) -> ScreeningResult:
        df = self._calc.dataframe
        row = self._calc.latest()

        # RS (상대강도)
        lookback = min(SCREEN_RS_LOOKBACK_DAYS, len(df) - 1)
        if lookback > 0:
            rs_score = (
                float(df["Close"].iloc[-1]) / float(df["Close"].iloc[-lookback]) - 1
            ) * 100
        else:
            rs_score = 0.0
        rs_positive = rs_score > SCREEN_RS_MIN_SCORE

        # ADX
        adx_val = float(row["adx"])
        adx_sufficient = adx_val >= SCREEN_MIN_ADX

        # DI 방향
        di_bullish = float(row["adx_pos"]) > float(row["adx_neg"])

        # 이평선 위치
        price = float(row["Close"])
        sma50 = float(row.get("sma50", 0.0)) if pd.notna(row.get("sma50")) else 0.0
        sma200 = float(row.get("sma200", 0.0)) if pd.notna(row.get("sma200")) else 0.0
        above_sma50 = price > sma50 if sma50 > 0 else True
        above_sma200 = price > sma200 if sma200 > 0 else True

        # 정배열 (Stage 2)
        ma_score = int(row.get("ma_trend_score", 2))
        ma_aligned = ma_score >= SCREEN_MA_TREND_MIN

        # 52주 신고가 근접
        high_52w = float(df["High"].rolling(252, min_periods=20).max().iloc[-1])
        near_52w_high = (price / high_52w) >= SCREEN_NEAR_52W_HIGH_PCT if high_52w > 0 else False

        # 거래량
        vol_ratio = float(row.get("vol_ratio", 1.0))
        volume_surge = vol_ratio >= SCREEN_VOL_SURGE_THRESHOLD

        # 종합 체크
        checks = [
            rs_positive, adx_sufficient, di_bullish,
            above_sma50, above_sma200, ma_aligned,
            near_52w_high, volume_surge,
        ]
        passed = sum(checks)

        if passed >= 7:
            grade = PositionScreenGrade.A_PLUS
        elif passed >= 6:
            grade = PositionScreenGrade.A
        elif passed >= 4:
            grade = PositionScreenGrade.B
        elif passed >= 3:
            grade = PositionScreenGrade.C
        else:
            grade = PositionScreenGrade.F

        score = passed / len(checks) * 100.0

        detail_parts = [
            f"RS={rs_score:+.1f}%({'✓' if rs_positive else '✗'})",
            f"ADX={adx_val:.1f}({'✓' if adx_sufficient else '✗'})",
            f"+DI>-DI({'✓' if di_bullish else '✗'})",
            f"SMA50{'위' if above_sma50 else '아래'}",
            f"SMA200{'위' if above_sma200 else '아래'}",
            f"정배열={ma_score}/4({'✓' if ma_aligned else '✗'})",
            f"52주고가{(price/high_52w*100):.0f}%({'✓' if near_52w_high else '✗'})" if high_52w > 0 else "52주고가 N/A",
            f"거래량={vol_ratio:.1f}x({'✓' if volume_surge else '✗'})",
        ]

        return ScreeningResult(
            grade=grade,
            rs_score=round(rs_score, 2),
            rs_positive=rs_positive,
            adx_sufficient=adx_sufficient,
            di_bullish=di_bullish,
            above_sma50=above_sma50,
            above_sma200=above_sma200,
            ma_aligned=ma_aligned,
            near_52w_high=near_52w_high,
            volume_surge=volume_surge,
            score=round(score, 1),
            checks_passed=passed,
            checks_total=len(checks),
            detail=" | ".join(detail_parts),
        )

    # ── 4단계: 매수 타이밍 ────────────────────────────────

    def _entry_signal(self) -> EntryResult:
        df = self._calc.dataframe
        row = self._calc.latest()
        prev = self._calc.previous()

        signals: list[EntrySignalDetail] = []
        price = float(row["Close"])

        # 4-1. MA20 Pullback 매수
        sma50 = float(row.get("sma50", 0.0)) if pd.notna(row.get("sma50")) else 0.0
        ema21 = float(row.get("ema21", 0.0)) if pd.notna(row.get("ema21")) else 0.0
        ma20_pullback = False
        if ema21 > 0:
            distance = abs(price - ema21) / ema21
            # 가격이 21EMA 근처(±2%)에서 반등 중이고, SMA50 위에 있는 경우
            if distance <= ENTRY_PULLBACK_TOLERANCE_PCT and price >= ema21 and (sma50 == 0 or price > sma50):
                ma20_pullback = True
        signals.append(EntrySignalDetail(
            name="MA20 풀백 매수",
            triggered=ma20_pullback,
            score=20.0 if ma20_pullback else 0.0,
            description=f"21EMA={ema21:,.0f} 거리={abs(price-ema21)/ema21*100:.1f}%" if ema21 > 0 else "N/A",
        ))

        # 4-2. MA50 Pullback 매수
        ma50_pullback = False
        if sma50 > 0:
            distance50 = abs(price - sma50) / sma50
            if distance50 <= ENTRY_PULLBACK_TOLERANCE_PCT and price >= sma50:
                ma50_pullback = True
        signals.append(EntrySignalDetail(
            name="MA50 풀백 매수",
            triggered=ma50_pullback,
            score=20.0 if ma50_pullback else 0.0,
            description=f"SMA50={sma50:,.0f} 거리={abs(price-sma50)/sma50*100:.1f}%" if sma50 > 0 else "N/A",
        ))

        # 4-3. Breakout 매수 (저항선 돌파 + 거래량)
        vol_ratio = float(row.get("vol_ratio", 1.0))
        # 최근 20일 고가 돌파를 Breakout으로 사용
        if len(df) >= 21:
            recent_high = float(df["High"].iloc[-21:-1].max())
        else:
            recent_high = price
        breakout = price > recent_high and vol_ratio >= ENTRY_BREAKOUT_VOL_SURGE
        breakout_score = 0.0
        if breakout:
            breakout_score = 20.0
            if vol_ratio >= ENTRY_BREAKOUT_STRONG_VOL:
                breakout_score = 25.0
        signals.append(EntrySignalDetail(
            name="Breakout 돌파",
            triggered=breakout,
            score=breakout_score,
            description=f"20일고가={recent_high:,.0f} 거래량={vol_ratio:.1f}x",
        ))

        # 4-4. MACD 시그널 상향 교차
        macd_diff = float(row["macd_diff"])
        prev_diff = float(prev["macd_diff"]) if prev is not None else 0.0
        macd_gc = prev_diff <= 0 < macd_diff
        macd_val = float(row["macd"])
        macd_score = 0.0
        if macd_gc:
            macd_score = 15.0
            if macd_val > 0:
                macd_score += ENTRY_MACD_ABOVE_ZERO_BONUS
        signals.append(EntrySignalDetail(
            name="MACD 골든크로스",
            triggered=macd_gc,
            score=macd_score,
            description=f"MACD={macd_val:.2f} Diff={macd_diff:.2f}{'(0선 위)' if macd_val > 0 else ''}",
        ))

        # 4-5. BB Squeeze → Breakout
        bb_pct = float(row["bb_pct"])
        bb_width = float(row["bb_width"])
        bb_squeeze = bb_width <= ENTRY_BB_BANDWIDTH_SQUEEZE and bb_pct >= ENTRY_BB_SQUEEZE_BREAKOUT
        signals.append(EntrySignalDetail(
            name="BB Squeeze 돌파",
            triggered=bb_squeeze,
            score=15.0 if bb_squeeze else 0.0,
            description=f"BB%B={bb_pct:.2f} BW={bb_width:.1f}%",
        ))

        # 4-6. EMA 골든크로스 (EMA9 > EMA21)
        ema_cross_str = detect_ema_crossover(row, prev)
        ema_gc = ema_cross_str == "골든크로스"
        signals.append(EntrySignalDetail(
            name="EMA 골든크로스",
            triggered=ema_gc,
            score=10.0 if ema_gc else 0.0,
            description=f"EMA9/21 {ema_cross_str}",
        ))

        # 종합 점수
        total_score = sum(s.score for s in signals)
        total_score = min(STEP_MAX_SCORE, total_score)

        if total_score >= ENTRY_SCORE_STRONG_BUY:
            signal = OrderSide.STRONG_ENTRY
        elif total_score >= ENTRY_SCORE_BUY:
            signal = OrderSide.ENTRY
        else:
            signal = OrderSide.HOLD

        return EntryResult(
            signal=signal,
            score=round(total_score, 1),
            signals=signals,
            ma20_pullback=ma20_pullback,
            ma50_pullback=ma50_pullback,
            breakout=breakout,
            macd_golden_cross=macd_gc,
            bb_squeeze_breakout=bb_squeeze,
            ema_golden_cross=ema_gc,
            detail=f"발동 {sum(1 for s in signals if s.triggered)}/{len(signals)} 신호",
        )

    # ── 5단계: 리스크 관리 ────────────────────────────────

    def _step5_risk_management(
        self,
        entry: EntryResult,
    ) -> RiskManagementResult:
        df = self._calc.dataframe
        row = self._calc.latest()

        price = float(row["Close"])
        atr = float(row["atr"])

        # ATR 기반 손절/익절 (포지션은 넓은 폭)
        stop_loss = calc_atr_stop_loss(price, atr, RISK_ATR_SL_MULTIPLIER)
        take_profit = calc_atr_take_profit(price, atr, RISK_ATR_TP_MULTIPLIER)

        # 피보나치 목표가
        fibo_161 = 0.0
        fibo_261 = 0.0
        try:
            sh, sl, direction = find_swing_points(df, lookback=60)
            fibo = compute_fibonacci_levels(sh, sl, direction)
            fibo_161 = fibo.target_161
            fibo_261 = fibo.target_261
        except Exception:
            pass

        # R배수
        risk_per_share = abs(price - stop_loss)
        reward = abs(take_profit - price)
        rr_ratio = round(reward / risk_per_share, 2) if risk_per_share > 0 else 0.0
        is_acceptable = rr_ratio >= RISK_MIN_RR_RATIO

        # 포지션 사이즈 (자본의 risk_pct를 넘지 않도록)
        max_risk = self.capital * self.risk_pct
        if risk_per_share > 0:
            pos_size = int(max_risk / risk_per_share)
        else:
            pos_size = 0

        pos_value = pos_size * price
        portfolio_pct = (pos_value / self.capital * 100) if self.capital > 0 else 0.0

        # 최대 비중 제한
        if portfolio_pct > RISK_MAX_PORTFOLIO_PCT * 100:
            pos_size = int(self.capital * RISK_MAX_PORTFOLIO_PCT / price)
            pos_value = pos_size * price
            portfolio_pct = pos_value / self.capital * 100

        # 분할 매수 계획 (1/3씩)
        split_1 = int(pos_size * RISK_SPLIT_BUY_RATIO_1)
        split_2 = int(pos_size * RISK_SPLIT_BUY_RATIO_2)
        split_3 = pos_size - split_1 - split_2  # 잔여

        # 점수
        score = 0.0
        if is_acceptable:
            score += 35.0
        if rr_ratio >= 3.0:
            score += 20.0
        elif rr_ratio >= 2.5:
            score += 10.0
        if portfolio_pct <= 15.0:
            score += 20.0
        if risk_per_share > 0:
            score += 15.0
        if pos_size > 0:
            score += 10.0
        score = min(STEP_MAX_SCORE, score)

        detail = (
            f"진입={price:,.0f} 손절={stop_loss:,.0f}(ATR×{RISK_ATR_SL_MULTIPLIER}) "
            f"익절={take_profit:,.0f}(ATR×{RISK_ATR_TP_MULTIPLIER}) RR=1:{rr_ratio} "
            f"수량={pos_size}주({split_1}+{split_2}+{split_3}) 비중={portfolio_pct:.1f}%"
        )

        return RiskManagementResult(
            entry_price=price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            risk_reward_ratio=rr_ratio,
            risk_per_share=round(risk_per_share, 2),
            position_size=pos_size,
            position_value=round(pos_value, 0),
            portfolio_pct=round(portfolio_pct, 1),
            capital=self.capital,
            atr=round(atr, 2),
            is_acceptable=is_acceptable,
            score=round(score, 1),
            detail=detail,
            split_buy_1=split_1,
            split_buy_2=split_2,
            split_buy_3=split_3,
            fibo_target_161=fibo_161,
            fibo_target_261=fibo_261,
        )

    # ── 6단계: 보유 관리 ──────────────────────────────────

    def _step6_holding_management(
        self,
        risk: RiskManagementResult,
    ) -> HoldingManagementResult:
        row = self._calc.latest()
        prev = self._calc.previous()

        price = float(row["Close"])
        atr = float(row["atr"])

        # ATR 기반 트레일링 스톱
        trailing_atr = calc_trailing_stop(price, atr, HOLD_TRAILING_ATR_MULTIPLIER)

        # 50일 MA 기반 트레일링 스톱
        sma50 = float(row.get("sma50", 0.0)) if pd.notna(row.get("sma50")) else 0.0
        trailing_ma50 = sma50 if sma50 > 0 else trailing_atr

        # 간이 파라볼릭 SAR (현재 ATR 기반 근사)
        # 실제 SAR 계산은 별도 지표가 필요하므로, 여기서는 ATR 기반 근사값 사용
        parabolic_sar = price - atr * 2.0

        # 피라미딩 가능 여부
        # (현재가가 진입가 대비 일정 이상 수익이면 추가 매수 가능)
        current_profit_pct = (price - risk.entry_price) / risk.entry_price * 100
        can_pyramid = current_profit_pct >= HOLD_PYRAMID_MIN_PROFIT_PCT * 100
        if can_pyramid:
            pyramid_condition = f"수익률 {current_profit_pct:.1f}% ≥ {HOLD_PYRAMID_MIN_PROFIT_PCT*100:.0f}% → 피라미딩 가능"
        else:
            pyramid_condition = f"수익률 {current_profit_pct:.1f}% < {HOLD_PYRAMID_MIN_PROFIT_PCT*100:.0f}% → 피라미딩 불가"

        # 점수 (보유 관리 건전성)
        score = 50.0  # 기본
        if price > trailing_atr:
            score += 15.0
        if price > trailing_ma50:
            score += 15.0
        if price > parabolic_sar:
            score += 10.0
        if can_pyramid:
            score += 10.0
        score = min(STEP_MAX_SCORE, score)

        detail_parts = [
            f"트레일링ATR={trailing_atr:,.0f}",
            f"트레일링MA50={trailing_ma50:,.0f}",
            f"SAR={parabolic_sar:,.0f}",
            f"수익률={current_profit_pct:+.1f}%",
            f"피라미딩={'가능' if can_pyramid else '불가'}",
        ]

        return HoldingManagementResult(
            trailing_stop_atr=trailing_atr,
            trailing_stop_ma50=trailing_ma50,
            parabolic_sar=parabolic_sar,
            can_pyramid=can_pyramid,
            pyramid_condition=pyramid_condition,
            current_profit_pct=round(current_profit_pct, 2),
            score=round(score, 1),
            detail=" | ".join(detail_parts),
        )

    # ── 7단계: 매도/청산 ──────────────────────────────────

    def _exit_strategy(
        self,
        risk: RiskManagementResult,
    ) -> ExitResult:
        df = self._calc.dataframe
        row = self._calc.latest()
        prev = self._calc.previous()

        price = float(row["Close"])
        atr = float(row["atr"])

        # 7-1. 50일 MA 이탈
        sma50 = float(row.get("sma50", 0.0)) if pd.notna(row.get("sma50")) else 0.0
        ma50_broken = price < sma50 if sma50 > 0 else False

        # 7-2. 200일 MA 이탈
        sma200 = float(row.get("sma200", 0.0)) if pd.notna(row.get("sma200")) else 0.0
        ma200_broken = price < sma200 if sma200 > 0 else False

        # 7-3. MACD 다이버전스 (가격 신고가 vs MACD 고점 하락)
        macd_divergence = False
        if len(df) >= 20:
            recent_prices = df["Close"].iloc[-20:]
            recent_macd = df["macd"].iloc[-20:]
            if pd.notna(recent_macd).all():
                # 가격이 최근 20일 고가 근처인데 MACD는 감소 추세
                price_near_high = price >= recent_prices.max() * 0.98
                macd_declining = float(recent_macd.iloc[-1]) < float(recent_macd.max()) * 0.7
                if price_near_high and macd_declining and float(recent_macd.max()) > 0:
                    macd_divergence = True

        # 7-4. RSI 다이버전스
        rsi_divergence = False
        rsi = float(row["rsi"])
        if len(df) >= 20:
            recent_rsi = df["rsi"].iloc[-20:]
            if pd.notna(recent_rsi).all():
                price_near_high = price >= df["Close"].iloc[-20:].max() * 0.98
                rsi_declining = rsi < float(recent_rsi.max()) * 0.85
                if price_near_high and rsi_declining:
                    rsi_divergence = True

        # 7-5. ADX 피크 대비 하락
        adx_val = float(row["adx"])
        adx_declining = False
        if len(df) >= 10:
            recent_adx = df["adx"].iloc[-10:]
            if pd.notna(recent_adx).all():
                adx_peak = float(recent_adx.max())
                if adx_peak - adx_val >= EXIT_ADX_DECLINE_FROM_PEAK:
                    adx_declining = True

        # 7-6. 거래량 고갈 (신고가 시 거래량 감소)
        vol_ratio = float(row.get("vol_ratio", 1.0))
        high_52w = float(df["High"].rolling(252, min_periods=20).max().iloc[-1])
        near_high = (price / high_52w) >= 0.98 if high_52w > 0 else False
        volume_dry_up = near_high and vol_ratio < EXIT_VOLUME_DRY_UP_RATIO

        # 7-7. RSI 과매수
        rsi_overbought = rsi >= EXIT_RSI_OVERBOUGHT

        # 트레일링 스톱 / 부분 익절가
        trailing = calc_trailing_stop(price, atr, HOLD_TRAILING_ATR_MULTIPLIER)
        partial_exit = round(risk.entry_price + atr * RISK_ATR_TP_MULTIPLIER * 0.5, 2)
        full_exit = risk.take_profit

        # 청산 점수 산출
        exit_score = 0.0
        if ma50_broken:
            exit_score += 25.0
        if ma200_broken:
            exit_score += 30.0
        if macd_divergence:
            exit_score += 15.0
        if rsi_divergence:
            exit_score += 10.0
        if adx_declining:
            exit_score += 10.0
        if volume_dry_up:
            exit_score += 10.0
        if rsi >= EXIT_RSI_EXTREME:
            exit_score += 15.0
        elif rsi_overbought:
            exit_score += 5.0

        # 신호 결정
        if exit_score >= 60:
            signal = OrderSide.STRONG_EXIT
        elif exit_score >= 40:
            signal = OrderSide.EXIT
        elif exit_score >= 25:
            signal = OrderSide.PARTIAL_EXIT
        else:
            signal = OrderSide.HOLD

        detail_parts = [
            f"SMA50{'이탈!' if ma50_broken else 'OK'}",
            f"SMA200{'이탈!' if ma200_broken else 'OK'}",
            f"MACD다이버전스{'⚠' if macd_divergence else 'OK'}",
            f"RSI다이버전스{'⚠' if rsi_divergence else 'OK'}",
            f"ADX{'하락↓' if adx_declining else 'OK'}",
            f"거래량{'고갈!' if volume_dry_up else 'OK'}",
            f"RSI={rsi:.1f}{'과매수' if rsi_overbought else ''}",
        ]

        return ExitResult(
            signal=signal,
            trailing_stop=trailing,
            partial_exit_price=partial_exit,
            full_exit_price=full_exit,
            rsi_overbought=rsi_overbought,

            ma50_broken=ma50_broken,
            ma200_broken=ma200_broken,
            macd_divergence=macd_divergence,
            rsi_divergence=rsi_divergence,
            adx_declining=adx_declining,
            volume_dry_up=volume_dry_up,
            score=round(min(STEP_MAX_SCORE, exit_score), 1),
            detail=" | ".join(detail_parts),
        )

    # ── 종합 점수/신호 ───────────────────────────────────

    def _compute_overall_score(
        self,
        market: MarketEnvResult,
        sector: SectorResult,
        screen: ScreeningResult,
        entry: EntryResult,
        risk: RiskManagementResult,
        holding: HoldingManagementResult,
        exit_: ExitResult,
    ) -> float:
        """7단계 가중 평균으로 종합 점수 산출"""
        return (
            market.score * WEIGHT_STEP1_MARKET
            + sector.score * WEIGHT_STEP2_SECTOR
            + screen.score * WEIGHT_STEP3_SCREENING
            + entry.score * WEIGHT_STEP4_ENTRY
            + risk.score * WEIGHT_STEP5_RISK
            + holding.score * WEIGHT_STEP6_HOLD
            + (STEP_MAX_SCORE - exit_.score) * WEIGHT_STEP7_EXIT  # 청산 점수 반전
        )

    def _compute_overall_signal(
        self,
        score: float,
        market: MarketEnvResult,
        screen: ScreeningResult,
        entry: EntryResult,
        exit_: ExitResult,
    ) -> OrderSide:
        """종합 점수 + 각 단계 결과로 최종 신호 결정"""
        # 청산 신호가 강하면 우선
        if exit_.signal in (OrderSide.STRONG_EXIT, OrderSide.EXIT):
            return exit_.signal
        if exit_.signal == OrderSide.PARTIAL_EXIT:
            return OrderSide.PARTIAL_EXIT

        # 시장 환경 불리 → 보류
        if not market.is_favorable:
            return OrderSide.HOLD

        # 스크리닝 미통과 → 보류
        if screen.grade in (PositionScreenGrade.C, PositionScreenGrade.F):
            return OrderSide.HOLD

        # 진입 신호 기반
        if entry.signal == OrderSide.STRONG_ENTRY and score >= 55:
            return OrderSide.STRONG_ENTRY
        if entry.signal in (OrderSide.STRONG_ENTRY, OrderSide.ENTRY) and score >= 40:
            return OrderSide.ENTRY
        return OrderSide.HOLD

    # ── 요약 생성 ─────────────────────────────────────────

    def _build_summary(
        self,
        market: MarketEnvResult,
        sector: SectorResult,
        screen: ScreeningResult,
        entry: EntryResult,
        risk: RiskManagementResult,
        holding: HoldingManagementResult,
        exit_: ExitResult,
        overall_signal: OrderSide,
        overall_score: float,
    ) -> str:
        signal_desc = {
            OrderSide.STRONG_ENTRY: "강력한 포지션 매수 신호입니다. 분할 진입을 시작하세요.",
            OrderSide.ENTRY: "포지션 매수 신호입니다. 1차 분할 매수를 고려하세요.",
            OrderSide.HOLD: "관망 신호입니다. 조건 개선을 기다리세요.",
            OrderSide.PARTIAL_EXIT: "부분 익절을 고려하세요. 추세 약화 조짐이 있습니다.",
            OrderSide.EXIT: "포지션 청산을 권장합니다. 주요 지지선이 이탈했습니다.",
            OrderSide.STRONG_EXIT: "즉시 청산을 강력히 권장합니다.",
        }

        return (
            f"[포지션 트레이딩 분석] "
            f"시장={market.environment.value}({market.score:.0f}점) | "
            f"섹터={sector.strength.value}({sector.score:.0f}점) | "
            f"스크리닝={screen.grade.value}({screen.score:.0f}점) | "
            f"진입={entry.signal.value}({entry.score:.0f}점) | "
            f"RR=1:{risk.risk_reward_ratio} | "
            f"청산압력={exit_.score:.0f}점 | "
            f"종합={overall_signal.value}({overall_score:.1f}점) | "
            f"{signal_desc.get(overall_signal, '')}"
        )
