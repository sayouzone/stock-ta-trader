"""
ta_trader/visualization/chart.py
5패널 기술적 분석 차트 시각화
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import matplotlib.gridspec as gridspec
import matplotlib.pyplot as plt
import pandas as pd

from ta_trader.constants import ADX_STRONG_TREND, ADX_WEAK_TREND, RSI_OVERBOUGHT, RSI_OVERSOLD
from ta_trader.models import TradingDecision
from ta_trader.utils.font import setup_korean_font

class ChartVisualizer:
    """ADX·MACD·RSI·Bollinger Bands + 복합 점수 5패널 차트"""

    def plot(
        self,
        decision: TradingDecision,
        df: pd.DataFrame,
        save_path: Optional[str | Path] = None,
        show: bool = True,
    ) -> None:
        """
        Args:
            decision:  분석 결과
            df:        지표가 계산된 DataFrame
            save_path: PNG 저장 경로 (None이면 저장 안 함)
            show:      plt.show() 호출 여부
        """
        setup_korean_font()   # plt 임포트 직후 1회 호출

        fig = plt.figure(figsize=(16, 14))
        fig.suptitle(
            f"{decision.ticker} ({decision.name})  |  {decision.date}  |  "
            f"{decision.final_signal.value}  (Score: {decision.composite_score:+.1f})",
            fontsize=14,
            fontweight="bold",
        )
        
        height_ratios = [3, 1, 1, 1, 1]
        gs = gridspec.GridSpec(5, 1, figure=fig, hspace=0.45, height_ratios=height_ratios)

        self._plot_price(fig.add_subplot(gs[0]), df, decision)
        self._plot_macd(fig.add_subplot(gs[1]), df)
        self._plot_rsi(fig.add_subplot(gs[2]), df)
        self._plot_adx(fig.add_subplot(gs[3]), df)
        self._plot_score(fig.add_subplot(gs[4]), decision)

        plt.tight_layout()
        if save_path:
            Path(save_path).parent.mkdir(parents=True, exist_ok=True)
            plt.savefig(save_path, dpi=150, bbox_inches="tight")
        if show:
            plt.show()
        plt.close(fig)

    # ── 개별 패널 ────────────────────────────────────────

    @staticmethod
    def _plot_price(ax, df: pd.DataFrame, decision: TradingDecision) -> None:
        ax.plot(df.index, df["Close"],     label="Close",     color="black", linewidth=1.2)
        ax.plot(df.index, df["bb_upper"],  label="BB Upper",  color="red",   linestyle="--", alpha=0.6)
        ax.plot(df.index, df["bb_middle"], label="BB Middle",  color="blue",  linestyle="--", alpha=0.6)
        ax.plot(df.index, df["bb_lower"],  label="BB Lower",  color="green", linestyle="--", alpha=0.6)
        ax.fill_between(df.index, df["bb_lower"], df["bb_upper"], alpha=0.05, color="blue")
        if decision.stop_loss:
            ax.axhline(decision.stop_loss,   color="red",   linewidth=0.8, linestyle=":", label=f"SL {decision.stop_loss:,.0f}")
        if decision.take_profit:
            ax.axhline(decision.take_profit, color="green", linewidth=0.8, linestyle=":", label=f"TP {decision.take_profit:,.0f}")
        ax.set_title("Price + Bollinger Bands")
        ax.legend(loc="upper left", fontsize=7)

    @staticmethod
    def _plot_macd(ax, df: pd.DataFrame) -> None:
        ax.plot(df.index, df["macd"],        label="MACD",   color="blue")
        ax.plot(df.index, df["macd_signal"], label="Signal", color="orange")
        colors = ["green" if v >= 0 else "red" for v in df["macd_diff"]]
        ax.bar(df.index, df["macd_diff"], color=colors, alpha=0.4, label="Histogram")
        ax.axhline(0, color="black", linewidth=0.5)
        ax.set_title("MACD")
        ax.legend(loc="upper left", fontsize=7)

    @staticmethod
    def _plot_rsi(ax, df: pd.DataFrame) -> None:
        ax.plot(df.index, df["rsi"], color="purple", label="RSI")
        ax.axhline(RSI_OVERBOUGHT, color="red",   linestyle="--", alpha=0.7, label=f"과매수 {RSI_OVERBOUGHT:.0f}")
        ax.axhline(RSI_OVERSOLD,   color="green", linestyle="--", alpha=0.7, label=f"과매도 {RSI_OVERSOLD:.0f}")
        ax.fill_between(df.index, RSI_OVERSOLD, df["rsi"],
                        where=df["rsi"] <= RSI_OVERSOLD, alpha=0.25, color="green")
        ax.fill_between(df.index, df["rsi"], RSI_OVERBOUGHT,
                        where=df["rsi"] >= RSI_OVERBOUGHT, alpha=0.25, color="red")
        ax.set_ylim(0, 100)
        ax.set_title("RSI")
        ax.legend(loc="upper left", fontsize=7)

    @staticmethod
    def _plot_adx(ax, df: pd.DataFrame) -> None:
        ax.plot(df.index, df["adx"],     label="ADX",  color="black", linewidth=1.5)
        ax.plot(df.index, df["adx_pos"], label="+DI",  color="green")
        ax.plot(df.index, df["adx_neg"], label="-DI",  color="red")
        ax.axhline(ADX_STRONG_TREND, color="orange", linestyle="--", alpha=0.7, label=f"강한추세 {ADX_STRONG_TREND:.0f}")
        ax.axhline(ADX_WEAK_TREND,   color="gray",   linestyle="--", alpha=0.7, label=f"약한추세 {ADX_WEAK_TREND:.0f}")
        ax.set_title("ADX (+DI / -DI)")
        ax.legend(loc="upper left", fontsize=7)

    @staticmethod
    def _plot_score(ax, decision: TradingDecision) -> None:
        ax.axhline(0,    color="black",      linewidth=0.5)
        ax.axhline(60,   color="green",      linestyle="--", alpha=0.5, label="강력매수 60")
        ax.axhline(-60,  color="red",        linestyle="--", alpha=0.5, label="강력매도 -60")
        ax.axhline(20,   color="lightgreen", linestyle=":",  alpha=0.5, label="매수 20")
        ax.axhline(-20,  color="lightcoral", linestyle=":",  alpha=0.5, label="매도 -20")
        ax.scatter(
            [0], [decision.composite_score],
            color="blue", s=120, zorder=5,
            label=f"현재 점수: {decision.composite_score:+.1f}",
        )
        ax.set_xlim(-0.5, 0.5)
        ax.set_ylim(-110, 110)
        ax.set_title("Composite Score")
        ax.legend(loc="upper right", fontsize=7)
