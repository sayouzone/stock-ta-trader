"""
ta_trader/recommend/engine.py
종목 추천 엔진

분석 파이프라인:
  1. TradingDecision 목록 수신
  2. 종목별 다차원 평가:
     - 추세 강도/방향 (ADX, +DI/-DI)
     - 모멘텀 전환 (MACD 히스토그램, 크로스오버)
     - 가격 위치 (RSI 과매수/과매도 여력, BB %B)
     - 변동성 상태 (BB 밴드폭, 스퀴즈 여부)
     - 전략 합치도 (체제-전략 정합성, 신호 일관성)
     - 리스크/보상 비율
  3. 다차원 점수를 종합하여 추천 등급 결정
  4. 등급별 분류 및 순위 매김

사용 예:
    engine = RecommendationEngine()
    report = engine.analyze(decisions)
"""

from __future__ import annotations

from ta_trader.constants.short import (
    ADX_STRONG_TREND, ADX_WEAK_TREND,
    RSI_OVERBOUGHT, RSI_OVERSOLD, RSI_UPPER_NEUTRAL, RSI_LOWER_NEUTRAL,
    BB_UPPER_THRESHOLD, BB_LOWER_THRESHOLD,
    BB_BANDWIDTH_SQUEEZE, BB_BANDWIDTH_EXPAND,
)
from ta_trader.models.short import (
    IndicatorResult, MarketRegime, Signal, StrategyType, TradingDecision,
)
from ta_trader.models.recommend import (
    Grade, Rationale, Recommendation, RecommendationReport,
)


class RecommendationEngine:
    """
    복수 종목의 TradingDecision을 분석하여
    추천 근거가 포함된 RecommendationReport를 생성합니다.
    """

    def analyze(self, decisions: list[TradingDecision]) -> RecommendationReport:
        """
        TradingDecision 리스트를 받아 추천 보고서를 반환합니다.

        Args:
            decisions: ShortTermAnalyzer.analyze() 결과 리스트

        Returns:
            RecommendationReport
        """
        recs: list[Recommendation] = []

        for dec in decisions:
            rec = self._evaluate_single(dec)
            recs.append(rec)

        # 신뢰도 × 등급 가중치로 최종 정렬
        grade_weight = {
            Grade.STRONG_BUY: 5, Grade.BUY: 4,
            Grade.CONDITIONAL: 3, Grade.WATCH: 2, Grade.AVOID: 1,
        }
        recs.sort(
            key=lambda r: (grade_weight[r.grade], r.confidence, r.score),
            reverse=True,
        )

        # 순위 부여
        for i, rec in enumerate(recs, 1):
            rec.rank = i

        # 등급별 분류
        buy_picks  = [r for r in recs if r.grade in (Grade.STRONG_BUY, Grade.BUY, Grade.CONDITIONAL)]
        watch_list = [r for r in recs if r.grade == Grade.WATCH]
        avoid_list = [r for r in recs if r.grade == Grade.AVOID]

        report_date = decisions[0].date if decisions else ""

        return RecommendationReport(
            date=report_date,
            recommendations=recs,
            buy_picks=buy_picks,
            watch_list=watch_list,
            avoid_list=avoid_list,
        )

    # ── 단일 종목 평가 ───────────────────────────────────

    def _evaluate_single(self, dec: TradingDecision) -> Recommendation:
        """단일 TradingDecision을 다차원 평가하여 Recommendation 생성"""
        bullish: list[Rationale] = []
        bearish: list[Rationale] = []
        risks:   list[Rationale] = []

        # 지표 결과를 이름으로 인덱싱
        ind_map = {ind.name: ind for ind in dec.indicators}
        adx_r  = ind_map.get("ADX")
        rsi_r  = ind_map.get("RSI")
        macd_r = ind_map.get("MACD")
        bb_r   = ind_map.get("Bollinger Bands")

        # 1. 추세 분석
        self._analyze_trend(dec, adx_r, bullish, bearish, risks)

        # 2. 모멘텀 분석
        self._analyze_momentum(dec, macd_r, bullish, bearish, risks)

        # 3. 가격 위치 분석
        self._analyze_price_position(dec, rsi_r, bb_r, bullish, bearish, risks)

        # 4. 변동성 분석
        self._analyze_volatility(dec, bb_r, bullish, bearish, risks)

        # 5. 전략 합치도 분석
        self._analyze_confluence(dec, adx_r, rsi_r, macd_r, bb_r, bullish, bearish, risks)

        # 6. 리스크/보상 분석
        self._analyze_risk_reward(dec, risks)

        # 등급·신뢰도 결정
        grade, confidence = self._determine_grade(dec, bullish, bearish, risks)

        # 진입 조건 및 행동 제안 생성
        entry_condition = self._build_entry_condition(dec, grade, bullish, bearish)
        action_plan     = self._build_action_plan(dec, grade, bullish, risks)

        return Recommendation(
            decision=dec,
            grade=grade,
            confidence=confidence,
            bullish_factors=bullish,
            bearish_factors=bearish,
            risk_factors=risks,
            entry_condition=entry_condition,
            action_plan=action_plan,
        )

    # ── 1. 추세 분석 ─────────────────────────────────────

    def _analyze_trend(
        self, dec: TradingDecision, adx_r: IndicatorResult | None,
        bullish: list, bearish: list, risks: list,
    ) -> None:
        if adx_r is None:
            return

        adx_val = adx_r.raw_value
        desc    = adx_r.description

        # +DI/-DI 방향 추출 (description 파싱)
        di_bullish = "+DI" in desc and "우위" not in desc  # 기본 로직
        # description 형태: "ADX=50.8 (+DI=35.7, -DI=11.1) [강한추세]"
        try:
            di_plus  = float(desc.split("+DI=")[1].split(",")[0])
            di_minus = float(desc.split("-DI=")[1].split(")")[0])
            di_bullish = di_plus > di_minus
            di_ratio   = di_plus / max(di_minus, 0.1)
        except (IndexError, ValueError):
            di_ratio = 1.0

        # 강한 추세
        if adx_val >= ADX_STRONG_TREND:
            if di_bullish:
                strength = "매우 강함" if adx_val >= 40 else "강함"
                bullish.append(Rationale(
                    category="추세",
                    direction="긍정",
                    summary=f"ADX={adx_val:.1f} 강한 상승 추세 ({strength})",
                    detail=(
                        f"ADX가 {adx_val:.1f}로 강한 추세 구간(≥25)에 진입해 있고, "
                        f"+DI가 -DI 대비 {di_ratio:.1f}배 우위입니다. "
                        f"추세추종 전략의 적중률이 가장 높은 영역으로, "
                        f"추세 방향(상승) 순행 매매가 유효합니다."
                    ),
                ))
                if adx_val >= 50:
                    risks.append(Rationale(
                        category="추세",
                        direction="부정",
                        summary="ADX 극단치로 추세 피로 가능",
                        detail=(
                            f"ADX가 {adx_val:.1f}로 50을 초과하여 추세 과열 구간입니다. "
                            f"추세가 극도로 강하지만, 이 수준에서는 추세 피로(trend exhaustion)로 "
                            f"급반전이 발생할 수 있으므로 손절선을 반드시 설정해야 합니다."
                        ),
                    ))
            else:
                bearish.append(Rationale(
                    category="추세",
                    direction="부정",
                    summary=f"ADX={adx_val:.1f} 강한 하락 추세",
                    detail=(
                        f"ADX가 {adx_val:.1f}로 강한 추세이지만 -DI가 우위입니다. "
                        f"하락 방향의 추세추종이 작동하는 구간으로, "
                        f"역추세 매수는 위험합니다."
                    ),
                ))

        # 약한 추세
        elif adx_val >= ADX_WEAK_TREND:
            direction_str = "상승" if di_bullish else "하락"
            factor = bullish if di_bullish else bearish
            factor.append(Rationale(
                category="추세",
                direction="긍정" if di_bullish else "부정",
                summary=f"ADX={adx_val:.1f} 약한 {direction_str} 추세 (전환 구간)",
                detail=(
                    f"ADX가 {adx_val:.1f}로 추세와 횡보 사이의 전환 구간입니다. "
                    f"추세가 강화되면 추세추종으로, 약화되면 횡보로 전환될 수 있어 "
                    f"방향성이 확정될 때까지 신중한 접근이 필요합니다."
                ),
            ))

        # 횡보
        else:
            risks.append(Rationale(
                category="추세",
                direction="중립",
                summary=f"ADX={adx_val:.1f} 횡보 (추세 부재)",
                detail=(
                    f"ADX가 {adx_val:.1f}로 방향성이 약합니다. "
                    f"추세추종 전략은 비효율적이며, "
                    f"평균회귀(BB/RSI 과매수·과매도 역추세) 전략이 적합한 구간입니다."
                ),
            ))

    # ── 2. 모멘텀 분석 ────────────────────────────────────

    def _analyze_momentum(
        self, dec: TradingDecision, macd_r: IndicatorResult | None,
        bullish: list, bearish: list, risks: list,
    ) -> None:
        if macd_r is None:
            return

        hist = macd_r.raw_value  # macd_diff (히스토그램)
        desc = macd_r.description
        has_cross = "크로스" in desc

        # MACD/Signal 값 파싱
        try:
            macd_val = float(desc.split("MACD=")[1].split(" ")[0])
            sig_val  = float(desc.split("Signal=")[1].split(" ")[0])
            hist_val = float(desc.split("Hist=")[1].split(" ")[0].rstrip("]"))
        except (IndexError, ValueError):
            macd_val, sig_val, hist_val = 0, 0, hist

        if has_cross and hist > 0:
            bullish.append(Rationale(
                category="모멘텀",
                direction="긍정",
                summary="MACD 골든크로스 발생 — 상승 전환 신호",
                detail=(
                    f"MACD 히스토그램이 양전환하며 골든크로스가 발생했습니다. "
                    f"하락 모멘텀이 소진되고 상승 모멘텀이 시작되는 "
                    f"전형적인 매수 타이밍 신호입니다. "
                    f"히스토그램={hist_val:+.3f}"
                ),
            ))
        elif has_cross and hist < 0:
            bearish.append(Rationale(
                category="모멘텀",
                direction="부정",
                summary="MACD 데드크로스 발생 — 하락 전환 신호",
                detail=(
                    f"MACD 히스토그램이 음전환하며 데드크로스가 발생했습니다. "
                    f"상승 모멘텀이 소진되고 하락 모멘텀이 시작됩니다. "
                    f"히스토그램={hist_val:+.3f}"
                ),
            ))
        elif hist > 0:
            if hist_val > 0 and macd_val < 0:
                # 히스토그램 양전환이지만 MACD 라인 자체는 아직 음수
                bullish.append(Rationale(
                    category="모멘텀",
                    direction="긍정",
                    summary="MACD 히스토그램 양전환 — 반전 초기 신호",
                    detail=(
                        f"히스토그램이 양전환({hist_val:+.3f})되어 하락 모멘텀이 감속 중입니다. "
                        f"MACD 라인({macd_val:.3f})이 시그널({sig_val:.3f})에 수렴하고 있어 "
                        f"조만간 골든크로스가 발생할 수 있습니다."
                    ),
                ))
            elif hist_val > 0:
                bullish.append(Rationale(
                    category="모멘텀",
                    direction="긍정",
                    summary=f"MACD 상승 모멘텀 지속 (Hist={hist_val:+.3f})",
                    detail=(
                        f"MACD 히스토그램({hist_val:+.3f})이 양수를 유지하며 "
                        f"상승 모멘텀이 지속되고 있습니다."
                    ),
                ))
        elif hist < 0:
            if abs(hist_val) < 0.1 and macd_val > sig_val * 0.9:
                risks.append(Rationale(
                    category="모멘텀",
                    direction="중립",
                    summary="MACD 하락 모멘텀 감속 중",
                    detail=(
                        f"히스토그램({hist_val:+.3f})이 음수이지만 절댓값이 감소 추세로, "
                        f"하락 모멘텀이 약해지고 있습니다. 반전 가능성을 주시하세요."
                    ),
                ))
            else:
                bearish.append(Rationale(
                    category="모멘텀",
                    direction="부정",
                    summary=f"MACD 하락 모멘텀 (Hist={hist_val:+.3f})",
                    detail=(
                        f"MACD 히스토그램({hist_val:+.3f})이 음수로 "
                        f"하락 모멘텀이 지속 중입니다. "
                        f"MACD={macd_val:.3f}, Signal={sig_val:.3f}"
                    ),
                ))

    # ── 3. 가격 위치 분석 ─────────────────────────────────

    def _analyze_price_position(
        self, dec: TradingDecision,
        rsi_r: IndicatorResult | None, bb_r: IndicatorResult | None,
        bullish: list, bearish: list, risks: list,
    ) -> None:
        if rsi_r is None or bb_r is None:
            return

        rsi_val = rsi_r.raw_value
        bb_pct  = bb_r.raw_value  # 0~1 범위의 %B

        # RSI 과매도 + BB 하단 = 강한 반등 후보
        if rsi_val <= RSI_OVERSOLD and bb_pct <= BB_LOWER_THRESHOLD:
            bullish.append(Rationale(
                category="가격위치",
                direction="긍정",
                summary=f"RSI({rsi_val:.1f}) 과매도 + BB 하단({bb_pct*100:.1f}%) — 강한 반등 후보",
                detail=(
                    f"RSI가 {rsi_val:.1f}로 과매도 구간이고, "
                    f"동시에 볼린저 밴드 하단 근처(BB%={bb_pct*100:.1f}%)에 위치합니다. "
                    f"두 지표의 동시 과매도는 평균회귀 관점에서 "
                    f"강한 반등 가능성을 시사합니다."
                ),
            ))
        # RSI 과매수 + BB 상단 = 하락 반전 경고
        elif rsi_val >= RSI_OVERBOUGHT and bb_pct >= BB_UPPER_THRESHOLD:
            bearish.append(Rationale(
                category="가격위치",
                direction="부정",
                summary=f"RSI({rsi_val:.1f}) 과매수 + BB 상단({bb_pct*100:.1f}%) — 과열 경고",
                detail=(
                    f"RSI가 {rsi_val:.1f}로 과매수이고 BB%={bb_pct*100:.1f}%로 "
                    f"밴드 상단에 근접해 있습니다. "
                    f"신규 매수보다는 보유 중이면 익절을, "
                    f"미보유면 눌림목까지 대기하는 것이 안전합니다."
                ),
            ))
        else:
            # 개별 분석
            self._analyze_rsi_detail(rsi_val, dec, bullish, bearish, risks)
            self._analyze_bb_position(bb_pct, bullish, bearish, risks)

    def _analyze_rsi_detail(
        self, rsi: float, dec: TradingDecision,
        bullish: list, bearish: list, risks: list,
    ) -> None:
        is_trend = dec.market_regime == MarketRegime.STRONG_TREND

        if rsi <= RSI_OVERSOLD:
            bullish.append(Rationale(
                category="가격위치",
                direction="긍정",
                summary=f"RSI={rsi:.1f} 과매도 — 반등 여력 충분",
                detail=(
                    f"RSI가 {rsi:.1f}로 과매도 구간입니다. "
                    f"중립(50) 대비 상승 여력이 {50 - rsi:.0f}pt 있습니다."
                ),
            ))
        elif rsi >= RSI_OVERBOUGHT:
            if is_trend:
                risks.append(Rationale(
                    category="가격위치",
                    direction="중립",
                    summary=f"RSI={rsi:.1f} 과매수이나 강한 추세장에서는 지속 가능",
                    detail=(
                        f"RSI가 {rsi:.1f}로 과매수이지만, 현재 강한 추세(추세추종) 구간에서는 "
                        f"'아직 모멘텀이 살아있다'로 해석합니다. "
                        f"다만 70 초과 시 추세 피로 가능성이 높아지므로 주의가 필요합니다."
                    ),
                ))
            else:
                bearish.append(Rationale(
                    category="가격위치",
                    direction="부정",
                    summary=f"RSI={rsi:.1f} 과매수 — 단기 하락 압력",
                    detail=(
                        f"RSI가 {rsi:.1f}로 과매수 구간이며 추세가 강하지 않아 "
                        f"되돌림 가능성이 높습니다. "
                        f"신규 매수보다는 RSI가 60대로 눌릴 때까지 대기를 권장합니다."
                    ),
                ))
        elif rsi <= RSI_LOWER_NEUTRAL:
            bullish.append(Rationale(
                category="가격위치",
                direction="긍정",
                summary=f"RSI={rsi:.1f} 중립 하단 — 상승 여력 충분",
                detail=(
                    f"RSI가 {rsi:.1f}로 중립 하단(30~40)에 위치합니다. "
                    f"상승 여력이 충분하며, 모멘텀 전환 시 빠르게 반응할 수 있는 위치입니다."
                ),
            ))
        elif rsi >= RSI_UPPER_NEUTRAL:
            risks.append(Rationale(
                category="가격위치",
                direction="중립",
                summary=f"RSI={rsi:.1f} 중립 상단 — 추가 상승 여력 제한적",
                detail=(
                    f"RSI가 {rsi:.1f}로 중립 상단(60~70)에 있어 "
                    f"추가 상승 여력이 제한적입니다. "
                    f"과매수 진입 전이므로 당장 위험하지는 않지만, "
                    f"상승 모멘텀이 약해질 수 있습니다."
                ),
            ))

    def _analyze_bb_position(
        self, bb_pct: float,
        bullish: list, bearish: list, risks: list,
    ) -> None:
        pct_display = bb_pct * 100

        if bb_pct <= BB_LOWER_THRESHOLD:
            bullish.append(Rationale(
                category="가격위치",
                direction="긍정",
                summary=f"BB%={pct_display:.1f}% 하단 근접 — 평균회귀 매수 영역",
                detail=(
                    f"가격이 볼린저 밴드 하단 근처(BB%={pct_display:.1f}%)에 위치합니다. "
                    f"횡보장에서 하단 터치 후 중간선 복귀 확률이 높아 "
                    f"평균회귀 매수 기회입니다."
                ),
            ))
        elif bb_pct >= BB_UPPER_THRESHOLD:
            bearish.append(Rationale(
                category="가격위치",
                direction="부정",
                summary=f"BB%={pct_display:.1f}% 상단 근접 — 저항 구간",
                detail=(
                    f"가격이 볼린저 밴드 상단 근처(BB%={pct_display:.1f}%)에 위치합니다. "
                    f"추세장이 아니라면 저항에 막혀 되돌림이 발생할 수 있습니다."
                ),
            ))
        elif 0.4 <= bb_pct <= 0.6:
            # 중간 근처 → 양방향 여력 있음
            pass  # 중립이므로 특별한 근거 불필요

    # ── 4. 변동성 분석 ────────────────────────────────────

    def _analyze_volatility(
        self, dec: TradingDecision, bb_r: IndicatorResult | None,
        bullish: list, bearish: list, risks: list,
    ) -> None:
        if bb_r is None:
            return

        desc = bb_r.description
        try:
            bw = float(desc.split("밴드폭=")[1].split("%")[0])
        except (IndexError, ValueError):
            return

        if bw <= BB_BANDWIDTH_SQUEEZE:
            bullish.append(Rationale(
                category="변동성",
                direction="긍정",
                summary=f"밴드폭={bw:.1f}% 스퀴즈 — 큰 움직임 임박",
                detail=(
                    f"볼린저 밴드폭이 {bw:.1f}%로 극도로 수축(≤{BB_BANDWIDTH_SQUEEZE}%)된 "
                    f"스퀴즈 상태입니다. 에너지가 축적되어 있어 "
                    f"조만간 큰 방향성 움직임이 발생할 가능성이 높습니다. "
                    f"돌파 방향을 확인한 후 진입하는 것이 안전합니다."
                ),
            ))
            risks.append(Rationale(
                category="변동성",
                direction="중립",
                summary="스퀴즈 돌파 방향 미확정 — 방향 확인 필요",
                detail=(
                    f"스퀴즈 상태에서 상방 돌파와 하방 돌파 확률이 모두 존재합니다. "
                    f"BB 상단 돌파 + MACD 양전환 확인 시 매수, "
                    f"BB 하단 돌파 + MACD 음전환 시 매수 보류가 원칙입니다."
                ),
            ))
        elif bw >= BB_BANDWIDTH_EXPAND:
            if bw >= 30:
                risks.append(Rationale(
                    category="변동성",
                    direction="부정",
                    summary=f"밴드폭={bw:.1f}% 극단적 변동성",
                    detail=(
                        f"밴드폭이 {bw:.1f}%로 매우 넓어 변동성이 극단적입니다. "
                        f"큰 수익 기회이기도 하지만 손절 폭이 넓어져 "
                        f"리스크 관리가 어렵습니다. 포지션 사이즈를 줄이는 것을 권장합니다."
                    ),
                ))
            else:
                risks.append(Rationale(
                    category="변동성",
                    direction="중립",
                    summary=f"밴드폭={bw:.1f}% 변동성 확대 구간",
                    detail=(
                        f"밴드폭이 {bw:.1f}%로 확대(≥{BB_BANDWIDTH_EXPAND}%)되어 있습니다. "
                        f"횡보장에서는 평균회귀 전략이 유효하고, "
                        f"추세장에서는 추세 방향 포지션이 유효합니다."
                    ),
                ))
        else:
            # 정상 범위 변동성
            if bw < 7:
                bullish.append(Rationale(
                    category="변동성",
                    direction="긍정",
                    summary=f"밴드폭={bw:.1f}% 안정적 변동성",
                    detail=(
                        f"변동성이 {bw:.1f}%로 안정적입니다. "
                        f"손절 폭을 타이트하게 설정할 수 있어 "
                        f"리스크 관리에 유리한 구간입니다."
                    ),
                ))

    # ── 5. 전략 합치도 분석 ───────────────────────────────

    def _analyze_confluence(
        self, dec: TradingDecision,
        adx_r: IndicatorResult | None, rsi_r: IndicatorResult | None,
        macd_r: IndicatorResult | None, bb_r: IndicatorResult | None,
        bullish: list, bearish: list, risks: list,
    ) -> None:
        indicators = [adx_r, rsi_r, macd_r, bb_r]
        bullish_count = sum(1 for i in indicators if i and i.signal.is_bullish)
        bearish_count = sum(1 for i in indicators if i and i.signal.is_bearish)
        total = sum(1 for i in indicators if i is not None)

        if bullish_count >= 3:
            bullish.append(Rationale(
                category="전략합치",
                direction="긍정",
                summary=f"4개 지표 중 {bullish_count}개 매수 신호 — 높은 합치도",
                detail=(
                    f"{total}개 지표 중 {bullish_count}개가 매수 방향을 가리키고 있어 "
                    f"신호 합치도가 높습니다. 복수 지표가 같은 방향일수록 "
                    f"신호의 신뢰도가 올라갑니다."
                ),
            ))
        elif bearish_count >= 3:
            bearish.append(Rationale(
                category="전략합치",
                direction="부정",
                summary=f"4개 지표 중 {bearish_count}개 매도 신호 — 매수 비적합",
                detail=(
                    f"{total}개 지표 중 {bearish_count}개가 매도 방향을 가리키고 있어 "
                    f"역추세 매수는 위험합니다."
                ),
            ))
        elif bullish_count >= 2 and bearish_count <= 1:
            bullish.append(Rationale(
                category="전략합치",
                direction="긍정",
                summary=f"지표 {bullish_count}개 매수 vs {bearish_count}개 매도 — 매수 우위",
                detail=(
                    f"매수 신호({bullish_count}개)가 매도 신호({bearish_count}개)보다 우세합니다. "
                    f"완전한 합치는 아니지만 매수 방향에 무게가 실립니다."
                ),
            ))
        else:
            risks.append(Rationale(
                category="전략합치",
                direction="중립",
                summary=f"지표 신호 혼재 (매수 {bullish_count} / 매도 {bearish_count}) — 방향성 불명확",
                detail=(
                    f"매수 신호({bullish_count}개)와 매도 신호({bearish_count}개)가 혼재되어 "
                    f"방향성이 불명확합니다. 추가 확인 없이 진입하면 "
                    f"손절 확률이 높아집니다."
                ),
            ))

    # ── 6. 리스크/보상 분석 ───────────────────────────────

    def _analyze_risk_reward(
        self, dec: TradingDecision, risks: list,
    ) -> None:
        if dec.risk is None:
            return

        rr = dec.risk.risk_reward_ratio
        price = dec.current_price
        sl = dec.risk.stop_loss
        tp = dec.risk.take_profit

        sl_pct = abs(price - sl) / price * 100
        tp_pct = abs(tp - price) / price * 100

        if rr >= 2.0:
            # 좋은 RR은 risk가 아닌 bullish에 추가하지 않음 (이미 별도 분석됨)
            risks.append(Rationale(
                category="리스크",
                direction="긍정",
                summary=f"RR=1:{rr:.1f} — 양호한 리스크/보상 비율",
                detail=(
                    f"손절 {sl_pct:.1f}%({sl:,.2f}) / 익절 {tp_pct:.1f}%({tp:,.2f})로 "
                    f"리스크 대비 보상이 {rr:.1f}배입니다. "
                    f"RR 2.0 이상은 양호한 수준입니다."
                ),
            ))
        elif rr >= 1.0:
            risks.append(Rationale(
                category="리스크",
                direction="중립",
                summary=f"RR=1:{rr:.1f} — 보통 수준의 리스크/보상",
                detail=(
                    f"손절 {sl_pct:.1f}% / 익절 {tp_pct:.1f}%로 "
                    f"리스크 대비 보상이 {rr:.1f}배입니다. "
                    f"승률이 50% 이상이라면 수익 가능한 수준입니다."
                ),
            ))
        else:
            risks.append(Rationale(
                category="리스크",
                direction="부정",
                summary=f"RR=1:{rr:.1f} — 불리한 리스크/보상 비율",
                detail=(
                    f"손절 {sl_pct:.1f}% / 익절 {tp_pct:.1f}%로 "
                    f"리스크가 보상보다 큽니다. "
                    f"높은 승률 없이는 장기적으로 수익을 내기 어렵습니다."
                ),
            ))

    # ── 등급 결정 ─────────────────────────────────────────

    def _determine_grade(
        self, dec: TradingDecision,
        bullish: list[Rationale], bearish: list[Rationale], risks: list[Rationale],
    ) -> tuple[Grade, float]:
        """
        긍정/부정/리스크 요인 수와 복합 점수를 종합하여
        추천 등급과 신뢰도를 결정합니다.
        """
        score = dec.composite_score
        n_bull = len(bullish)
        n_bear = len(bearish)
        n_risk_neg = sum(1 for r in risks if r.direction == "부정")

        # 기본 점수 기반 등급
        if score >= 20 and n_bull >= 3 and n_bear == 0:
            grade = Grade.STRONG_BUY
        elif score >= 15 and n_bull >= 2 and n_bear <= 1:
            grade = Grade.BUY
        elif score >= 5 and n_bull >= 2:
            grade = Grade.BUY
        elif score > 0 and n_bull >= 1:
            grade = Grade.CONDITIONAL
        elif score > -10 and n_bull >= 1:
            grade = Grade.WATCH
        elif dec.final_signal.is_bearish:
            grade = Grade.AVOID
        elif score <= -15:
            grade = Grade.AVOID
        else:
            grade = Grade.WATCH

        # 부정 요인이 많으면 등급 하향
        if n_bear >= 3 and grade in (Grade.STRONG_BUY, Grade.BUY):
            grade = Grade.WATCH
        elif n_bear >= 2 and grade == Grade.STRONG_BUY:
            grade = Grade.BUY
        elif n_risk_neg >= 2 and grade == Grade.STRONG_BUY:
            grade = Grade.BUY

        # 매도 신호인데 긍정 요인이 있으면 WATCH로
        if dec.final_signal.is_bearish and n_bull >= 2:
            grade = max(grade, Grade.WATCH, key=lambda g: list(Grade).index(g))
            grade = Grade.WATCH

        # 신뢰도 계산 (0~1)
        total_factors = n_bull + n_bear + len(risks)
        if total_factors == 0:
            confidence = 0.3
        else:
            # 긍정 비율 기반
            positive_ratio = n_bull / total_factors
            # 합치도 보너스
            confluence_bonus = 0.1 if n_bull >= 3 else 0.0
            # 점수 절대값 보너스
            score_bonus = min(abs(score) / 100, 0.2)
            confidence = min(1.0, positive_ratio * 0.6 + score_bonus + confluence_bonus + 0.1)

        return grade, round(confidence, 2)

    # ── 진입 조건 / 행동 제안 생성 ────────────────────────

    def _build_entry_condition(
        self, dec: TradingDecision, grade: Grade,
        bullish: list, bearish: list,
    ) -> str:
        strategy = dec.strategy_type

        if grade == Grade.AVOID:
            return "매수 비추천 — 매도 신호가 우세하므로 진입하지 마세요."

        conditions = []

        if strategy == StrategyType.TREND_FOLLOWING:
            conditions.append("추세 방향 확인: +DI > -DI 유지 확인")
            conditions.append("MACD 히스토그램 양수 유지 확인")
            conditions.append(f"손절: BB 하단 또는 ATR 1.5배 하방 → {dec.stop_loss:,.2f}" if dec.stop_loss else "")

        elif strategy == StrategyType.MEAN_REVERSION:
            conditions.append("BB 하단 터치 + RSI 과매도 동시 발생 시 진입")
            conditions.append("BB 중간선 도달 시 1차 익절")
            conditions.append(f"손절: BB 하단 이탈 → {dec.stop_loss:,.2f}" if dec.stop_loss else "")

        elif strategy == StrategyType.BREAKOUT_MOMENTUM:
            conditions.append("BB 상단 돌파 + MACD 양전환 시 매수 진입")
            conditions.append("BB 하단 돌파 시 매수 보류")
            conditions.append("ADX 상승 전환 확인 (추세 형성 시작)")

        elif strategy == StrategyType.ADAPTIVE_DEFAULT:
            conditions.append("추세 강화 시 추세추종 전환 대기")
            conditions.append("ADX 25 돌파 시 방향 확인 후 진입")

        if grade == Grade.CONDITIONAL:
            conditions.insert(0, "⚠ 아래 조건 충족 시에만 진입:")

        return " | ".join(c for c in conditions if c)

    def _build_action_plan(
        self, dec: TradingDecision, grade: Grade,
        bullish: list, risks: list,
    ) -> str:
        price = dec.current_price

        if grade == Grade.STRONG_BUY:
            sl_str = f" 손절: {dec.stop_loss:,.2f}" if dec.stop_loss else ""
            tp_str = f" 익절: {dec.take_profit:,.2f}" if dec.take_profit else ""
            return (
                f"적극 매수 추천. 현재가({price:,.2f}) 부근에서 진입 가능."
                f"{sl_str},{tp_str}"
            )
        elif grade == Grade.BUY:
            return (
                f"매수 추천. 현재가({price:,.2f}) 부근에서 분할 진입을 권장. "
                f"1차 50% 진입 후 추가 확인 시 나머지 진입."
            )
        elif grade == Grade.CONDITIONAL:
            return (
                f"조건부 매수. 현재가({price:,.2f})에서 즉시 진입보다는 "
                f"진입 조건 충족 여부를 확인한 후 소량 진입."
            )
        elif grade == Grade.WATCH:
            return "관망 추천. 방향성이 확정될 때까지 대기하세요."
        else:
            return "매수 비추천. 매도 신호가 우세하므로 진입을 피하세요."
