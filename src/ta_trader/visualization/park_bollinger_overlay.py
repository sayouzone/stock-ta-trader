"""
ta_trader/visualization/park_bollinger_overlay.py
박병창 매수/매도 원칙 vs 볼린저 밴드 매매 - 비교 오버레이 (일봉+5분봉)

ParkChartVisualizer(park.py)의 일봉/5분봉 가격 패널에
박병창과 볼린저 두 방식의 매매 신호를 나란히 표시해 비교한다.

표시 요소:
    [박병창]  ▲ 매수(분홍) / ▼ 매도(파랑)   - 캔들 아래/위
    [볼린저]  ● 매수(청록) / ○ 매도(주황)   - 박병창 마커보다 안쪽
    50% 룰선 - 박병창 직전 봉 50% 지지/저항
    비교 배지 - 두 방식 현재 판정 나란히 + 일치/불일치 표시

핵심 비교 포인트:
    같은 봉에서 박병창 매수 ↔ 볼린저(평균회귀) 매도처럼 '반대 신호'가
    나는 지점이 두 철학의 차이를 드러낸다 (추세추종 vs 평균회귀).
    배지에서 이를 강조한다.
"""

from __future__ import annotations

from typing import Callable, Optional

import numpy as np
import pandas as pd

from ta_trader.park.rules.ma_position_rule import MABuyRule, MASellRule, ensure_ma, classify_ma_zone
from ta_trader.park.rules.fifty_percent_rule import (
    FiftyPercentRule, FiftyRuleType,
    RuleAction, MAZone,
)
from ta_trader.park.rules.core import CoreRuleEngine
from ta_trader.park.rules.bollinger_rule import BollingerRule, BollingerMode


# ── 색상 ───────────────────────────────────────────────
C_PARK_BUY = "#c2185b"     # 박병창 매수 (진분홍)
C_PARK_SELL = "#1565c0"    # 박병창 매도 (파랑)
C_BB_BUY = "#00897b"       # 볼린저 매수 (청록)
C_BB_SELL = "#ef6c00"      # 볼린저 매도 (주황)
C_FIFTY_BULL = "#d81b60"   # 황소50% 지지: 핑크레드 (양봉/매수마커와 구분)
C_FIFTY_BEAR = "#0277bd"   # 곰50% 저항: 진한 하늘색


class ParkBollingerOverlay:
    """박병창 + 볼린저 비교 신호 오버레이."""

    def __init__(self, min_confidence: float = 0.55,
                 bb_mode: BollingerMode = BollingerMode.MEAN_REVERSION,
                 marker_lookback: int = 45,
                 show_fifty_line: bool = True,
                 show_badge: bool = True):
        self.min_conf = min_confidence
        self.lookback = marker_lookback
        self.show_fifty_line = show_fifty_line
        self.show_badge = show_badge

        self.fifty = FiftyPercentRule()
        self.buy_rule = MABuyRule(self.fifty)
        self.sell_rule = MASellRule(self.fifty)
        self.bb = BollingerRule(mode=bb_mode)
        self.bb_mode = bb_mode

    def render(self, ax, df: pd.DataFrame, x: np.ndarray,
               fmt: Callable[[float], str], timeframe: str = "일봉") -> None:
        if len(df) < 20:
            return
        d = ensure_ma(df)

        if self.show_fifty_line:
            self._draw_fifty_line(ax, d, x, fmt)
        self._draw_markers(ax, d, x)
        if self.show_badge:
            self._draw_compare_badge(ax, d, fmt, timeframe)

    # ── 50% 룰선 ──
    def _draw_fifty_line(self, ax, d, x, fmt) -> None:
        try:
            res = self.fifty.evaluate(d)
        except (ValueError, KeyError):
            return
        if res.rule_type == FiftyRuleType.NONE:
            return
        is_bull = res.rule_type == FiftyRuleType.BULL
        color = C_FIFTY_BULL if is_bull else C_FIFTY_BEAR
        label = "황소50%(지지)" if is_bull else "곰50%(저항)"
        x0 = x[max(0, len(x) - max(8, len(x) // 3))]
        #print(res, x0, x)
        ax.hlines(res.midpoint, x0, x[-1], color=color, lw=1.2, ls="--",
                  alpha=0.8, zorder=5)
        ax.annotate(f"{label} {fmt(res.midpoint)}",
                    xy=(x[-3], res.midpoint), xytext=(-2, 3),
                    textcoords="offset points", ha="right", va="bottom",
                    fontsize=7, color=color, fontweight="bold", zorder=6)

    # ── 두 방식 마커 (전환점에만) ──
    def _draw_markers(self, ax, d, x) -> None:
        n = len(d)
        start = max(20, n - self.lookback)
        hi = d["High"].to_numpy(float) if "High" in d else d["Close"].to_numpy(float)
        lo = d["Low"].to_numpy(float) if "Low" in d else d["Close"].to_numpy(float)
        span = float(np.nanmax(hi) - np.nanmin(lo))
        off1 = span * 0.02    # 박병창 (바깥)
        off2 = span * 0.06    # 볼린저 (더 바깥)

        pk_buy, pk_sell = ([], []), ([], [])
        bb_buy, bb_sell = ([], []), ([], [])
        pp_b = pp_s = pb_b = pb_s = False
        for i in range(start, n):
            sub = d.iloc[:i + 1]
            try:
                pbsig = self.buy_rule.evaluate(sub)
                pssig = self.sell_rule.evaluate(sub)
                bbb = self.bb.evaluate_buy(sub)
                bbs = self.bb.evaluate_sell(sub)
            except (ValueError, KeyError):
                continue
            # 박병창
            is_pb = pbsig.action == RuleAction.BUY and pbsig.confidence >= self.min_conf
            is_ps = pssig.action == RuleAction.SELL and pssig.confidence >= self.min_conf
            if is_pb and not pp_b:
                pk_buy[0].append(x[i]); pk_buy[1].append(lo[i] - off1)
            if is_ps and not pp_s:
                pk_sell[0].append(x[i]); pk_sell[1].append(hi[i] + off1)
            pp_b, pp_s = is_pb, is_ps
            # 볼린저
            is_bb = bbb.action == RuleAction.BUY and bbb.confidence >= self.min_conf
            is_bs = bbs.action == RuleAction.SELL and bbs.confidence >= self.min_conf
            if is_bb and not pb_b:
                bb_buy[0].append(x[i]); bb_buy[1].append(lo[i] - off2)
            if is_bs and not pb_s:
                bb_sell[0].append(x[i]); bb_sell[1].append(hi[i] + off2)
            pb_b, pb_s = is_bb, is_bs

        # 박병창 (삼각형)
        if pk_buy[0]:
            ax.scatter(*pk_buy, marker="^", s=70, color=C_PARK_BUY,
                       edgecolors="white", linewidths=0.6, zorder=9, label="박병창 매수")
        if pk_sell[0]:
            ax.scatter(*pk_sell, marker="v", s=70, color=C_PARK_SELL,
                       edgecolors="white", linewidths=0.6, zorder=9, label="박병창 매도")
        # 볼린저 (원형)
        if bb_buy[0]:
            ax.scatter(*bb_buy, marker="o", s=42, color=C_BB_BUY,
                       edgecolors="white", linewidths=0.6, zorder=9,
                       label=f"볼린저({self.bb_mode.value}) 매수")
        if bb_sell[0]:
            ax.scatter(*bb_sell, marker="o", s=42, color=C_BB_SELL,
                       edgecolors="white", linewidths=0.6, zorder=9,
                       label=f"볼린저({self.bb_mode.value}) 매도")

    # ── 비교 배지 ──
    def _draw_compare_badge(self, ax, d, fmt, timeframe) -> None:
        try:
            pb = self.buy_rule.evaluate(d)
            ps = self.sell_rule.evaluate(d)
            bb_b = self.bb.evaluate_buy(d)
            bb_s = self.bb.evaluate_sell(d)
            # 밴드타기 모드도 함께 (대비용)
            bb_ride = BollingerRule(mode=BollingerMode.BAND_RIDING)
            br_b = bb_ride.evaluate_buy(d)
            br_s = bb_ride.evaluate_sell(d)
        except (ValueError, KeyError):
            return

        curr = d.iloc[-1]
        price = float(curr["Close"])
        ma5, ma20 = float(curr["ma5"]), float(curr["ma20"])
        zone = classify_ma_zone(price, ma5, ma20)
        zone_label = {MAZone.ABOVE_MA5: "5일선 위",
                      MAZone.BETWEEN_MA5_MA20: "5-20일선 사이",
                      MAZone.BELOW_MA20: "20일선 아래"}[zone]

        park_concl = self._conclude(pb, ps)
        mr_concl = self._conclude(bb_b, bb_s)       # 평균회귀
        ride_concl = self._conclude(br_b, br_s)     # 밴드타기

        # 박병창 vs 볼린저 평균회귀 일치 여부
        def agree_mark(a, b):
            if a == b:
                return "[O] 일치"
            if ("매수" in a and "매도" in b) or ("매도" in a and "매수" in b):
                return "[X] 정반대"
            return "[~] 부분"

        lines = [
            f"[{timeframe}] 구간: {zone_label}",
            "─────────────────",
            f"박병창:        {park_concl[0]} ({park_concl[1]:.2f})",
            f"볼린저 평균회귀: {mr_concl[0]} ({mr_concl[1]:.2f})  {agree_mark(park_concl[0], mr_concl[0])}",
            f"볼린저 밴드타기: {ride_concl[0]} ({ride_concl[1]:.2f})  {agree_mark(park_concl[0], ride_concl[0])}",
        ]
        # 평균회귀와 정반대면 빨강 강조
        amark = agree_mark(park_concl[0], mr_concl[0])
        edge = "#c62828" if "정반대" in amark else ("#2e7d32" if "일치" in amark else "#666")
        ax.text(0.013, 0.62, "\n".join(lines),
                transform=ax.transAxes, fontsize=7, va="top", ha="left",
                bbox=dict(boxstyle="round,pad=0.4", facecolor="white",
                          edgecolor=edge, alpha=0.93, linewidth=1.4),
                zorder=10)

    @staticmethod
    def _conclude(buy_sig, sell_sig) -> tuple[str, float]:
        """매수/매도 신호 중 강한 쪽으로 결론."""
        b = buy_sig.confidence if buy_sig.action == RuleAction.BUY else 0.0
        s = sell_sig.confidence if sell_sig.action == RuleAction.SELL else 0.0
        if b == 0 and s == 0:
            return "관망", max(buy_sig.confidence, sell_sig.confidence)
        return ("매수", b) if b >= s else ("매도", s)


# ─────────────────────────────────────────────────────────────
# ParkChartVisualizer에 비침투로 붙이기
# ─────────────────────────────────────────────────────────────
def attach_park_bollinger(
    visualizer,
    result,
    df_daily: pd.DataFrame,
    df_5min: pd.DataFrame,
    save_path: Optional[str] = None,
    show: bool = False,
    overlay: Optional[ParkBollingerOverlay] = None,
) -> None:
    """일봉+5분봉 차트에 박병창 vs 볼린저 비교 신호 오버레이."""
    ov = overlay or ParkBollingerOverlay()
    original = visualizer._plot_price

    def wrapped(ax, df, result_, x, fmt_, has_ohlc, title="..."):
        original(ax, df, result_, x, fmt_, has_ohlc, title=title)
        tf = "5분봉" if "5분" in title else "일봉"
        ov.render(ax, df, x, fmt_, timeframe=tf)
        # 비교 마커 범례 (좌하단)
        h2, l2 = ax.get_legend_handles_labels()
        sig_h = [(h, l) for h, l in zip(h2, l2)
                 if "박병창" in l or "볼린저" in l]
        if sig_h:
            ax.legend([h for h, _ in sig_h], [l for _, l in sig_h],
                      loc="lower right", fontsize=6.5, framealpha=0.9, ncol=2)

    visualizer._plot_price = wrapped
    try:
        visualizer.plot(result, df_daily, df_5min, save_path=save_path, show=show)
    finally:
        visualizer._plot_price = original