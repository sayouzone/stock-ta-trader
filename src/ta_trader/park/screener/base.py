from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, time
from enum import Enum
from typing import Optional

import numpy as np
import pandas as pd

# ─────────────────────────────────────────────────────────────
# 공통 데이터 구조
# ─────────────────────────────────────────────────────────────
class ScreenMethod(Enum):
    """
    장 시작 전 종목 선정 방법 (원본 시트 4구분)
    장중 종목 선정 방법 (원본 시트 4구분)
    """
    STRONG_MOMENTUM = "최근일 강세/연속 상승"
    WEAK_REVERSAL = "최근일 약세/연속 하락"
    MARKET_THEME = "시장 재료(테마/섹터)"
    CHART_PATTERN = "차트(지지/저항/추세/패턴)"
    TICK_SURGE = "순간 체결량 검색"
    PRICE_VOLUME_SCAN = "가격/거래량 급변 검색식"
    INDEX_LINKED = "시장 재료(지수 연동)"
    NEWS_FLASH = "공시/시황/속보/뉴스"


@dataclass
class TickSnapshot:
    """실시간 체결 스냅샷 (틱 데이터 집계).

    HTS/OpenAPI 실시간 시세에서 받은 현재 상태.
    """
    timestamp: datetime                       # 현재 시각
    last_price: float                         # 현재가
    prev_close: float                         # 전일 종가
    # 순간 체결량 (최근 1분 또는 N틱 누적)
    recent_tick_volume: float                 # 최근 단위시간 체결량
    avg_tick_volume: float                    # 평소 단위시간 체결량 (기준)
    # 누적 거래량
    cum_volume_today: float                   # 당일 누적 거래량
    prev_day_volume_at_same_time: float       # 전일 동일 시각 누적 거래량
    # 호가 잔량 (박병창 호가 역해석용, 선택)
    total_bid_qty: float = 0.0                # 총 매수 호가 잔량
    total_ask_qty: float = 0.0                # 총 매도 호가 잔량

    @property
    def price_change_pct(self) -> float:
        return (self.last_price / self.prev_close - 1.0) * 100.0

    @property
    def tick_volume_ratio(self) -> float:
        """순간 체결량 / 평소 체결량 (체결 급증 배율)"""
        return self.recent_tick_volume / max(self.avg_tick_volume, 1e-9)

    @property
    def volume_vs_prev_day(self) -> float:
        """전일 동일 시각 대비 누적 거래량 배율"""
        return self.cum_volume_today / max(self.prev_day_volume_at_same_time, 1e-9)


@dataclass
class StockData:
    """스크리닝 입력 단위: 한 종목의 데이터 묶음"""
    ticker: str
    name: str
    # 데이터 소스 — 셋 다 Optional, 스크리너가 필요한 것만 검사
    df: Optional[pd.DataFrame] = None          # 일봉 (premarket)
    snapshot: Optional[TickSnapshot] = None    # 실시간 (intraday)
    sector: Optional[str] = None              # 섹터명 (테마 스크리닝용)
    beta: float = 1.0                         # 지수 대비 베타계수
    # 정성적 요소 주입용 (뉴스/공시 파이프라인에서 채움)
    has_news_catalyst: bool = False           # 시장 호재 여부
    is_theme_member: bool = False             # 테마 형성 종목 여부
    theme_name: Optional[str] = None
    news_summary: Optional[str] = None
    custom_screen_hit: bool = False


@dataclass
class CheckResult:
    """개별 확인 요소의 평가 결과"""
    name: str               # 확인 요소명 (예: "신고가 여부")
    passed: bool            # 통과 여부
    score: float            # 기여 점수 (0~100)
    detail: str             # 근거 설명

@dataclass
class ScreenResult:
    """한 종목의 스크리닝 결과"""
    ticker: str
    name: str
    method: ScreenMethod
    total_score: float                        # 종합 점수 (0~100)
    checks: list[CheckResult] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)   # 정성적 메모
    timestamp: Optional[datetime] = None      # 장중 시점 (선택)

    @property
    def passed_checks(self) -> list[str]:
        return [c.name for c in self.checks if c.passed]

    @property
    def rank_key(self) -> float:
        return self.total_score

    def summary(self) -> str:
        passed = ", ".join(self.passed_checks) or "없음"
        ts = self.timestamp.strftime("%H:%M") if self.timestamp else "--:--"
        return (f"[{ts}][{self.method.value}] {self.ticker}({self.name}) "
                f"점수 {self.total_score:.1f} | 통과: {passed}")


# ─────────────────────────────────────────────────────────────
# 스크리너 베이스 클래스
# ─────────────────────────────────────────────────────────────
class BaseScreener(ABC):
    method: ScreenMethod

    @abstractmethod
    def evaluate(self, stock: StockData) -> ScreenResult:
        ...

    def screen(self, stocks: list[StockData],
               min_score: float = 50.0) -> list[ScreenResult]:
        """여러 종목을 평가하고 점수순 정렬, min_score 이상만 반환."""
        results = []
        for stock in stocks:
            try:
                r = self.evaluate(stock)
                if r.total_score >= min_score:
                    results.append(r)
            except ValueError:
                continue  # 데이터 부족 종목은 스킵
        return sorted(results, key=lambda r: r.rank_key, reverse=True)
