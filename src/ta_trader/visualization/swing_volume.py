"""
ta_trader/visualization/swing_volume.py
Price + Bollinger Bands + Volume 통합 + MACD / RSI / ADX 4패널 차트

특징
- 한국 HTS 관례: 양봉=빨강, 음봉=파랑
- 상단: 캔들스틱 + 볼린저밴드 + 이동평균선(5/20/60/120) + 거래량 하단 겹침
- 하단: MACD / RSI / ADX 보조지표 패널 (가격 패널과 x축 공유)
- 가격축 우측 표시, 최고/최저 주석, 월별 날짜 라벨, 주말 갭 제거(연속 위치축)
- OHLC 컬럼이 없으면 종가 라인으로 자동 폴백
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import matplotlib.gridspec as gridspec
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.collections import LineCollection
from matplotlib.patches import Rectangle

from ta_trader.constants.short import ADX_STRONG_TREND, ADX_WEAK_TREND, RSI_OVERBOUGHT, RSI_OVERSOLD
from ta_trader.models.swing import SwingAnalysisResult
from ta_trader.utils.font import setup_korean_font

# ── 색상 상수 (한국 HTS 관례) ──────────────────────────────
COLOR_UP = "#d92b2b"     # 양봉 (종가 ≥ 시가)
COLOR_DOWN = "#1f63d6"   # 음봉 (종가 < 시가)

# 이동평균선 (기간, 색상, 두께)
MA_SPECS = [
    (5, "#e8453c", 0.9),
    (20, "#f0a020", 0.9),
    #(60, "#1f9d55", 0.9),
    #(120, "#8a6d3b", 0.9),
]

CANDLE_WIDTH = 0.62


class SwingVolumeChartVisualizer:
    """Price(캔들+BB+MA+Volume) + MACD·RSI·ADX 4패널 차트"""

    def plot(
        self,
        result: SwingAnalysisResult,
        df: pd.DataFrame,
        save_path: Optional[str | Path] = None,
        show: bool = True,
    ) -> None:
        """
        Args:
            result:    분석 결과
            df:        지표가 계산된 DataFrame
            save_path: PNG 저장 경로 (None이면 저장 안 함)
            show:      plt.show() 호출 여부
        """
        setup_korean_font()   # plt 임포트 직후 1회 호출

        has_ohlc = all(c in df.columns for c in ("Open", "High", "Low"))
        is_kr = ".K" in result.ticker
        fmt = (lambda v: f"{v:,.0f}") if is_kr else (lambda v: f"{v:,.2f}")

        fig = plt.figure(figsize=(16, 16))
        fig.suptitle(
            f"{result.trading_style.value}: {result.ticker} ({result.name})  |  {result.date}  |  "
            f"Price: {fmt(result.current_price)}  |  "
            f"{result.overall_signal.value} ({result.market_env.environment.value})  |  "
            f"Grade: {result.screening.grade.value}, Score: {result.overall_score:+.1f}",
            fontsize=13,
            fontweight="bold",
        )

        # 4행: [가격(+거래량)] / MACD / RSI / ADX
        gs = gridspec.GridSpec(4, 1, figure=fig, hspace=0.38, height_ratios=[3, 1, 1, 1])
        ax_p = fig.add_subplot(gs[0])               # 가격 (캔들+BB+MA)
        ax_v = ax_p.twinx()                         # 거래량 (하단 겹침)
        ax_macd = fig.add_subplot(gs[1], sharex=ax_p)
        ax_rsi = fig.add_subplot(gs[2], sharex=ax_p)
        ax_adx = fig.add_subplot(gs[3], sharex=ax_p)

        x = np.arange(len(df))

        # 거래량을 먼저 그리고 가격을 위에 올린다 (twin 축은 axes zorder로 앞뒤 결정)
        self._plot_volume(ax_v, df, x, has_ohlc)
        self._plot_price(ax_p, df, result, x, fmt, has_ohlc)
        ax_p.set_zorder(ax_v.get_zorder() + 1)
        ax_p.patch.set_visible(False)               # 가격 축 배경 투명 → 뒤의 거래량이 보임

        # 보조지표 패널
        self._plot_macd(ax_macd, df, x)
        self._plot_rsi(ax_rsi, df, x)
        self._plot_adx(ax_adx, df, x)

        # 각 패널 x축 모두에 년-월 라벨 출력
        for a in (ax_p, ax_macd, ax_rsi, ax_adx):
            self._format_xaxis(a, df, x)

        if save_path:
            Path(save_path).parent.mkdir(parents=True, exist_ok=True)
            fig.savefig(save_path, dpi=150, bbox_inches="tight")
        if show:
            plt.show()
        plt.close(fig)

    # ── 가격 패널 ─────────────────────────────────────────
    def _plot_price(self, ax, df, result, x, fmt, has_ohlc) -> None:
        # 1) 볼린저밴드 (캔들 배경)
        ax.plot(x, df["bb_upper"], color="#e57373", lw=0.9, ls="--", alpha=0.7, label="BB Upper", zorder=1)
        ax.plot(x, df["bb_middle"], color="#5c6bc0", lw=0.9, ls="--", alpha=0.7, label="BB Mid", zorder=1)
        ax.plot(x, df["bb_lower"], color="#66bb6a", lw=0.9, ls="--", alpha=0.7, label="BB Lower", zorder=1)
        ax.fill_between(x, df["bb_lower"], df["bb_upper"], color="#7986cb", alpha=0.06, zorder=0)

        # 2) 이동평균선 (없으면 종가에서 계산)
        for period, color, lw in MA_SPECS:
            col = f"ma{period}"
            ma = df[col] if col in df.columns else df["Close"].rolling(period).mean()
            ax.plot(x, ma, color=color, lw=lw, alpha=0.9, label=f"MA{period}", zorder=2)

        # 3) 캔들 또는 종가선
        if has_ohlc:
            self._draw_candles(ax, df, x)
        else:
            ax.plot(x, df["Close"], color="black", lw=1.2, label="Close", zorder=3)

        # 4) 손절/익절 라인 (우측 범례)
        right_handles = []
        es, pos = result.exit_strategy, result.position
        for value, color, ls, name in (
            (getattr(es, "full_exit_price", None), "#1565c0", "--", "전량익절"),
            (getattr(es, "partial_exit_price", None), "#2e7d32", ":", "부분익절"),
            (getattr(pos, "stop_loss", None), "#ef6c00", ":", "손절"),
            (getattr(es, "trailing_stop", None), "#c62828", "--", "트레일링 스톱"),
        ):
            if value:
                ln = ax.axhline(value, color=color, lw=0.9, ls=ls, label=f"{name} {fmt(value)}", zorder=4)
                right_handles.append(ln)

        # 5) 최고/최저 주석 (HTS 스타일)
        hi_col, lo_col = ("High", "Low") if has_ohlc else ("Close", "Close")
        hi_i = int(np.argmax(df[hi_col].values)); hi_v = df[hi_col].values[hi_i]
        lo_i = int(np.argmin(df[lo_col].values)); lo_v = df[lo_col].values[lo_i]
        ax.annotate(f"최고 {fmt(hi_v)}", xy=(hi_i, hi_v), xytext=(0, 12), textcoords="offset points",
                    ha="center", fontsize=8, color="#c62828",
                    arrowprops=dict(arrowstyle="->", color="#c62828", lw=0.8))
        ax.annotate(f"최저 {fmt(lo_v)}", xy=(lo_i, lo_v), xytext=(0, -16), textcoords="offset points",
                    ha="center", fontsize=8, color="#1565c0",
                    arrowprops=dict(arrowstyle="->", color="#1565c0", lw=0.8))

        # 우측 가격축
        ax.yaxis.tick_right()
        ax.yaxis.set_label_position("right")
        ax.grid(True, axis="y", ls=":", alpha=0.3)
        ax.margins(x=0.01)

        # 범례: 좌측(지표) / 우측(손절익절)
        left_handles, left_labels = [], []
        for h, l in zip(*ax.get_legend_handles_labels()):
            if h not in right_handles:
                left_handles.append(h); left_labels.append(l)
        ax.add_artist(ax.legend(left_handles, left_labels, loc="upper left", fontsize=7, ncol=2, framealpha=0.9))
        if right_handles:
            ax.legend(right_handles, [h.get_label() for h in right_handles],
                      loc="upper right", fontsize=7, framealpha=0.9)

        ax.set_title("Price + Bollinger Bands + Volume", fontsize=11, pad=8)

    @staticmethod
    def _draw_candles(ax, df, x) -> None:
        o = df["Open"].to_numpy(float)
        h = df["High"].to_numpy(float)
        l = df["Low"].to_numpy(float)
        c = df["Close"].to_numpy(float)
        up = c >= o

        # 심지(wick) - LineCollection 일괄 처리
        segs = [((xi, lo), (xi, hi)) for xi, lo, hi in zip(x, l, h)]
        wcolors = [COLOR_UP if u else COLOR_DOWN for u in up]
        ax.add_collection(LineCollection(segs, colors=wcolors, linewidths=0.7, zorder=3))

        # 몸통(body)
        w = CANDLE_WIDTH
        for xi, oi, ci, u in zip(x, o, c, up):
            color = COLOR_UP if u else COLOR_DOWN
            height = abs(ci - oi)
            if height == 0:  # 도지
                ax.plot([xi - w / 2, xi + w / 2], [ci, ci], color=color, lw=0.8, zorder=4)
            else:
                ax.add_patch(Rectangle((xi - w / 2, min(oi, ci)), w, height,
                                       facecolor=color, edgecolor=color, linewidth=0.4, zorder=4))

    # ── 거래량 (가격 차트 하단에 겹쳐 그리기) ───────────────
    @staticmethod
    def _plot_volume(ax, df, x, has_ohlc) -> None:
        if has_ohlc:
            up = df["Close"].to_numpy(float) >= df["Open"].to_numpy(float)
        else:
            up = df["Close"].diff().fillna(0).to_numpy(float) >= 0
        colors = np.where(up, COLOR_UP, COLOR_DOWN)
        ax.bar(x, df["Volume"].to_numpy(float), color=colors, width=CANDLE_WIDTH, alpha=0.45, zorder=0)

        # 거래량 막대가 화면 하단 ~12.5%에만 머물도록 y범위 확대 (* 8.0) / ~25% (* 4.0)
        vmax = float(df["Volume"].max())
        ax.set_ylim(0, vmax * 8.0)

        # 거래량 축은 왼쪽에 옅게 (가격 축은 오른쪽)
        ax.yaxis.tick_left()
        ax.yaxis.set_label_position("left")
        ax.tick_params(axis="y", labelsize=7, colors="#888")
        ax.margins(x=0.01)

    # ── MACD 패널 ─────────────────────────────────────────
    @staticmethod
    def _plot_macd(ax, df, x) -> None:
        ax.plot(x, df["macd"], label="MACD", color="blue", lw=1.0)
        ax.plot(x, df["macd_signal"], label="Signal", color="orange", lw=1.0)
        colors = ["green" if v >= 0 else "red" for v in df["macd_diff"]]
        ax.bar(x, df["macd_diff"], color=colors, alpha=0.4, width=CANDLE_WIDTH, label="Histogram")
        ax.axhline(0, color="black", linewidth=0.5)
        ax.set_title("MACD", fontsize=10, pad=4)
        ax.legend(loc="upper left", fontsize=7)
        ax.yaxis.tick_right()
        ax.yaxis.set_label_position("right")
        ax.grid(True, axis="y", ls=":", alpha=0.3)
        ax.margins(x=0.01)

    # ── RSI 패널 ──────────────────────────────────────────
    @staticmethod
    def _plot_rsi(ax, df, x) -> None:
        rsi = df["rsi"].to_numpy(float)
        ax.plot(x, rsi, color="purple", label="RSI", lw=1.0)
        ax.axhline(RSI_OVERBOUGHT, color="red", linestyle="--", alpha=0.7, label=f"과매수 {RSI_OVERBOUGHT:.0f}")
        ax.axhline(RSI_OVERSOLD, color="green", linestyle="--", alpha=0.7, label=f"과매도 {RSI_OVERSOLD:.0f}")
        ax.fill_between(x, RSI_OVERSOLD, rsi, where=rsi <= RSI_OVERSOLD, alpha=0.25, color="green")
        ax.fill_between(x, rsi, RSI_OVERBOUGHT, where=rsi >= RSI_OVERBOUGHT, alpha=0.25, color="red")
        ax.set_ylim(0, 100)
        ax.set_title("RSI", fontsize=10, pad=4)
        ax.legend(loc="upper left", fontsize=7)
        ax.yaxis.tick_right()
        ax.yaxis.set_label_position("right")
        ax.grid(True, axis="y", ls=":", alpha=0.3)
        ax.margins(x=0.01)

    # ── ADX 패널 ──────────────────────────────────────────
    @staticmethod
    def _plot_adx(ax, df, x) -> None:
        ax.plot(x, df["adx"], label="ADX", color="black", linewidth=1.3)
        ax.plot(x, df["adx_pos"], label="+DI", color="green", lw=1.0)
        ax.plot(x, df["adx_neg"], label="-DI", color="red", lw=1.0)
        ax.axhline(ADX_STRONG_TREND, color="orange", linestyle="--", alpha=0.7, label=f"강한추세 {ADX_STRONG_TREND:.0f}")
        ax.axhline(ADX_WEAK_TREND, color="gray", linestyle="--", alpha=0.7, label=f"약한추세 {ADX_WEAK_TREND:.0f}")
        ax.set_title("ADX (+DI / -DI)", fontsize=10, pad=4)
        ax.legend(loc="upper left", fontsize=7)
        ax.yaxis.tick_right()
        ax.yaxis.set_label_position("right")
        ax.grid(True, axis="y", ls=":", alpha=0.3)
        ax.margins(x=0.01)

    # ── x축 (월별 날짜 라벨, 연속 위치축, 맨 왼쪽 시작 라벨 생략) ──
    @staticmethod
    def _format_xaxis(ax, df, x) -> None:
        idx = df.index
        ticks, labels, prev = [], [], None
        for i in range(len(idx)):
            key = (idx[i].year, idx[i].month)
            if key != prev:
                ticks.append(i)
                labels.append(idx[i].strftime("%Y-%m"))
                prev = key
        # 제일 왼쪽 시작 년-월 라벨은 출력하지 않음
        ticks, labels = ticks[1:], labels[1:]
        ax.set_xticks(ticks)
        ax.set_xticklabels(labels, rotation=0, fontsize=8)
        ax.set_xlim(-1, len(df))