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
from ta_trader.visualization.park_bollinger_overlay import ParkBollingerOverlay

# ── 색상 상수 (한국 HTS 관례) ──────────────────────────────
COLOR_UP = "#d92b2b"     # 양봉 (종가 ≥ 시가)
COLOR_DOWN = "#1f63d6"   # 음봉 (종가 < 시가)
COLOR_FULL_EXIT_PRICE = "#00838f"     # 전량익절: 진한 청록 (최상단 목표)
COLOR_PARTIAL_EXIT_PRICE = "#558b2f"  # 부분익절: 올리브그린 (중간 목표)
COLOR_STOP_LOSS = "#e65100"           # 손절: 진한 주황
COLOR_TRAILING_STOP = "#6a1b9a"       # 트레일링 스톱: 보라 (양봉 빨강과 구분)

# 이동평균선 (기간, 색상, 두께)
MA_SPECS = [
    (5, "#e8453c", 0.9),
    (20, "#f0a020", 0.9),
    #(60, "#1f9d55", 0.9),
    #(120, "#8a6d3b", 0.9),
]

CANDLE_WIDTH = 0.62


class ParkChartVisualizer:
    """Price(캔들+BB+MA+Volume) + MACD·RSI·ADX 4패널 차트"""

    def plot(
        self,
        result: SwingAnalysisResult,
        df_daily: pd.DataFrame,
        df_5min: pd.DataFrame,
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

        # df_daily: 4개월 일봉 → 최근 3개월만 표시 (지표는 4개월 기준으로 계산된 값 그대로 사용)
        cutoff = df_daily.index.max() - pd.DateOffset(months=3)
        df_daily = df_daily.loc[df_daily.index >= cutoff]

        #cutoff = df_5min.index.max() - pd.DateOffset(days=3)
        #df_5min = df_5min.loc[df_5min.index >= cutoff]

        has_ohlc = all(c in df_daily.columns for c in ("Open", "High", "Low"))
        has_ohlc1 = all(c in df_5min.columns for c in ("Open", "High", "Low"))   # ← 5분봉용 별도 판정
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
            y=0.945,   # 타이틀을 아래로 내려 첫 패널과의 간격 축소
        )

        # 4행: [가격(+거래량)] / MACD / RSI / ADX
        # top을 0.91로 올려(타이틀 바로 아래) 타이틀-패널 간격을 좁힘
        # left/right로 차트 좌우 마진 확대
        gs = gridspec.GridSpec(2, 1, figure=fig, hspace=0.08, height_ratios=[3, 3],
                               top=0.90, bottom=0.05, left=0.10, right=0.90)
        ax_p = fig.add_subplot(gs[0])               # 일봉, 가격 (캔들+BB+MA)
        ax_v = ax_p.twinx()                         # 거래량 (하단 겹침)
        ax_5min_p = fig.add_subplot(gs[1])          # 5분봉
        ax_5min_v = ax_5min_p.twinx()

        x = np.arange(len(df_daily))
        x1 = np.arange(len(df_5min))      # ← 5분봉 x (별도)

        # 거래량을 먼저 그리고 가격을 위에 올린다 (twin 축은 axes zorder로 앞뒤 결정)
        self._plot_volume(ax_v, df_daily, x, has_ohlc, is_5min=False)
        #self._plot_price(ax_p, df_daily, result, x, fmt, has_ohlc,
        #                title="3개월 일봉 — Price + BB + MA + Volume")
        self._plot_park_overlay(ax_p, df_daily, result, x, fmt, has_ohlc, is_5min=False, 
                                title="3개월 일봉 — Price + BB + MA + Volume")
        ax_p.set_zorder(ax_v.get_zorder() + 1)
        ax_p.patch.set_visible(False)               # 가격 축 배경 투명 → 뒤의 거래량이 보임
        self._format_xaxis_weekly(ax_p, df_daily, x)      # 날짜 표시

        # 하단: 5일 5분봉
        self._plot_volume(ax_5min_v, df_5min, x1, has_ohlc1, is_5min=True)
        self._plot_price(ax_5min_p, df_5min, result, x1, fmt, has_ohlc1, is_5min=True, 
                        title="5일 5분봉 — Price + BB + MA + Volume")
        #self._plot_park_overlay(ax_5min_p, df_5min, result, x1, fmt, has_ohlc1,
        #                        title="5일 5분봉 — Price + BB + MA + Volume")
        ax_5min_p.set_zorder(ax_5min_v.get_zorder() + 1)
        ax_5min_p.patch.set_visible(False)
        self._format_xaxis_intraday(ax_5min_p, df_5min, x1)   # 날짜 표시

        if save_path:
            Path(save_path).parent.mkdir(parents=True, exist_ok=True)
            fig.savefig(save_path, dpi=150, bbox_inches="tight")
        if show:
            plt.show()
        plt.close(fig)

    # ── 가격 패널 ─────────────────────────────────────────
    def _plot_price(self, ax, df, result, x, fmt, has_ohlc, is_5min=True,
                    title="Price + Bollinger Bands + Volume") -> None:
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

        # 최소 날짜와 최대 날짜 구하기
        # 기간이 30일 이상인 경우에만 손절/익절 라인 그리기
        start_date = pd.to_datetime(df.index.min()).date()
        end_date = pd.to_datetime(df.index.max()).date()
        period = int((end_date - start_date).days)

        # 4) 손절/익절 라인 (우측 범례)
        right_handles = []
        es, pos = result.exit_strategy, result.position
        # (값, 색, 선스타일, 이름) — 선스타일도 4종 모두 다르게
        line_specs = [
            (getattr(es, "full_exit_price", None), COLOR_FULL_EXIT_PRICE, (0, (6, 2)), "전량익절"),
            (getattr(es, "partial_exit_price", None), COLOR_PARTIAL_EXIT_PRICE, (0, (1, 1.5)), "부분익절"),
            (getattr(pos, "stop_loss", None), COLOR_STOP_LOSS, (0, (4, 1, 1, 1)), "손절"),
            (getattr(es, "trailing_stop", None), COLOR_TRAILING_STOP, (0, (3, 1, 1, 1, 1, 1)), "트레일링 스톱"),
        ]
        
        if not is_5min:
            # 유효한 것만, 값 기준 정렬 (라벨 분산 계산용)
            valid = [(v, c, s, nm) for v, c, s, nm in line_specs if v]
            # 라인 먼저 그리기
            for value, color, ls, name in valid:
                ax.hlines(value, 55, x[-1], color=color, lw=1.4, ls=ls, alpha=0.9, zorder=5)

            # 라벨 y위치 분산: 값이 가까우면 텍스트가 겹치므로 최소 간격 확보
            if valid:
                ylo, yhi = ax.get_ylim() if ax.get_ylim()[1] > ax.get_ylim()[0] else (
                    min(v for v, *_ in valid), max(v for v, *_ in valid))
                # set_ylim이 아직 호출 전이므로 데이터 범위로 추정
                span_est = float(df[("High" if has_ohlc else "Close")].max()
                                - df[("Low" if has_ohlc else "Close")].min())
                min_gap = span_est * 0.03   # 라벨 간 최소 세로 간격 (겹칠 때만 분산)
                # 값 큰 것부터 위에서 아래로 배치하며 겹치면 끌어올림
                order = sorted(valid, key=lambda t: t[0], reverse=True)
                label_y = []
                for value, color, ls, name in order:
                    ly = value
                    for prev in label_y:
                        if abs(ly - prev) < min_gap:
                            ly = prev - min_gap   # 아래로 밀기
                    label_y.append(ly)
                for (value, color, ls, name), ly in zip(order, label_y):
                    # 라벨은 라인 우측 끝 안쪽에. 분산된 ly로 겹침 방지.
                    ax.annotate(f"{name}",
                                xy=(x[-5], ly),
                                xytext=(-2, 3), textcoords="offset points",
                                ha="right", va="baseline",                                 # 'top', 'bottom', 'center', 'baseline', 'center_baseline'
                                fontsize=6, color=color, fontweight="normal", zorder=4,
                                bbox=dict(boxstyle="round,pad=0.15", facecolor="white",
                                        edgecolor="none", alpha=0.5))
                    ax.annotate(f"{fmt(value)}",
                                xy=(x[-1], ly),
                                xytext=(-3, 0), textcoords="offset points",
                                ha="right", va="center",
                                fontsize=9, color=color, fontweight="bold", zorder=6,
                                bbox=dict(boxstyle="round,pad=0.15", facecolor="white",
                                        edgecolor="none", alpha=0.9))

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

        # 가격 y축 범위를 인위적으로 확대해 캔들이 차지하는 세로 폭을 줄인다.
        # 데이터의 실제 고저 범위를 구한 뒤, 위아래로 패딩을 크게 부여.
        price_hi = float(df[hi_col].max())
        price_lo = float(df[lo_col].min())
        # 손절/익절 수평선 값 (그려질 때만 범위에 포함 - 아래에서 처리)
        line_vals = [getattr(es, "full_exit_price", None),
                     getattr(es, "partial_exit_price", None),
                     getattr(pos, "stop_loss", None),
                     getattr(es, "trailing_stop", None)]
        line_vals = [v for v in line_vals if v]
        span = price_hi - price_lo
        # 손절/익절선은 실제로 그려질 때(period>30, 일봉)만 범위에 포함.
        # 5분봉은 일봉 손절가가 가격범위 밖이라 포함 시 상단 여백이 과도해짐.
        if period > 30 and line_vals:
            price_hi = max(price_hi, max(line_vals))
            price_lo = min(price_lo, min(line_vals))
            span = price_hi - price_lo
        # 아래 25% / 위 35% 여백 → 캔들이 화면 중앙~상단에 납작하게 모임 (최초)
        # 아래 25% / 위 1% 여백 (5분봉) / 아래 15% / 위 7% (일봉)
        y_low = price_lo - span * (0.25 if is_5min else 0.15)
        y_high = price_hi + span * (0.01 if is_5min else 0.07)
        ax.set_ylim(y_low, y_high)

        # 범례: 좌측(지표) / 우측(손절익절)
        left_handles, left_labels = [], []
        for h, l in zip(*ax.get_legend_handles_labels()):
            if h not in right_handles:
                left_handles.append(h); left_labels.append(l)
        ax.add_artist(ax.legend(left_handles, left_labels, loc="upper left", fontsize=7, ncol=2, framealpha=0.9))
        if period > 30 and right_handles:
            ax.legend(right_handles, [h.get_label() for h in right_handles],
                      loc="upper right", fontsize=7, framealpha=0.9)

        ax.set_title(title, fontsize=11, pad=4)

    def _plot_park_overlay(self, ax, df, result, x, fmt, has_ohlc, is_5min=True, title="...") -> None:
        ov = ParkBollingerOverlay()

        self._plot_price(ax, df, result, x, fmt, has_ohlc, is_5min=is_5min, title=title)
        tf = "5분봉" if "5분" in title else "일봉"
        ov.render(ax, df, x, fmt, timeframe=tf)
        # 비교 마커 범례 (좌하단)
        h2, l2 = ax.get_legend_handles_labels()
        sig_h = [(h, l) for h, l in zip(h2, l2)
                 if "박병창" in l or "볼린저" in l]
        if sig_h:
            # 좌측 중앙 배지(y≈0.62~) 바로 아래에 좌측 정렬로 배치
            ax.legend([h for h, _ in sig_h], [l for _, l in sig_h],
                    loc="upper left", bbox_to_anchor=(0.013, 0.50),
                    fontsize=6.5, framealpha=0.9, ncol=1)
            ## 5분봉: 우하단 유지
            #ax.legend([h for h, _ in sig_h], [l for _, l in sig_h],
            #            loc="lower right", fontsize=6.5, framealpha=0.9, ncol=2)

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
    def _plot_volume(ax, df, x, has_ohlc, is_5min=True) -> None:
        if has_ohlc:
            up = df["Close"].to_numpy(float) >= df["Open"].to_numpy(float)
        else:
            up = df["Close"].diff().fillna(0).to_numpy(float) >= 0
        colors = np.where(up, COLOR_UP, COLOR_DOWN)
        ax.bar(x, df["Volume"].to_numpy(float), color=colors, width=CANDLE_WIDTH, alpha=0.45, zorder=0)

        # 거래량 막대가 화면 하단 ~12.5%에만 머물도록 y범위 확대 (* 8.0) / ~25% (* 4.0)
        vmax = float(df["Volume"].max())
        ax.set_ylim(0, vmax * (4.0 if is_5min else 8.0))

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
        # 좌우 마진 확대: 양쪽에 전체 길이의 3%씩 여백
        pad = max(2, len(df) * 0.03)
        ax.set_xlim(-pad, len(df) - 1 + pad)

    # ── 일봉 x축 (일주일 단위 날짜 라벨 + 주간 세로 구분선) ──────
    @staticmethod
    def _format_xaxis_weekly(ax, df, x) -> None:
        idx = pd.to_datetime(df.index)
        week = idx.to_period("W")        # 주 단위로 묶기 (월~일)
        ticks, labels, prev = [], [], None
        for i in range(len(idx)):
            w = week[i]
            if w != prev:                # 새로운 주의 첫 거래일
                ticks.append(i)
                labels.append(idx[i].strftime("%m-%d"))
                ax.axvline(i, color="#d0d0d0", ls="-", lw=0.6, alpha=0.5, zorder=1)
                prev = w
        ax.set_xticks(ticks)
        ax.set_xticklabels(labels, rotation=0, fontsize=8)
        pad = max(2, len(df) * 0.02)
        ax.set_xlim(-pad, len(df) - 1 + pad)

    # ── 5분봉 x축 (매일 날짜 라벨 + 일별 세로 구분선) ──────────
    @staticmethod
    def _format_xaxis_intraday(ax, df, x) -> None:
        idx = pd.to_datetime(df.index)
        day = idx.normalize()           # 날짜 부분만 (시:분 제거)
        ticks, labels, prev = [], [], None
        for i in range(len(idx)):
            d = day[i]
            if d != prev:               # 날(day)이 바뀌는 첫 봉
                ticks.append(i)
                labels.append(idx[i].strftime("%m-%d"))
                # 일별 경계 세로선 (전체 높이)
                ax.axvline(i, color="#b0b0b0", ls="-", lw=0.7, alpha=0.6, zorder=1)
                prev = d
        ax.set_xticks(ticks)
        ax.set_xticklabels(labels, rotation=0, fontsize=8)
        pad = max(2, len(df) * 0.01)
        ax.set_xlim(-pad, len(df) - 1 + pad)