"""
src/ta_trader/screener/intraday_screener.py
박병창 『돈을 부르는 매매의 기술』 - 장중 종목 선정 스크리너

원본 시트의 4가지 장중 선정 방법을 정량화된 실시간 스크리닝 로직으로 구현:
    1. TickSurgeScreener      - 전체 종목을 순간(단위) 체결량으로 검색
    2. PriceVolumeScanScreener - 가격/거래량 급변 + 사용자 검색식
    3. IndexLinkedScreener     - 시장 재료(지수 움직임/멈춤, 베타) 기반
    4. NewsFlashScreener       - 공시/시황/속보/뉴스 기반

장 시작 전(premarket)과의 차이:
    - 입력이 '일봉'이 아니라 '분봉(intraday_df) + 실시간 스냅샷(TickSnapshot)'
    - '순간 체결량', '체결 속도', '지수와의 동조' 등 장중 고유 개념 사용
    - 시그널은 timestamp를 포함 (장중 어느 시점인지 중요 - 10시 이전 등)

premarket.py와 동일한 ScreenResult/CheckResult 구조를 재사용하므로
PreMarketScreener와 결과를 동일한 방식으로 처리/시각화할 수 있다.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, time
from enum import Enum
from typing import Optional

import numpy as np
import pandas as pd

from .base import BaseScreener, TickSnapshot, StockData, CheckResult, ScreenResult, ScreenMethod


# ─────────────────────────────────────────────────────────────
# 장중 시간대 판단 (박병창: 10시 이전 / 14시 이후 등이 중요)
# ─────────────────────────────────────────────────────────────
class SessionPhase(Enum):
    OPENING = "개장초 (09:00-10:00)"
    MORNING = "오전장 (10:00-11:30)"
    LUNCH = "점심 무렵 (11:30-13:00)"
    AFTERNOON = "오후장 (13:00-14:30)"
    CLOSING = "마감 무렵 (14:30-15:30)"
    OFF = "장외"


def classify_session(ts: datetime) -> SessionPhase:
    """현재 시각이 장중 어느 국면인지 분류 (KRX 정규장 기준)."""
    t = ts.time()
    if time(9, 0) <= t < time(10, 0):
        return SessionPhase.OPENING
    elif time(10, 0) <= t < time(11, 30):
        return SessionPhase.MORNING
    elif time(11, 30) <= t < time(13, 0):
        return SessionPhase.LUNCH
    elif time(13, 0) <= t < time(14, 30):
        return SessionPhase.AFTERNOON
    elif time(14, 30) <= t <= time(15, 30):
        return SessionPhase.CLOSING
    return SessionPhase.OFF


# ─────────────────────────────────────────────────────────────
# 분봉 컨텍스트 (분봉이 있을 때만 사용)
# ─────────────────────────────────────────────────────────────
class IntradayContext:
    """당일 분봉 df에서 장중 지표를 계산."""

    def __init__(self, df: pd.DataFrame):
        self.df = df
        self.close = df["Close"]
        self.volume = df["Volume"]

    def momentum_last_n(self, n: int = 5) -> float:
        """최근 n개 분봉의 가격 모멘텀(%)"""
        if len(self.close) < n + 1:
            return 0.0
        return (self.close.iloc[-1] / self.close.iloc[-n - 1] - 1.0) * 100.0

    def volume_acceleration(self, n: int = 5) -> float:
        """최근 n개 분봉 거래량 / 그 이전 n개 평균 (체결 가속도)"""
        if len(self.volume) < 2 * n:
            return 1.0
        recent = self.volume.iloc[-n:].mean()
        prior = self.volume.iloc[-2 * n:-n].mean()
        return float(recent / max(prior, 1e-9))

    def is_breaking_day_high(self) -> bool:
        """당일 고가 갱신 중인지"""
        if len(self.df) < 2:
            return False
        return self.df["High"].iloc[-1] >= self.df["High"].iloc[:-1].max()



# ─────────────────────────────────────────────────────────────
# 1. 순간 체결량 검색 스크리너
# ─────────────────────────────────────────────────────────────
class TickSurgeScreener(BaseScreener):
    """전체 종목을 순간(단위) 체결량으로 검색하여 선정.

    확인 요소 (시트 기준):
        - 체결량 급증
        - 가격 급변
        - 전일 대비 거래량 급증
        - 상대 강도

    시트 단점: 종목별 집중력 떨어짐, 위험 종목 사전지식 부족.
    → 따라서 '체결 급증 + 가격 동반 상승'이 동시 충족될 때 가점.
    """
    method = ScreenMethod.TICK_SURGE

    def evaluate(self, stock: StockData) -> ScreenResult:
        if stock.snapshot is None:
            raise ValueError("실시간 스냅샷(snapshot)이 필요합니다.")

        snap = stock.snapshot
        checks: list[CheckResult] = []

        # 1) 체결량 급증 (가중 30) - 핵심 시그널
        tvr = snap.tick_volume_ratio
        surge = tvr >= 3.0
        checks.append(CheckResult(
            "체결량 급증", surge,
            min(30.0, tvr * 6.0) if surge else max(0.0, tvr * 3.0),
            f"순간체결량/평소 = {tvr:.2f}배"
        ))

        # 2) 가격 급변 (가중 25)
        chg = abs(snap.price_change_pct)
        price_move = chg >= 2.0
        checks.append(CheckResult(
            "가격 급변", price_move,
            min(25.0, chg * 3.0) if price_move else chg * 1.5,
            f"전일대비 {snap.price_change_pct:+.2f}%"
        ))

        # 3) 전일 대비 거래량 급증 (가중 25)
        vpd = snap.volume_vs_prev_day
        vol_surge = vpd >= 1.5
        checks.append(CheckResult(
            "전일대비 거래량 급증", vol_surge,
            min(25.0, vpd * 10.0) if vol_surge else max(0.0, (vpd - 0.5) * 10.0),
            f"전일 동시각 대비 {vpd:.2f}배"
        ))

        # 4) 상대 강도 (가중 20) - 가격 상승 방향이면서 체결 급증
        is_up = snap.price_change_pct > 0
        strong = is_up and surge
        checks.append(CheckResult(
            "상대 강도 (상승+급증)", strong, 20.0 if strong else 0.0,
            "상승 + 체결급증 동조" if strong else "동조 미충족"
        ))

        total = sum(c.score for c in checks)
        phase = classify_session(snap.timestamp)
        notes = [f"국면: {phase.value}",
                 "⚠ 시트 경고: 위험 종목 사전지식 부족 시 빠른 대응이 손실 초래 가능."]
        # 박병창: 개장초 급변은 변동성 크므로 주의 메모
        if phase == SessionPhase.OPENING:
            notes.append("개장초 체결급증 - 변동성 매우 큼, 분할 진입 권장.")
        return ScreenResult(stock.ticker, stock.name, self.method,
                            round(total, 1), checks, notes, timestamp=snap.timestamp)


# ─────────────────────────────────────────────────────────────
# 2. 가격/거래량 급변 + 검색식 스크리너
# ─────────────────────────────────────────────────────────────
class PriceVolumeScanScreener(BaseScreener):
    """가격과 거래량 급변 메뉴 + 사용자 검색식에 의한 선정.

    확인 요소 (시트 기준):
        - 가격 급등락
        - 거래량 급변
        - 자신이 만들어놓은 검색식에 의한 종목

    시트 단점: 시스템 의존 시 대세 흐름/테마/주도섹터 놓칠 수 있음.
    → 검색식 적중을 핵심 가점으로 두되, 분봉 모멘텀으로 보강.
    """
    method = ScreenMethod.PRICE_VOLUME_SCAN

    def evaluate(self, stock: StockData) -> ScreenResult:
        if stock.snapshot is None:
            raise ValueError("실시간 스냅샷(snapshot)이 필요합니다.")

        snap = stock.snapshot
        checks: list[CheckResult] = []

        # 1) 가격 급등락 (가중 25)
        chg = abs(snap.price_change_pct)
        price_move = chg >= 3.0
        checks.append(CheckResult(
            "가격 급등락", price_move,
            min(25.0, chg * 2.5) if price_move else chg,
            f"전일대비 {snap.price_change_pct:+.2f}%"
        ))

        # 2) 거래량 급변 (가중 25)
        vpd = snap.volume_vs_prev_day
        vol_surge = vpd >= 2.0
        checks.append(CheckResult(
            "거래량 급변", vol_surge,
            min(25.0, vpd * 8.0) if vol_surge else 0.0,
            f"전일 동시각 대비 {vpd:.2f}배"
        ))

        # 3) 사용자 검색식 적중 (가중 30) - 외부 주입
        checks.append(CheckResult(
            "검색식 적중", stock.custom_screen_hit,
            30.0 if stock.custom_screen_hit else 0.0,
            "사용자 검색식 조건 충족" if stock.custom_screen_hit else "검색식 미적중"
        ))

        # 4) 분봉 모멘텀 보강 (가중 20) - 시스템 매매 보완
        momentum_score = 0.0
        detail = "분봉 데이터 없음"
        passed = False
        if stock.df is not None and len(stock.df) >= 6:
            ictx = IntradayContext(stock.df)
            mom = ictx.momentum_last_n(5)
            vacc = ictx.volume_acceleration(5)
            passed = mom > 0 and vacc > 1.2
            momentum_score = min(20.0, max(0.0, mom * 3.0 + (vacc - 1) * 10.0)) if passed else 0.0
            detail = f"최근5분 모멘텀 {mom:+.2f}%, 거래량가속 {vacc:.2f}배"
        checks.append(CheckResult(
            "분봉 모멘텀 보강", passed, momentum_score, detail
        ))

        total = sum(c.score for c in checks)
        notes = ["⚠ 시트 경고: 검색식 의존 시 대세 흐름/테마/주도섹터 놓칠 수 있음."]
        return ScreenResult(stock.ticker, stock.name, self.method,
                            round(total, 1), checks, notes, timestamp=snap.timestamp)


# ─────────────────────────────────────────────────────────────
# 3. 시장 재료(지수 연동) 스크리너
# ─────────────────────────────────────────────────────────────
class IndexLinkedScreener(BaseScreener):
    """지수 움직임/멈춤을 이용한 종목 선정 (베타/강세종목 매매).

    확인 요소 (시트 기준):
        - 지수 움직임을 파악할 수 있도록 화면 구성
        - 지수 움직임과 멈춤을 이용한 타이밍
        - 베타계수 높거나 강세 종목

    시트 단점: 지수 변동성 줄면 매매 어려움.
    → 지수 방향성 + 종목 베타 + 종목 상대강세를 결합 평가.
    """
    method = ScreenMethod.INDEX_LINKED

    def __init__(self, index_change_pct: float, index_volatility: float = 1.0):
        """
        Args:
            index_change_pct: 당일 지수 변동률(%) (예: KOSPI +1.2%)
            index_volatility: 지수 변동성 수준 (1.0=평소, <0.5=저변동)
        """
        self.index_change_pct = index_change_pct
        self.index_volatility = index_volatility

    def evaluate(self, stock: StockData) -> ScreenResult:
        if stock.snapshot is None:
            raise ValueError("실시간 스냅샷(snapshot)이 필요합니다.")

        snap = stock.snapshot
        checks: list[CheckResult] = []

        # 1) 지수 변동성 충분 (가중 20) - 시트 단점 방어
        enough_vol = self.index_volatility >= 0.5
        checks.append(CheckResult(
            "지수 변동성 충분", enough_vol,
            20.0 if enough_vol else 0.0,
            f"지수 변동성 {self.index_volatility:.2f} "
            f"{'(매매 적합)' if enough_vol else '(저변동-매매 부적합)'}"
        ))

        # 2) 베타계수 (가중 25) - 지수 대비 민감도 높을수록 매매 용이
        high_beta = stock.beta >= 1.2
        checks.append(CheckResult(
            "높은 베타계수", high_beta,
            min(25.0, stock.beta * 12.0) if high_beta else stock.beta * 8.0,
            f"베타 {stock.beta:.2f}"
        ))

        # 3) 지수 동조 (가중 25) - 지수 상승 시 종목도 상승 방향
        index_up = self.index_change_pct > 0
        stock_up = snap.price_change_pct > 0
        in_sync = index_up == stock_up
        checks.append(CheckResult(
            "지수 동조", in_sync, 25.0 if in_sync else 0.0,
            f"지수 {self.index_change_pct:+.2f}% / 종목 {snap.price_change_pct:+.2f}%"
        ))

        # 4) 종목 상대강도 (가중 30) - 지수보다 강하게 움직이는가
        # 베타 보정 기대수익 대비 실제 수익 초과분
        expected = self.index_change_pct * stock.beta
        excess = snap.price_change_pct - expected
        outperform = excess > 0.5
        checks.append(CheckResult(
            "상대강도 (지수 초과)", outperform,
            min(30.0, excess * 6.0) if outperform else max(0.0, excess * 3.0),
            f"베타기대 {expected:+.2f}% 대비 실제 {snap.price_change_pct:+.2f}% "
            f"(초과 {excess:+.2f}%p)"
        ))

        total = sum(c.score for c in checks)
        notes = []
        if not enough_vol:
            notes.append("⚠ 시트 경고: 지수 변동성 줄면 이 방식 매매 어려움.")
        return ScreenResult(stock.ticker, stock.name, self.method,
                            round(total, 1), checks, notes, timestamp=snap.timestamp)


# ─────────────────────────────────────────────────────────────
# 4. 공시/시황/속보/뉴스 스크리너
# ─────────────────────────────────────────────────────────────
class NewsFlashScreener(BaseScreener):
    """공시, 시황, 속보, 뉴스 등을 주시한 종목 선정.

    확인 요소 (시트 기준):
        - 공시, 시황, 속보, 뉴스 등을 주시

    시트 장점: 장중 호재 급변 종목 매매, 외부충격 급락 시 단기 고수익.
    시트 단점: 신속성/재료 판단 중요. 늦은 대응은 고점 매수 손실 우려.
    → 속보 발생 + 발생 후 경과시간 + 즉각적 가격/체결 반응을 평가.
    """
    method = ScreenMethod.NEWS_FLASH

    def evaluate(self, stock: StockData) -> ScreenResult:
        if stock.snapshot is None:
            raise ValueError("실시간 스냅샷(snapshot)이 필요합니다.")

        snap = stock.snapshot
        checks: list[CheckResult] = []

        # 1) 속보/공시 발생 (가중 35) - 외부 주입, 전제 조건
        checks.append(CheckResult(
            "속보/공시 발생", stock.has_news_catalyst,
            35.0 if stock.has_news_catalyst else 0.0,
            stock.news_summary or ("속보 있음" if stock.has_news_catalyst else "속보 없음")
        ))

        # 2) 즉각적 체결 반응 (가중 35) - 뉴스에 시장이 반응 중인가
        tvr = snap.tick_volume_ratio
        reacting = tvr >= 3.0 and stock.has_news_catalyst
        checks.append(CheckResult(
            "즉각적 체결 반응", reacting,
            min(35.0, tvr * 7.0) if reacting else 0.0,
            f"순간체결량 {tvr:.2f}배 "
            f"{'(시장 반응 중)' if reacting else ''}"
        ))

        # 3) 가격 반응 방향성 (가중 30) - 급변 + 명확한 방향
        chg = abs(snap.price_change_pct)
        clear_move = chg >= 3.0 and stock.has_news_catalyst
        checks.append(CheckResult(
            "가격 반응 명확", clear_move,
            min(30.0, chg * 3.0) if clear_move else 0.0,
            f"전일대비 {snap.price_change_pct:+.2f}%"
        ))

        total = sum(c.score for c in checks)
        notes = [
            "⚠ 시트 경고: 늦은 대응은 고점 매수 손실 우려. 신속성/재료 판단이 관건.",
        ]
        # 박병창: 이미 큰 폭 상승 후 추격은 위험
        if snap.price_change_pct > 7.0:
            notes.append(f"이미 {snap.price_change_pct:+.1f}% 상승 - 추격 매수 고점 위험.")
        return ScreenResult(stock.ticker, stock.name, self.method,
                            round(total, 1), checks, notes, timestamp=snap.timestamp)


# ─────────────────────────────────────────────────────────────
# 통합 장중 스크리너
# ─────────────────────────────────────────────────────────────
class IntradayScreener:
    """장중 종목 선정 - 4가지 방법 통합 실행기.

    실시간 루프에서 주기적으로 호출하는 것을 가정:
        while market_open:
            stocks = build_intraday_stocks(...)   # 실시간 스냅샷 갱신
            results = screener.run(stocks)
            push_alerts(results)
            sleep(interval)
    """

    def __init__(self, index_change_pct: float = 0.0,
                 index_volatility: float = 1.0):
        self.screeners: dict[ScreenMethod, BaseScreener] = {
            ScreenMethod.TICK_SURGE: TickSurgeScreener(),
            ScreenMethod.PRICE_VOLUME_SCAN: PriceVolumeScanScreener(),
            ScreenMethod.INDEX_LINKED: IndexLinkedScreener(
                index_change_pct, index_volatility),
            ScreenMethod.NEWS_FLASH: NewsFlashScreener(),
        }

    def run(
        self,
        stocks: list[StockData],
        method: Optional[ScreenMethod] = None,
        min_score: float = 50.0,
        top_n: int = 20,
    ) -> dict[ScreenMethod, list[ScreenResult]]:
        methods = [method] if method else list(self.screeners.keys())
        results: dict[ScreenMethod, list[ScreenResult]] = {}
        for m in methods:
            results[m] = self.screeners[m].screen(stocks, min_score)[:top_n]
        return results

    def run_combined(
        self,
        stocks: list[StockData],
        min_score: float = 50.0,
        top_n: int = 20,
    ) -> list[tuple[str, str, dict[ScreenMethod, float]]]:
        """4가지 방법 점수를 종목별 합산해 종합 랭킹."""
        all_results = self.run(stocks, min_score=0.0, top_n=len(stocks))
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
    from datetime import datetime

    now = datetime(2026, 5, 28, 9, 35)  # 개장초 09:35

    def make_intraday_df(trend: float, n: int = 30) -> pd.DataFrame:
        np.random.seed(1)
        times = pd.date_range("2026-05-28 09:00", periods=n, freq="1min")
        base = np.linspace(0, trend, n)
        noise = np.cumsum(np.random.randn(n) * 0.001)
        close = 50000 * np.exp(base + noise)
        high = close * 1.002
        low = close * 0.998
        vol = np.random.gamma(2, 5e4, n)
        vol[-5:] *= 3  # 최근 거래량 가속
        return pd.DataFrame({"Open": close, "High": high, "Low": low,
                             "Close": close, "Volume": vol}, index=times)

    stocks = [
        # 체결 급증 + 가격 급등 + 호재
        StockData(
            "005930.KS", "삼성전자",
            df=make_intraday_df(0.06),
            snapshot=TickSnapshot(now, last_price=53000, prev_close=50000,
                                  recent_tick_volume=5e5, avg_tick_volume=8e4,
                                  cum_volume_today=8e6, prev_day_volume_at_same_time=3e6),
            sector="반도체", beta=1.4,
            has_news_catalyst=True, news_summary="HBM4 대규모 수주 공시",
            custom_screen_hit=True,
        ),
        # 지수 동조 강세, 베타 높음
        StockData(
            "000660.KS", "SK하이닉스",
            snapshot=TickSnapshot(now, last_price=204000, prev_close=200000,
                                  recent_tick_volume=2e5, avg_tick_volume=9e4,
                                  cum_volume_today=4e6, prev_day_volume_at_same_time=3.2e6),
            sector="반도체", beta=1.6,
            custom_screen_hit=True,
        ),
        # 급락 종목 (외부 충격)
        StockData(
            "035720.KS", "카카오",
            snapshot=TickSnapshot(now, last_price=38000, prev_close=42000,
                                  recent_tick_volume=4e5, avg_tick_volume=7e4,
                                  cum_volume_today=6e6, prev_day_volume_at_same_time=2e6),
            sector="인터넷", beta=1.1,
            has_news_catalyst=True, news_summary="규제 강화 속보",
        ),
        # 평범한 종목 (시그널 약함)
        StockData(
            "051910.KS", "LG화학",
            snapshot=TickSnapshot(now, last_price=400500, prev_close=400000,
                                  recent_tick_volume=8e4, avg_tick_volume=8e4,
                                  cum_volume_today=1.1e6, prev_day_volume_at_same_time=1e6),
            sector="2차전지", beta=0.9,
        ),
    ]

    # 당일 지수 +1.2%, 변동성 정상
    screener = IntradayScreener(index_change_pct=1.2, index_volatility=1.0)

    print("=" * 72)
    print(f"장중 종목 선정 - 4가지 방법별 결과  ({now:%Y-%m-%d %H:%M}, "
          f"{classify_session(now).value})")
    print("=" * 72)
    results = screener.run(stocks, min_score=30.0)
    for method, res_list in results.items():
        print(f"\n▶ {method.value}")
        if not res_list:
            print("   (통과 종목 없음)")
        for r in res_list:
            print(f"   {r.summary()}")

    print("\n" + "=" * 72)
    print("종합 랭킹 (4가지 방법 점수 합산)")
    print("=" * 72)
    combined = screener.run_combined(stocks, min_score=50.0)
    for i, (ticker, name, scores) in enumerate(combined, 1):
        total = sum(scores.values())
        detail = ", ".join(f"{m.value.split('(')[0].split('/')[0].strip()}={s:.0f}"
                           for m, s in scores.items())
        print(f"{i}. {ticker}({name}) 합계 {total:.0f}  [{detail}]")

    # 상세 리포트 (1위 종목)
    print("\n" + "=" * 72)
    print("상세 리포트: 삼성전자 - 순간 체결량 검색")
    print("=" * 72)
    r = TickSurgeScreener().evaluate(stocks[0])
    for c in r.checks:
        mark = "O" if c.passed else "X"
        print(f"  [{mark}] {c.name:18s} {c.score:5.1f}점 | {c.detail}")
    for note in r.notes:
        print(f"  · {note}")
