"""
src/ta_trader/screener/premarket.py
박병창 『돈을 부르는 매매의 기술』 - 장 시작 전 종목 선정 스크리너

원본 시트의 4가지 선정 방법을 정량화된 스크리닝 로직으로 구현:
    1. StrongMomentumScreener   - 최근일 강세 또는 연속 상승 종목
    2. WeakReversalScreener     - 최근일 약세 또는 연속 하락 종목 (반등 노림)
    3. MarketThemeScreener      - 시장 재료(테마/섹터 상대강도) 기반
    4. ChartPatternScreener     - 차트(지지/저항/추세/패턴) 기반

설계 원칙:
    - 정량화 가능한 요소(신고가, 거래량, 매물대 돌파 등)는 자동 계산
    - 정성적 요소(시장 호재, 테마)는 외부 입력(news_flags 등)으로 주입
    - 각 스크리너는 ScreenResult 리스트를 반환 (점수 + 통과 사유)
    - stock-ta-trader의 DataAgent에서 받은 OHLCV df를 입력으로 사용
"""

from __future__ import annotations

from typing import Optional

import numpy as np
import pandas as pd

from .base import BaseScreener, StockData, CheckResult, ScreenResult, ScreenMethod


# ─────────────────────────────────────────────────────────────
# 공통 지표 계산 유틸 (park_rules.core_concepts와 공유 가능)
# ─────────────────────────────────────────────────────────────
class TechnicalContext:
    """OHLCV df에서 자주 쓰는 지표를 미리 계산해 캐싱."""

    def __init__(self, df: pd.DataFrame):
        if len(df) < 20:
            raise ValueError("최소 20거래일 데이터 필요")
        self.df = df
        c = df["Close"]
        v = df["Volume"]
        h = df["High"]
        l = df["Low"]

        self.close = float(c.iloc[-1])
        self.prev_close = float(c.iloc[-2])
        self.ma5 = c.rolling(5).mean()
        self.ma20 = c.rolling(20).mean()
        self.ma60 = c.rolling(60).mean() if len(df) >= 60 else None
        self.vol = v
        self.vol_ma20 = v.rolling(20).mean()

        # 최근 등락률
        self.daily_return = (self.close / self.prev_close - 1.0) * 100.0

        # 고가/저가 기준 (52주 ≈ 250일, 데이터 부족 시 전체)
        window = min(len(df), 250)
        self.high_52w = float(h.iloc[-window:].max())
        self.low_52w = float(l.iloc[-window:].min())

        # 당일 등락폭 (장중 변동성)
        self.intraday_range_pct = (
            (float(h.iloc[-1]) - float(l.iloc[-1])) / self.prev_close * 100.0
        )

    def consecutive_up_days(self) -> int:
        """연속 상승 일수"""
        c = self.df["Close"]
        count = 0
        for i in range(len(c) - 1, 0, -1):
            if c.iloc[i] > c.iloc[i - 1]:
                count += 1
            else:
                break
        return count

    def consecutive_down_days(self) -> int:
        """연속 하락 일수"""
        c = self.df["Close"]
        count = 0
        for i in range(len(c) - 1, 0, -1):
            if c.iloc[i] < c.iloc[i - 1]:
                count += 1
            else:
                break
        return count

    def volume_ratio(self) -> float:
        """당일 거래량 / 20일 평균"""
        avg = self.vol_ma20.iloc[-1]
        return float(self.vol.iloc[-1] / avg) if avg > 0 else 0.0

    def is_near_high(self, tolerance: float = 0.02) -> bool:
        """신고가 근접 여부 (52주 고가 대비 tolerance 이내)"""
        return self.close >= self.high_52w * (1 - tolerance)

    def is_near_low(self, tolerance: float = 0.02) -> bool:
        """신저가 근접 여부"""
        return self.close <= self.low_52w * (1 + tolerance)

    def volume_profile_resistance(self, bins: int = 30) -> float:
        """최대 매물대(집중 거래 가격대) 반환 - 매물대 돌파 판단용"""
        df = self.df
        edges = np.linspace(df["Low"].min(), df["High"].max(), bins + 1)
        centers = (edges[:-1] + edges[1:]) / 2
        profile = np.zeros(bins)
        for _, row in df.iterrows():
            lo = max(0, min(bins - 1, np.searchsorted(edges, row["Low"]) - 1))
            hi = max(0, min(bins - 1, np.searchsorted(edges, row["High"]) - 1))
            nb = hi - lo + 1
            if nb > 0:
                profile[lo:hi + 1] += row["Volume"] / nb
        return float(centers[int(np.argmax(profile))])


# ─────────────────────────────────────────────────────────────
# 1. 강세/연속 상승 종목 스크리너
# ─────────────────────────────────────────────────────────────
class StrongMomentumScreener(BaseScreener):
    """최근일 강세 또는 연속 상승 종목 선정.

    확인 요소 (시트 기준):
        - 신고가 여부
        - 매물대 돌파 여부
        - 거래량 증감
        - 하루 중 등락폭과 추세 유지 여부
        - 지지와 저항
        - 패턴 형성 여부 (간이)
        - 최근 시장 호재 (외부 주입)
        - 테마 형성 여부 (외부 주입)
    """
    method = ScreenMethod.STRONG_MOMENTUM

    def evaluate(self, stock: StockData) -> ScreenResult:
        if stock.df is None:
            raise ValueError("일봉 데이터(df)가 필요합니다.")
        
        ctx = TechnicalContext(stock.df)
        checks: list[CheckResult] = []

        # 1) 신고가 여부 (가중 20)
        near_high = ctx.is_near_high(tolerance=0.03)
        checks.append(CheckResult(
            "신고가 여부", near_high, 20.0 if near_high else 0.0,
            f"종가 {ctx.close:,.0f} vs 52주 고가 {ctx.high_52w:,.0f}"
            f" ({ctx.close / ctx.high_52w * 100:.1f}%)"
        ))

        # 2) 매물대 돌파 여부 (가중 18)
        resistance = ctx.volume_profile_resistance()
        broke_out = ctx.close > resistance
        checks.append(CheckResult(
            "매물대 돌파 여부", broke_out, 18.0 if broke_out else 0.0,
            f"종가 {ctx.close:,.0f} vs 최대 매물대 {resistance:,.0f}"
        ))

        # 3) 거래량 증감 (가중 18) - 평균 1.5배 이상
        vr = ctx.volume_ratio()
        vol_surge = vr >= 1.5
        vol_score = min(18.0, vr * 7.0) if vol_surge else max(0.0, vr * 4.0)
        checks.append(CheckResult(
            "거래량 증감", vol_surge, vol_score,
            f"당일/20일평균 = {vr:.2f}배"
        ))

        # 4) 당일 강세 + 추세 유지 (가중 16)
        is_up = ctx.daily_return > 0
        up_days = ctx.consecutive_up_days()
        trend_score = 0.0
        if is_up:
            trend_score = 8.0 + min(8.0, up_days * 2.0)
        checks.append(CheckResult(
            "등락폭/추세 유지", is_up, trend_score,
            f"당일 {ctx.daily_return:+.2f}%, 연속상승 {up_days}일"
        ))

        # 5) 지지/저항: 5일선 위 (가중 12)
        above_ma5 = ctx.close > ctx.ma5.iloc[-1]
        checks.append(CheckResult(
            "지지/저항 (5일선 위)", above_ma5, 12.0 if above_ma5 else 0.0,
            f"종가 {ctx.close:,.0f} vs 5일선 {ctx.ma5.iloc[-1]:,.0f}"
        ))

        # 6) 패턴 형성 (간이): 정배열 5>20>60 (가중 6)
        aligned = False
        if ctx.ma60 is not None:
            aligned = (ctx.ma5.iloc[-1] > ctx.ma20.iloc[-1] > ctx.ma60.iloc[-1])
        checks.append(CheckResult(
            "패턴 (정배열)", aligned, 6.0 if aligned else 0.0,
            "5일>20일>60일 정배열" if aligned else "정배열 아님"
        ))

        # 7) 시장 호재 (외부 주입, 가중 5)
        checks.append(CheckResult(
            "최근 시장 호재", stock.has_news_catalyst,
            5.0 if stock.has_news_catalyst else 0.0,
            "호재 있음" if stock.has_news_catalyst else "호재 정보 없음"
        ))

        # 8) 테마 형성 (외부 주입, 가중 5)
        checks.append(CheckResult(
            "테마 형성 여부", stock.is_theme_member,
            5.0 if stock.is_theme_member else 0.0,
            f"테마: {stock.theme_name}" if stock.is_theme_member else "테마 없음"
        ))

        total = sum(c.score for c in checks)
        notes = []
        if not stock.has_news_catalyst:
            notes.append("호재/테마 정보 미주입 - 뉴스 파이프라인 연동 권장")
        return ScreenResult(stock.ticker, stock.name, self.method,
                            round(total, 1), checks, notes)


# ─────────────────────────────────────────────────────────────
# 2. 약세/연속 하락 종목 스크리너 (반등 노림)
# ─────────────────────────────────────────────────────────────
class WeakReversalScreener(BaseScreener):
    """최근일 약세 또는 연속 하락 종목 선정 (장중 급락 후 반등 매매).

    확인 요소 (시트 기준):
        - 신저가 여부
        - 반등 시 매물대 확인
        - 거래량 증감
        - 하루 중 등락폭과 하향 추세 여부
        - 저항선 하향 돌파 여부
        - 최근 시장 약세 이유 (외부 주입)

    주의: 시트의 단점대로 "약세 지속" 위험이 크므로,
          단순 하락이 아니라 '반등 가능성' 신호를 가점한다.
    """
    method = ScreenMethod.WEAK_REVERSAL

    def evaluate(self, stock: StockData) -> ScreenResult:
        if stock.df is None:
            raise ValueError("일봉 데이터(df)가 필요합니다.")
        
        ctx = TechnicalContext(stock.df)
        checks: list[CheckResult] = []

        # 1) 신저가 여부 (가중 18) - 과매도 영역 진입
        near_low = ctx.is_near_low(tolerance=0.03)
        checks.append(CheckResult(
            "신저가 여부", near_low, 18.0 if near_low else 0.0,
            f"종가 {ctx.close:,.0f} vs 52주 저가 {ctx.low_52w:,.0f}"
        ))

        # 2) 연속 하락 (가중 14) - 과도한 낙폭은 반등 여지
        down_days = ctx.consecutive_down_days()
        many_down = down_days >= 3
        checks.append(CheckResult(
            "연속 하락/하향추세", many_down,
            min(14.0, down_days * 4.0),
            f"연속하락 {down_days}일"
        ))

        # 3) 거래량 급증 (가중 18) - 투매(capitulation) 신호
        vr = ctx.volume_ratio()
        vol_spike = vr >= 2.0
        checks.append(CheckResult(
            "거래량 급증(투매)", vol_spike,
            min(18.0, vr * 6.0) if vol_spike else 0.0,
            f"당일/20일평균 = {vr:.2f}배"
        ))

        # 4) 당일 반등 신호 (가중 20) - 종가가 저가보다 높이 마감
        low_today = float(ctx.df["Low"].iloc[-1])
        close_recovery = (
            (ctx.close - low_today) / max(ctx.intraday_range_pct, 1e-9)
        )
        # 저가 대비 종가 회복 비율
        intra_low = float(ctx.df["Low"].iloc[-1])
        intra_high = float(ctx.df["High"].iloc[-1])
        recovery_pct = ((ctx.close - intra_low) / max(intra_high - intra_low, 1e-9))
        bounced = recovery_pct >= 0.5
        checks.append(CheckResult(
            "장중 반등 (아래꼬리)", bounced,
            20.0 * recovery_pct if bounced else 5.0 * recovery_pct,
            f"저가 대비 종가 회복률 {recovery_pct * 100:.0f}%"
        ))

        # 5) 반등 매물대까지 거리 (가중 15) - 목표가 여력
        resistance = ctx.volume_profile_resistance()
        upside = (resistance - ctx.close) / ctx.close * 100.0
        has_upside = upside > 2.0
        checks.append(CheckResult(
            "반등 매물대 여력", has_upside,
            min(15.0, upside) if has_upside else 0.0,
            f"매물대 {resistance:,.0f}까지 +{upside:.1f}%"
        ))

        # 6) 시장 약세 이유 파악 (외부 주입, 가중 - 정보성)
        # 약세 이유가 '일시적'이면 반등 가점, '구조적'이면 회피
        checks.append(CheckResult(
            "약세 이유 파악", stock.has_news_catalyst,
            0.0,  # 점수 미반영, 정보 표시용
            "약세 이유 확인 필요 (일시적 vs 구조적)"
        ))

        total = sum(c.score for c in checks)
        notes = [
            "⚠ 시트 경고: 약세 종목은 반등이 작고 하락이 깊어질 위험.",
            "약세 이유가 '구조적'이면 진입 회피 권장.",
        ]
        return ScreenResult(stock.ticker, stock.name, self.method,
                            round(total, 1), checks, notes)


# ─────────────────────────────────────────────────────────────
# 3. 시장 재료(테마/섹터) 스크리너
# ─────────────────────────────────────────────────────────────
class MarketThemeScreener(BaseScreener):
    """시장 재료에 의한 종목 선정 (테마/섹터 상대강도).

    확인 요소 (시트 기준):
        - 테마 형성
        - 강세 섹터 (상대강도)
        - 호재 발표 또는 예정 종목

    주의: 시트 단점대로 '이미 상투' 위험. 상대강도는 높되
          단기 과열(RSI 등)은 감점한다.
    """
    method = ScreenMethod.MARKET_THEME

    def __init__(self, sector_returns: Optional[dict[str, float]] = None):
        """
        Args:
            sector_returns: {섹터명: 최근 N일 수익률(%)}.
                            섹터 상대강도 계산용. None이면 종목 자체 모멘텀만 사용.
        """
        self.sector_returns = sector_returns or {}

    def evaluate(self, stock: StockData) -> ScreenResult:
        if stock.df is None:
            raise ValueError("일봉 데이터(df)가 필요합니다.")
        
        ctx = TechnicalContext(stock.df)
        checks: list[CheckResult] = []

        # 1) 테마 형성 (외부 주입, 가중 30)
        checks.append(CheckResult(
            "테마 형성", stock.is_theme_member,
            30.0 if stock.is_theme_member else 0.0,
            f"테마: {stock.theme_name}" if stock.is_theme_member else "테마 없음"
        ))

        # 2) 강세 섹터 - 섹터 상대강도 (가중 30)
        sector_ret = self.sector_returns.get(stock.sector or "", None)
        strong_sector = sector_ret is not None and sector_ret > 0
        sector_score = 0.0
        if strong_sector:
            sector_score = min(30.0, sector_ret * 3.0)
        checks.append(CheckResult(
            "강세 섹터", strong_sector, sector_score,
            f"섹터 '{stock.sector}' 수익률 {sector_ret:+.1f}%"
            if sector_ret is not None else "섹터 수익률 정보 없음"
        ))

        # 3) 호재 발표/예정 (외부 주입, 가중 25)
        checks.append(CheckResult(
            "호재 발표/예정", stock.has_news_catalyst,
            25.0 if stock.has_news_catalyst else 0.0,
            "호재 있음" if stock.has_news_catalyst else "호재 정보 없음"
        ))

        # 4) 상투 경계 - 단기 과열 감점 (가중 15, 역방향)
        # 연속 상승 과도하면 감점 (이미 상투 위험)
        up_days = ctx.consecutive_up_days()
        not_overheated = up_days <= 4
        overheating_score = 15.0 if not_overheated else max(0.0, 15.0 - (up_days - 4) * 5.0)
        checks.append(CheckResult(
            "상투 경계 (과열 아님)", not_overheated, overheating_score,
            f"연속상승 {up_days}일 {'(적정)' if not_overheated else '(과열 주의)'}"
        ))

        total = sum(c.score for c in checks)
        notes = ["⚠ 시트 경고: 핫한 테마는 이미 상투일 수 있음. 재료 해석 속도가 관건."]
        return ScreenResult(stock.ticker, stock.name, self.method,
                            round(total, 1), checks, notes)


# ─────────────────────────────────────────────────────────────
# 4. 차트(지지/저항/추세/패턴) 스크리너
# ─────────────────────────────────────────────────────────────
class ChartPatternScreener(BaseScreener):
    """차트에 의한 종목 선정 (미리 분석한 가격권 기준 매매).

    확인 요소 (시트 기준):
        - 지지와 저항, 추세, 패턴 등의 차트 분석

    장점(시트): 미리 분석한 가격권 기준으로 신속 대응 가능.
    단점(시트): 예상 매매는 위험.
    → 따라서 '명확한 지지/저항 근접' 시점만 시그널을 낸다.
    """
    method = ScreenMethod.CHART_PATTERN

    def evaluate(self, stock: StockData) -> ScreenResult:
        if stock.df is None:
            raise ValueError("일봉 데이터(df)가 필요합니다.")
        
        ctx = TechnicalContext(stock.df)
        checks: list[CheckResult] = []

        # 1) 추세 방향 (가중 25) - 20일선 기울기
        ma20_now = ctx.ma20.iloc[-1]
        ma20_prev = ctx.ma20.iloc[-6]  # 5일 전
        uptrend = ma20_now > ma20_prev
        slope_pct = (ma20_now / ma20_prev - 1.0) * 100.0
        checks.append(CheckResult(
            "추세 (20일선 기울기)", uptrend,
            min(25.0, abs(slope_pct) * 5.0) if uptrend else 0.0,
            f"20일선 5일 기울기 {slope_pct:+.2f}%"
        ))

        # 2) 지지 근접 (가중 25) - 5일선/20일선 지지 테스트
        ma5_now = ctx.ma5.iloc[-1]
        dist_ma5 = abs(ctx.close - ma5_now) / ctx.close * 100.0
        dist_ma20 = abs(ctx.close - ma20_now) / ctx.close * 100.0
        near_support = (dist_ma5 < 2.0 or dist_ma20 < 2.0) and ctx.close >= ma20_now
        checks.append(CheckResult(
            "지지선 근접", near_support, 25.0 if near_support else 0.0,
            f"5일선까지 {dist_ma5:.1f}%, 20일선까지 {dist_ma20:.1f}%"
        ))

        # 3) 저항 돌파/근접 (가중 25) - 매물대 기준
        resistance = ctx.volume_profile_resistance()
        dist_resist = (resistance - ctx.close) / ctx.close * 100.0
        # 저항 바로 아래(돌파 임박) 또는 막 돌파
        near_breakout = -2.0 <= dist_resist <= 3.0
        checks.append(CheckResult(
            "저항(매물대) 돌파 임박", near_breakout,
            25.0 if near_breakout else 0.0,
            f"매물대 {resistance:,.0f}까지 {dist_resist:+.1f}%"
        ))

        # 4) 패턴: 변동성 수축 (가중 25) - 박스권 후 돌파 기대
        recent_range = ctx.df["High"].iloc[-10:].max() - ctx.df["Low"].iloc[-10:].min()
        prior_range = ctx.df["High"].iloc[-30:-10].max() - ctx.df["Low"].iloc[-30:-10].min()
        contraction = recent_range < prior_range * 0.7
        checks.append(CheckResult(
            "패턴 (변동성 수축)", contraction, 25.0 if contraction else 0.0,
            f"최근10일 변동폭이 직전 대비 {recent_range / max(prior_range, 1e-9) * 100:.0f}%"
        ))

        total = sum(c.score for c in checks)
        notes = ["⚠ 시트 경고: 예상 매매는 위험. 가격권 도달 확인 후 진입."]
        return ScreenResult(stock.ticker, stock.name, self.method,
                            round(total, 1), checks, notes)


# ─────────────────────────────────────────────────────────────
# 통합 스크리너 (4가지 방법을 한 번에 실행)
# ─────────────────────────────────────────────────────────────
class PreMarketScreener:
    """장 시작 전 종목 선정 - 4가지 방법 통합 실행기.

    stock-ta-trader의 CLI에서:
        park scan --method strong --min-score 60
    형태로 호출하는 것을 가정.
    """

    def __init__(self, sector_returns: Optional[dict[str, float]] = None):
        self.screeners: dict[ScreenMethod, BaseScreener] = {
            ScreenMethod.STRONG_MOMENTUM: StrongMomentumScreener(),
            ScreenMethod.WEAK_REVERSAL: WeakReversalScreener(),
            ScreenMethod.MARKET_THEME: MarketThemeScreener(sector_returns),
            ScreenMethod.CHART_PATTERN: ChartPatternScreener(),
        }

    def run(
        self,
        stocks: list[StockData],
        method: Optional[ScreenMethod] = None,
        min_score: float = 50.0,
        top_n: int = 20,
    ) -> dict[ScreenMethod, list[ScreenResult]]:
        """
        Args:
            stocks:    스크리닝 대상 종목 리스트
            method:    특정 방법만 실행 (None이면 4가지 모두)
            min_score: 최소 통과 점수
            top_n:     방법별 상위 N개만 반환
        """
        methods = [method] if method else list(self.screeners.keys())
        results: dict[ScreenMethod, list[ScreenResult]] = {}
        for m in methods:
            screener = self.screeners[m]
            results[m] = screener.screen(stocks, min_score)[:top_n]
        return results

    def run_combined(
        self,
        stocks: list[StockData],
        min_score: float = 50.0,
        top_n: int = 20,
    ) -> list[tuple[str, str, dict[ScreenMethod, float]]]:
        """모든 방법의 점수를 종목별로 합산해 종합 랭킹 산출.

        Returns:
            [(ticker, name, {method: score, ...}), ...] 점수 합 내림차순
        """
        all_results = self.run(stocks, min_score=0.0, top_n=len(stocks))
        # 종목별로 방법별 점수 수집
        by_ticker: dict[str, dict] = {}
        for m, res_list in all_results.items():
            for r in res_list:
                if r.ticker not in by_ticker:
                    by_ticker[r.ticker] = {"name": r.name, "scores": {}}
                by_ticker[r.ticker]["scores"][m] = r.total_score

        ranked = []
        for ticker, info in by_ticker.items():
            total = sum(info["scores"].values())
            if total >= min_score:
                ranked.append((ticker, info["name"], info["scores"], total))
        ranked.sort(key=lambda x: x[3], reverse=True)
        return [(t, n, s) for t, n, s, _ in ranked[:top_n]]


# ─────────────────────────────────────────────────────────────
# 데모
# ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    np.random.seed(0)

    def make_df(trend: float, vol_spike_last: bool = False,
                bounce: bool = False) -> pd.DataFrame:
        n = 120
        dates = pd.date_range("2026-01-01", periods=n, freq="B")
        drift = np.linspace(0, trend, n)
        noise = np.cumsum(np.random.randn(n) * 0.02)
        close = np.exp(4.0 + drift + noise) * 1000
        open_ = close * (1 + np.random.randn(n) * 0.005)
        high = np.maximum(close, open_) * (1 + np.abs(np.random.randn(n)) * 0.01)
        low = np.minimum(close, open_) * (1 - np.abs(np.random.randn(n)) * 0.01)
        volume = np.random.gamma(3, 1e6, n).astype(int)
        if vol_spike_last:
            volume[-1] *= 4
        if bounce:
            # 마지막 봉: 장중 깊은 저가 후 종가 회복
            low[-1] = close[-1] * 0.93
            high[-1] = close[-1] * 1.005
        return pd.DataFrame({"Open": open_, "High": high, "Low": low,
                             "Close": close, "Volume": volume}, index=dates)

    stocks = [
        StockData("005930.KS", "삼성전자", make_df(0.5, vol_spike_last=True),
                  sector="반도체", has_news_catalyst=True,
                  is_theme_member=True, theme_name="AI 반도체"),
        StockData("000660.KS", "SK하이닉스",  make_df(0.6),
                  sector="반도체", is_theme_member=True, theme_name="AI 반도체"),
        StockData("035720.KS", "카카오", make_df(-0.4, vol_spike_last=True, bounce=True),
                  sector="인터넷"),
        StockData("051910.KS", "LG화학", make_df(0.05),
                  sector="2차전지"),
    ]

    sector_returns = {"반도체": 8.5, "인터넷": -2.0, "2차전지": 1.5}

    screener = PreMarketScreener(sector_returns=sector_returns)

    print("=" * 70)
    print("장 시작 전 종목 선정 - 4가지 방법별 결과")
    print("=" * 70)
    results = screener.run(stocks, min_score=30.0)
    for method, res_list in results.items():
        print(f"\n▶ {method.value}")
        if not res_list:
            print("   (통과 종목 없음)")
        for r in res_list:
            print(f"   {r.summary()}")

    print("\n" + "=" * 70)
    print("종합 랭킹 (4가지 방법 점수 합산)")
    print("=" * 70)
    combined = screener.run_combined(stocks, min_score=50.0)
    for i, (ticker, name, scores) in enumerate(combined, 1):
        total = sum(scores.values())
        detail = ", ".join(f"{m.value.split('/')[0]}={s:.0f}"
                           for m, s in scores.items())
        print(f"{i}. {ticker}({name}) 합계 {total:.0f}  [{detail}]")
