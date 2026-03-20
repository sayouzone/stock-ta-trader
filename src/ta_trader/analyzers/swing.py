"""
ta_trader/analyzers/swing.py
스윙 트레이딩 6단계 프로세스 분석기

6단계 프로세스:
  [1단계] 시장 환경 판단  → ADX, SMA200, ATR%
  [2단계] 종목 스크리닝   → 거래량, RS, +DI/-DI, 정배열
  [3단계] 진입 타이밍     → MACD, RSI, BB, 피보나치, EMA 크로스
  [4단계] 포지션 사이징   → ATR 기반 손절/익절, R배수, 자본 배분
  [5단계] 익절/청산 전략  → 트레일링 스톱, RSI/MACD/BB 청산 신호
  [6단계] 매매 복기       → 결과 요약

사용 예:
    analyzer = SwingTradingAnalyzer("AAPL")
    result = analyzer.analyze()
    print(f"{result.overall_signal.value} {result.overall_score:.1f}점")
"""

from __future__ import annotations

from typing import Optional

import pandas as pd

from ta_trader.base.analyzer import BaseAnalyzer
from ta_trader.data.fetcher import DataFetcher
from ta_trader.indicators.swing_calculator import SwingIndicatorCalculator
from ta_trader.indicators.atr import ATRAnalyzer, calc_atr_stop_loss, calc_atr_take_profit, calc_trailing_stop
from ta_trader.indicators.volume import VolumeAnalyzer
from ta_trader.indicators.moving_avg import MovingAverageAnalyzer, is_bullish_market, detect_ema_crossover
from ta_trader.indicators.fibonacci import (
    compute_fibonacci_levels, find_swing_points, get_fibonacci_zone,
)
from ta_trader.indicators.adx import ADXAnalyzer
from ta_trader.indicators.rsi import RSIAnalyzer
from ta_trader.indicators.macd import MACDAnalyzer
from ta_trader.indicators.bollinger import BollingerAnalyzer

from ta_trader.swing.constants import *
from ta_trader.constants import BB_BANDWIDTH_SQUEEZE
from ta_trader.models.base import CheckItem, StageResult, StageStatus
from ta_trader.models.swing import (
    SwingAnalysisResult, SwingSignal,
    MarketEnvResult, MarketEnvironment,
    ScreeningResult, ScreeningGrade,
    EntryResult, EntrySignalDetail,
    PositionSizingResult,
    ExitStrategyResult,
)
from ta_trader.utils.logger import get_logger

from ta_trader.llm.swing_prompt_builder import SwingPromptBuilder

logger = get_logger(__name__)


class SwingTradingAnalyzer(BaseAnalyzer[SwingAnalysisResult]):
    """
    스윙 트레이딩 6단계 프로세스 분석기.

    GrowthMomentumAnalyzer가 '향후 1년 내 대폭 상승할 잠재력'을 평가한다면,
    SwingTradingAnalyzer는 '단기~중기 스윙 매매의 진입/청산 타이밍'을 분석합니다.

    사용 예:
        analyzer = SwingTradingAnalyzer("005930.KS")
        result = analyzer.analyze()

        analyzer = SwingTradingAnalyzer("AAPL", capital=50_000_000)
        result = analyzer.analyze()
    """

    def __init__(
        self,
        ticker: str,
        period: str = "1y",
        interval: str = "1d",
        capital: float = POSITION_DEFAULT_CAPITAL,
        risk_pct: float = POSITION_RISK_PER_TRADE_PCT,
    ) -> None:
        super().__init__(ticker, period=period, interval=interval)
        self.capital = capital
        self.risk_pct = risk_pct

    @property
    def name(self) -> str:
        return "스윙 트레이딩 분석 에이전트"

    @property
    def role(self) -> str:
        return "스윙 매매 시장 환경 판단 및 진입/청산 신호 분석"

    @property
    def calculator(self) -> SwingIndicatorCalculator | None:
        return self._calc

    # ── 데이터 수집 (SwingIndicatorCalculator 사용) ────────

    def _fetch_data(self) -> None:
        """BaseAnalyzer의 _fetch_data를 오버라이드하여 SwingIndicatorCalculator 사용"""
        fetcher = DataFetcher(period=self.period, interval=self.interval)
        self._name, self._df = fetcher.fetch(self.ticker)
        self._calc = SwingIndicatorCalculator(self._df)
        self._name, self._info = fetcher.info(self.ticker)

    # ── 메인 분석 ─────────────────────────────────────────

    def analyze(self) -> SwingAnalysisResult:
        """6단계 스윙 트레이딩 분석 파이프라인 실행"""

        # 0. 데이터 수집 & 지표 계산
        self._fetch_data()
        df = self._calc.dataframe
        #print(self._df)
        #print(df)
        latest = self._calc.latest()
        prev = self._calc.previous()
        price = float(latest["Close"])
        date = str(df.index[-1].date())

        # 1~5단계 순차 실행
        market_env    = self._stage1_market_environment()
        screening     = self._stage2_screening()
        entry         = self._stage3_entry_signal()
        position      = self._stage4_position_sizing(entry)
        exit_strategy = self._stage5_exit_strategy(position)

        # 6단계: 종합 점수 & 신호
        overall_score = self._compute_overall_score(
            market_env, screening, entry, position, exit_strategy,
        )
        overall_signal = self._compute_overall_signal(
            overall_score, market_env, screening, entry,
        )

        summary = self._build_summary(
            market_env, screening, entry, position, exit_strategy,
            overall_signal, overall_score,
        )

        result = SwingAnalysisResult(
            ticker=self.ticker,
            name=self._name,
            date=date,
            current_price=price,
            market_env=market_env,
            screening=screening,
            entry=entry,
            position=position,
            exit_strategy=exit_strategy,
            overall_signal=overall_signal,
            overall_score=round(overall_score, 1),
            summary=summary,
        )

        logger.info(
            "스윙 분석 완료",
            ticker=self.ticker,
            name=self._name,
            signal=overall_signal.value,
            score=overall_score,
        )

        return result

    def analyze_with_llm(
        self,
        provider:    str | None = None,
        api_key:     str | None = None,
        model:       str | None = None,
        recent_days: int = 10,
        stream:      bool = False,
    ) -> SwingAnalysisResult:
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
        result = self.analyze()
        df = self._calc.dataframe

        llm = create_llm_analyzer(provider=provider, api_key=api_key, model=model)

        prompt_builder = SwingPromptBuilder()
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

    # ── 1단계: 시장 환경 판단 ─────────────────────────────

    def _stage1_market_environment(self) -> MarketEnvResult:
        """ADX, SMA200, 이평선 정배열, ATR%로 시장 환경 분류"""
        df = self._calc.dataframe
        row = self._calc.latest()

        adx_val = float(row["adx"])
        adx_trend = adx_val >= MARKET_ADX_TREND_THRESHOLD
        above_200 = is_bullish_market(row)
        ma_score = int(row.get("ma_trend_score", 2))
        atr_pct = float(row.get("atr_pct", 2.0))

        # 환경 분류
        if adx_trend and above_200 and ma_score >= 3:
            env = MarketEnvironment.BULLISH_TREND
        elif above_200 and ma_score >= 2:
            env = MarketEnvironment.BULLISH_WEAK
        elif not above_200 and adx_trend:
            env = MarketEnvironment.BEARISH_TREND
        elif atr_pct >= 4.0:
            env = MarketEnvironment.HIGH_VOLATILITY
        else:
            env = MarketEnvironment.SIDEWAYS

        # 점수 산출
        score = 0.0
        if adx_trend:
            score += 30.0
        if above_200:
            score += 30.0
        score += ma_score * 7.5   # 0~30
        if atr_pct < 4.0:
            score += 10.0

        detail_parts = []
        detail_parts.append(f"ADX={adx_val:.1f}({'추세' if adx_trend else '비추세'})")
        detail_parts.append(f"SMA200{'위' if above_200 else '아래'}")
        detail_parts.append(f"정배열={ma_score}/4")
        detail_parts.append(f"ATR%={atr_pct:.2f}%")

        return MarketEnvResult(
            environment=env,
            adx_value=adx_val,
            adx_trend_exists=adx_trend,
            above_sma200=above_200,
            ma_trend_score=ma_score,
            atr_pct=atr_pct,
            score=min(100.0, round(score, 1)),
            detail=" | ".join(detail_parts),
        )

    # ── 2단계: 종목 스크리닝 ──────────────────────────────

    def _stage2_screening(
        self
    ) -> ScreeningResult:
        """거래량, ADX, DI, 이평선 정배열, 상대강도로 종목 적합성 평가"""
        df = self._calc.dataframe
        row = self._calc.latest()

        vol_ratio = float(row.get("vol_ratio", 1.0))
        vol_surge = vol_ratio >= SCREEN_VOL_SURGE_THRESHOLD
        adx_val = float(row["adx"])
        adx_ok = adx_val >= SCREEN_MIN_ADX
        di_bullish = float(row["adx_pos"]) > float(row["adx_neg"])
        ma_score = int(row.get("ma_trend_score", 2))
        ma_aligned = ma_score >= SCREEN_MA_TREND_MIN

        # 상대강도: 최근 N일 수익률
        if len(df) >= SCREEN_RS_LOOKBACK_DAYS:
            rs_return = (
                float(df["Close"].iloc[-1]) / float(df["Close"].iloc[-SCREEN_RS_LOOKBACK_DAYS]) - 1
            ) * 100
            rs_positive = rs_return > SCREEN_RS_MIN_SCORE
        else:
            rs_return = 0.0
            rs_positive = True

        checks = [vol_surge, adx_ok, di_bullish, ma_aligned, rs_positive]
        passed = sum(checks)

        if passed >= 5:
            grade = ScreeningGrade.A_PLUS
        elif passed >= 4:
            grade = ScreeningGrade.A
        elif passed >= 3:
            grade = ScreeningGrade.B
        elif passed >= 2:
            grade = ScreeningGrade.C
        else:
            grade = ScreeningGrade.F

        score = passed / len(checks) * 100.0

        detail_parts = []
        detail_parts.append(f"거래량={vol_ratio:.2f}x({'급증' if vol_surge else '보통'})")
        detail_parts.append(f"ADX={adx_val:.1f}({'OK' if adx_ok else 'X'})")
        detail_parts.append(f"+DI{'>' if di_bullish else '<'}-DI")
        detail_parts.append(f"정배열={ma_score}({'OK' if ma_aligned else 'X'})")
        detail_parts.append(f"RS={rs_return:.1f}%({'OK' if rs_positive else 'X'})")

        return ScreeningResult(
            grade=grade,
            volume_surge=vol_surge,
            volume_ratio=vol_ratio,
            adx_sufficient=adx_ok,
            di_bullish=di_bullish,
            ma_aligned=ma_aligned,
            rs_positive=rs_positive,
            score=round(score, 1),
            checks_passed=passed,
            checks_total=len(checks),
            detail=" | ".join(detail_parts),
        )

    # ── 3단계: 진입 타이밍 ────────────────────────────────

    def _stage3_entry_signal(
        self
    ) -> EntryResult:
        """MACD, RSI, BB, 피보나치, EMA 크로스로 진입 타이밍 판단"""
        df = self._calc.dataframe
        row = self._calc.latest()
        prev = self._calc.previous()

        signals: list[EntrySignalDetail] = []
        total_score = 0.0

        # (a) MACD 골든크로스
        macd_diff = float(row["macd_diff"])
        prev_diff = float(prev["macd_diff"]) if prev is not None else 0.0
        macd_gc = prev_diff <= 0 < macd_diff
        macd_score = 0.0
        if macd_gc:
            macd_score = 20.0
            if float(row["macd"]) > 0:
                macd_score += ENTRY_MACD_ABOVE_ZERO_BONUS
        signals.append(EntrySignalDetail(
            "MACD 골든크로스", macd_gc, macd_score,
            f"MACD Hist: {prev_diff:.3f} → {macd_diff:.3f}",
        ))
        total_score += macd_score

        # (b) RSI 과매도 반등
        rsi = float(row["rsi"])
        prev_rsi = float(prev["rsi"]) if prev is not None else 50.0
        rsi_bounce = prev_rsi <= ENTRY_RSI_OVERSOLD_BOUNCE and rsi > prev_rsi
        rsi_recovery = rsi >= ENTRY_RSI_RECOVERY_TARGET and prev_rsi < ENTRY_RSI_RECOVERY_TARGET
        rsi_score = 0.0
        if rsi_bounce:
            rsi_score = 15.0
        if rsi_recovery:
            rsi_score = 20.0
        signals.append(EntrySignalDetail(
            "RSI 반등/회복", rsi_bounce or rsi_recovery, rsi_score,
            f"RSI: {prev_rsi:.1f} → {rsi:.1f}",
        ))
        total_score += rsi_score

        # (c) BB 하단 반등
        bb_pct = float(row["bb_pct"])
        prev_bb = float(prev["bb_pct"]) if prev is not None else 0.5
        bb_bounce = prev_bb <= ENTRY_BB_LOWER_BOUNCE and bb_pct > prev_bb
        bb_score = 15.0 if bb_bounce else 0.0
        signals.append(EntrySignalDetail(
            "BB 하단 반등", bb_bounce, bb_score,
            f"BB%B: {prev_bb:.2f} → {bb_pct:.2f}",
        ))
        total_score += bb_score

        # (d) BB 스퀴즈 상단 돌파
        bb_width = float(row["bb_width"])
        bb_breakout = bb_width <= BB_BANDWIDTH_SQUEEZE and bb_pct >= ENTRY_BB_SQUEEZE_BREAKOUT
        bb_brk_score = 20.0 if bb_breakout else 0.0
        signals.append(EntrySignalDetail(
            "BB 스퀴즈 돌파", bb_breakout, bb_brk_score,
            f"BW={bb_width:.1f}% BB%B={bb_pct:.2f}",
        ))
        total_score += bb_brk_score

        # (e) 피보나치 골든존
        fibo_in_golden = False
        fibo_score = 0.0
        try:
            sh, sl, direction = find_swing_points(df, lookback=60)
            fibo = compute_fibonacci_levels(sh, sl, direction)
            zone = get_fibonacci_zone(float(row["Close"]), fibo)
            fibo_in_golden = "골든존" in zone
            if fibo_in_golden:
                fibo_score = 15.0
            signals.append(EntrySignalDetail(
                "피보나치 골든존", fibo_in_golden, fibo_score,
                f"{zone} (H={sh:.0f} L={sl:.0f})",
            ))
        except Exception:
            signals.append(EntrySignalDetail(
                "피보나치 골든존", False, 0.0, "계산 불가",
            ))
        total_score += fibo_score

        # (f) EMA 골든크로스
        ema_cross = detect_ema_crossover(row, prev)
        ema_gc = ema_cross == "골든크로스"
        ema_score = 15.0 if ema_gc else 0.0
        signals.append(EntrySignalDetail(
            "EMA9/21 크로스", ema_gc, ema_score,
            f"EMA 크로스: {ema_cross}",
        ))
        total_score += ema_score

        # 진입 신호 결정
        total_score = min(100.0, total_score)

        if total_score >= ENTRY_SCORE_STRONG_BUY:
            signal = SwingSignal.STRONG_ENTRY
        elif total_score >= ENTRY_SCORE_BUY:
            signal = SwingSignal.ENTRY
        else:
            signal = SwingSignal.HOLD

        return EntryResult(
            signal=signal,
            score=round(total_score, 1),
            signals=signals,
            macd_golden_cross=macd_gc,
            rsi_oversold_bounce=rsi_bounce or rsi_recovery,
            bb_lower_bounce=bb_bounce,
            bb_squeeze_breakout=bb_breakout,
            fibo_golden_zone=fibo_in_golden,
            ema_golden_cross=ema_gc,
            detail=f"발동 {sum(1 for s in signals if s.triggered)}/{len(signals)} 신호",
        )

    # ── 4단계: 포지션 사이징 ──────────────────────────────

    def _stage4_position_sizing(
        self,
        entry: EntryResult,
    ) -> PositionSizingResult:
        """ATR 기반 손절/익절, R배수, 자본 배분 산출"""
        df = self._calc.dataframe
        row = self._calc.latest()

        price = float(row["Close"])
        atr = float(row["atr"])

        # ATR 기반 손절/익절
        stop_loss = calc_atr_stop_loss(price, atr, POSITION_ATR_SL_MULTIPLIER)
        take_profit = calc_atr_take_profit(price, atr, POSITION_ATR_TP_MULTIPLIER)

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
        is_acceptable = rr_ratio >= POSITION_MIN_RR_RATIO

        # 포지션 사이즈 (자본의 risk_pct를 넘지 않도록)
        max_risk = self.capital * self.risk_pct
        if risk_per_share > 0:
            pos_size = int(max_risk / risk_per_share)
        else:
            pos_size = 0

        pos_value = pos_size * price
        portfolio_pct = (pos_value / self.capital * 100) if self.capital > 0 else 0.0

        # 최대 비중 제한
        if portfolio_pct > POSITION_MAX_PORTFOLIO_PCT * 100:
            pos_size = int(self.capital * POSITION_MAX_PORTFOLIO_PCT / price)
            pos_value = pos_size * price
            portfolio_pct = pos_value / self.capital * 100

        # 점수
        score = 0.0
        if is_acceptable:
            score += 40.0
        if rr_ratio >= 3.0:
            score += 20.0
        if portfolio_pct <= 15.0:
            score += 20.0
        if risk_per_share > 0:
            score += 20.0
        score = min(100.0, score)

        detail = (
            f"진입={price:,.0f} 손절={stop_loss:,.0f} "
            f"익절={take_profit:,.0f} RR=1:{rr_ratio} "
            f"수량={pos_size}주 비중={portfolio_pct:.1f}%"
        )

        return PositionSizingResult(
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
            fibo_target_161=fibo_161,
            fibo_target_261=fibo_261,
        )

    # ── 5단계: 익절/청산 전략 ─────────────────────────────

    def _stage5_exit_strategy(
        self,
        position: PositionSizingResult,
    ) -> ExitStrategyResult:
        """트레일링 스톱, RSI/MACD/BB 청산 신호 판단"""
        row = self._calc.latest()
        prev = self._calc.previous()

        price = float(row["Close"])
        atr = float(row["atr"])

        # 트레일링 스톱
        trailing = calc_trailing_stop(price, atr, EXIT_TRAILING_ATR_MULTIPLIER)

        # RSI 과매수
        rsi = float(row["rsi"])
        rsi_ob = rsi >= EXIT_RSI_OVERBOUGHT

        # MACD 데드크로스
        macd_diff = float(row["macd_diff"])
        prev_diff = float(prev["macd_diff"]) if prev is not None else 0.0
        macd_dc = prev_diff >= 0 > macd_diff

        # BB 상단 터치
        bb_pct = float(row["bb_pct"])
        bb_upper = bb_pct >= EXIT_BB_UPPER_TOUCH

        # 1차 익절가 (ATR 기반)
        partial_exit = round(position.entry_price + atr * POSITION_ATR_TP_MULTIPLIER * 0.5, 2)
        full_exit = position.take_profit

        # 청산 신호 결정
        exit_score = 0.0
        if rsi_ob:
            exit_score += 30.0
        if macd_dc:
            exit_score += 35.0
        if bb_upper:
            exit_score += 20.0
        if rsi >= EXIT_RSI_EXTREME:
            exit_score += 15.0

        if exit_score >= 60:
            signal = SwingSignal.STRONG_EXIT
        elif exit_score >= 40:
            signal = SwingSignal.EXIT
        elif exit_score >= 25:
            signal = SwingSignal.PARTIAL_EXIT
        else:
            signal = SwingSignal.HOLD

        detail_parts = []
        detail_parts.append(f"트레일링={trailing:,.0f}")
        detail_parts.append(f"RSI={rsi:.1f}({'과매수' if rsi_ob else 'OK'})")
        detail_parts.append(f"MACD {'데드크로스!' if macd_dc else 'OK'}")
        detail_parts.append(f"BB%B={bb_pct:.2f}({'상단' if bb_upper else 'OK'})")

        return ExitStrategyResult(
            trailing_stop=trailing,
            partial_exit_price=partial_exit,
            full_exit_price=full_exit,
            rsi_overbought=rsi_ob,
            macd_dead_cross=macd_dc,
            bb_upper_touch=bb_upper,
            current_signal=signal,
            score=round(min(100.0, exit_score), 1),
            detail=" | ".join(detail_parts),
        )

    # ── 종합 점수/신호 ───────────────────────────────────

    def _compute_overall_score(
        self,
        market: MarketEnvResult,
        screen: ScreeningResult,
        entry: EntryResult,
        position: PositionSizingResult,
        exit_: ExitStrategyResult,
    ) -> float:
        """5단계 가중 평균으로 종합 점수 산출"""
        # 가중치: 시장(15%) + 스크리닝(20%) + 진입(35%) + 포지션(20%) + 익절(10%)
        return (
            market.score * 0.15
            + screen.score * 0.20
            + entry.score * 0.35
            + position.score * 0.20
            + (100.0 - exit_.score) * 0.10  # 익절 점수는 반전 (청산 권장이 낮을수록 보유 유리)
        )

    def _compute_overall_signal(
        self,
        score: float,
        market: MarketEnvResult,
        screen: ScreeningResult,
        entry: EntryResult,
    ) -> SwingSignal:
        """종합 점수 + 각 단계 결과로 최종 신호 결정"""
        # 시장 환경 불리 → 보류
        if not market.is_favorable:
            return SwingSignal.HOLD

        # 스크리닝 미통과 → 보류
        if screen.grade in (ScreeningGrade.C, ScreeningGrade.F):
            return SwingSignal.HOLD

        # 진입 신호 기반
        if entry.signal == SwingSignal.STRONG_ENTRY and score >= 60:
            return SwingSignal.STRONG_ENTRY
        if entry.signal in (SwingSignal.STRONG_ENTRY, SwingSignal.ENTRY) and score >= 40:
            return SwingSignal.ENTRY
        return SwingSignal.HOLD

    # ── 요약 생성 ─────────────────────────────────────────

    @staticmethod
    def _build_summary(
        market: MarketEnvResult,
        screen: ScreeningResult,
        entry: EntryResult,
        position: PositionSizingResult,
        exit_: ExitStrategyResult,
        overall_signal: SwingSignal,
        overall_score: float,
    ) -> str:
        """종합 요약 문자열 생성"""
        signal_desc = {
            SwingSignal.STRONG_ENTRY: "적극 매수 진입. 적극 진입을 고려하세요.",
            SwingSignal.ENTRY: "스윙 매수 신호입니다. 분할 진입을 권장합니다.",
            SwingSignal.HOLD: "보류 신호입니다. 조건 개선을 기다리세요.",
            SwingSignal.PARTIAL_EXIT: "부분 익절을 고려하세요.",
            SwingSignal.EXIT: "포지션 청산을 권장합니다.",
            SwingSignal.STRONG_EXIT: "즉시 청산을 강력히 권장합니다.",
        }

        return (
            f"[스윙 트레이딩 분석] "
            f"시장={market.environment.value}({market.score:.0f}점) | "
            f"스크리닝={screen.grade.value}({screen.score:.0f}점) | "
            f"진입={entry.signal.value}({entry.score:.0f}점) | "
            f"RR=1:{position.risk_reward_ratio} | "
            f"종합={overall_signal.value}({overall_score:.1f}점) | "
            f"{signal_desc.get(overall_signal, '')}"
        )