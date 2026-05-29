"""
ta_trader/visualization/park.py
박병창 매매 기법 기반 5패널 차트 시각화

기존 swing.py와의 차이점:
    - BB 대신 5/20/60일 이평선 + 50% 룰선을 메인 패널에 표시
    - MACD/RSI/ADX 패널을 박병창 핵심 요소로 교체:
        * P2: 거래량 + 평균 2배 이상 급증 강조
        * P3: 매물대 (이퀴볼륨) — 가격대별 누적 거래량
        * P4: 박병창 6축 점수 (시간·가격·거래량·움직임·속도·구조)
        * P5: 매수 3원칙 게이지 (현재가의 이평선 위치)

기존 코드와의 호환성:
    - SwingAnalysisResult 인터페이스 그대로 사용
    - setup_korean_font(), .K 가격 포맷, 왼쪽/오른쪽 범례 분리 패턴 유지
    - 박병창 전용 필드(park_signal)는 옵셔널로 추가
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal, Optional

import matplotlib.gridspec as gridspec
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.patches import Rectangle

from ta_trader.models.swing import SwingAnalysisResult
from ta_trader.utils.font import setup_korean_font


# ─────────────────────────────────────────────────────────────
# 박병창 전용 시그널 데이터 (SwingAnalysisResult에 첨부하거나 별도 전달)
# ─────────────────────────────────────────────────────────────
MarketStance = Literal["황소_강세", "황소_눌림", "곰_과매도", "중립"]


@dataclass
class ParkSignal:
    """박병창 매매 기법 평가 결과.

    swing.py의 SwingAnalysisResult와 함께 사용하거나,
    SwingAnalysisResult.park_signal 속성으로 첨부해서 사용.
    """
    stance: MarketStance = "중립"

    # 6축 핵심 개념 점수 (0~100)
    time_score: float = 50.0          # 시간대 (10시 이전, 종가 30분 등)
    price_score: float = 50.0         # 50% 룰, 이평선 위치
    volume_score: float = 50.0        # 거래량 급증
    motion_score: float = 50.0        # 움직임/멈춤 (정체 후 돌파)
    velocity_score: float = 50.0      # 속도 (체결 빈도)
    structure_score: float = 50.0     # 지지/저항/매물대

    # 50% 룰
    fifty_pct_level: float = 0.0
    fifty_pct_rule: Literal["bull", "bear", "none"] = "none"

    # 이평선
    ma5: float = 0.0
    ma20: float = 0.0
    ma60: float = 0.0

    # 매매 체크리스트
    checklist: list[tuple[str, bool]] = field(default_factory=list)

    @property
    def total_score(self) -> float:
        """6축 가중평균 (-100 ~ +100 스케일)"""
        weights = {"time": 0.15, "price": 0.25, "volume": 0.25,
                   "motion": 0.15, "velocity": 0.10, "structure": 0.10}
        avg = (self.time_score * weights["time"]
               + self.price_score * weights["price"]
               + self.volume_score * weights["volume"]
               + self.motion_score * weights["motion"]
               + self.velocity_score * weights["velocity"]
               + self.structure_score * weights["structure"])
        # 0~100 → -100~+100 스케일로 변환
        return (avg - 50.0) * 2.0

    @property
    def ma_position_rule(self) -> int:
        """현재가 위치에 따른 매수 원칙 번호 (price는 외부에서 비교)"""
        return 1 if self.ma5 > self.ma20 else 2  # 외부에서 price 전달 시 재계산


class ParkChartVisualizer:
    """박병창 매매 기법 5패널 차트 (이평선·50%룰·매물대·6축점수·3원칙 게이지)"""

    def plot(
        self,
        result: SwingAnalysisResult,
        df: pd.DataFrame,
        park_signal: Optional[ParkSignal] = None,
        save_path: Optional[str | Path] = None,
        show: bool = True,
    ) -> None:
        """
        Args:
            result:      기존 SwingAnalysisResult (가격, 손절/익절 등 재사용)
            df:          OHLCV + 지표 DataFrame
            park_signal: 박병창 전용 시그널 (없으면 df에서 자동 계산)
            save_path:   PNG 저장 경로
            show:        plt.show() 호출 여부
        """
        setup_korean_font()

        # 박병창 시그널 자동 계산 (전달 안 됐을 때)
        if park_signal is None:
            park_signal = self._auto_compute_signal(df, result)

        fig = plt.figure(figsize=(16, 15))

        # 타이틀
        current_price = (f"{result.current_price:,.0f}" if ".K" in result.ticker
                         else f"{result.current_price:,.2f}")
        rule_no = self._compute_rule_number(result.current_price, park_signal)

        fig.suptitle(
            f"박병창 매매: {result.ticker} ({result.name})  |  {result.date}  |  "
            f"Price: {current_price}  |  "
            f"{result.overall_signal.value} ({result.market_env.environment.value})  |  "
            f"{park_signal.stance}  |  매수 {rule_no}원칙  |  "
            f"Park Score: {park_signal.total_score:+.1f}",
            fontsize=13,
            fontweight="bold",
            y=0.98,
        )

        # GridSpec: 메인(3.5) + 거래량(1) + 매물대(1.3) + 6축(1) + 3원칙게이지(0.9)
        # 우측 여백을 0.82로 두어 게이지 패널의 체크리스트가 잘리지 않도록 함
        height_ratios = [3.5, 1, 1.3, 1, 0.9]
        gs = gridspec.GridSpec(
            5, 1, figure=fig, hspace=0.45, height_ratios=height_ratios,
            left=0.06, right=0.82, top=0.95, bottom=0.04,
        )

        from pandas.tseries.offsets import DateOffset
        cutoff = df.index[-1] - DateOffset(months=3)
        df_view = df.loc[df.index >= cutoff]

        self._plot_price(fig.add_subplot(gs[0]), df, df_view, result, park_signal)
        self._plot_volume(fig.add_subplot(gs[1]), df_view)
        self._plot_volume_profile(fig.add_subplot(gs[2]), df_view, result, park_signal)
        self._plot_six_axis(fig.add_subplot(gs[3]), park_signal)
        self._plot_rule_gauge(fig.add_subplot(gs[4]), result, park_signal)

        # tight_layout 대신 명시적 subplots_adjust 사용 (axis off 패널 경고 회피)
        if save_path:
            Path(save_path).parent.mkdir(parents=True, exist_ok=True)
            plt.savefig(save_path, dpi=150, bbox_inches="tight")
        if show:
            plt.show()
        plt.close(fig)

    # ─────────────────────────────────────────────────────────
    # 자동 계산 헬퍼
    # ─────────────────────────────────────────────────────────
    @staticmethod
    def _auto_compute_signal(df: pd.DataFrame,
                              result: SwingAnalysisResult) -> ParkSignal:
        """df에서 박병창 시그널을 자동 계산.

        실제 운영 시엔 park_rules/scoring.py의 ParkSignalAggregator를 사용하고,
        여기는 fallback용 간이 계산.
        """
        signal = ParkSignal()
        if len(df) < 60:
            return signal

        # 이평선
        signal.ma5 = float(df["Close"].rolling(5).mean().iloc[-1])
        signal.ma20 = float(df["Close"].rolling(20).mean().iloc[-1])
        signal.ma60 = float(df["Close"].rolling(60).mean().iloc[-1])

        # 50% 룰
        prev = df.iloc[-2]
        signal.fifty_pct_level = float((prev["Open"] + prev["Close"]) / 2.0)
        signal.fifty_pct_rule = "bull" if prev["Close"] > prev["Open"] else "bear"

        # 시장 자세 판단
        price = result.current_price
        if price > signal.ma5 and signal.ma5 > signal.ma20:
            signal.stance = "황소_강세"
        elif price > signal.ma20:
            signal.stance = "황소_눌림"
        elif price < signal.ma20 * 0.95:
            signal.stance = "곰_과매도"
        else:
            signal.stance = "중립"

        # 6축 간이 점수
        signal.price_score = 80.0 if price > signal.ma5 else (60.0 if price > signal.ma20 else 35.0)
        vol_ma = df["Volume"].rolling(20).mean().iloc[-1]
        vol_ratio = df["Volume"].iloc[-1] / max(vol_ma, 1)
        signal.volume_score = min(100.0, 50.0 + vol_ratio * 15.0)
        signal.time_score = 60.0
        signal.motion_score = 65.0 if signal.ma5 > signal.ma20 else 40.0
        signal.velocity_score = 60.0
        signal.structure_score = 55.0

        # 체크리스트
        signal.checklist = [
            ("5일선 위 (매수 1원칙)", price > signal.ma5),
            ("황소 50% 룰 지지",
             signal.fifty_pct_rule == "bull" and price > signal.fifty_pct_level),
            ("거래량 급증 동반", vol_ratio >= 2.0),
            ("정배열 (5일>20일>60일)",
             signal.ma5 > signal.ma20 > signal.ma60),
            ("상승 추세 (현재가 > 60일선)", price > signal.ma60),
        ]
        return signal

    @staticmethod
    def _compute_rule_number(price: float, signal: ParkSignal) -> int:
        if price > signal.ma5:
            return 1
        elif price > signal.ma20:
            return 2
        return 3

    @staticmethod
    def _fmt_price(value: float, ticker: str) -> str:
        return f"{value:,.0f}" if ".K" in ticker else f"{value:,.2f}"

    # ─────────────────────────────────────────────────────────
    # 패널 1: 가격 + 이평선 + 50% 룰선
    # ─────────────────────────────────────────────────────────
    @staticmethod
    def _plot_price(ax, 
                    df_full: pd.DataFrame,
                    df_view: pd.DataFrame,
                    result: SwingAnalysisResult,
                    signal: ParkSignal) -> None:
        # 이평선 5/20/60
        ma5 = df_full["Close"].rolling(5).mean()
        ma20 = df_full["Close"].rolling(20).mean()
        ma60 = df_full["Close"].rolling(60).mean()

        ax.plot(df_view.index, ma5.loc[df_view.index], label="5일선", color="#1D9E75",
                linewidth=1.8, zorder=5)
        ax.plot(df_view.index, ma20.loc[df_view.index], label="20일선", color="#BA7517",
                linewidth=1.4, linestyle="--", zorder=5)
        ax.plot(df_view.index, ma60.loc[df_view.index], label="60일선", color="#993556",
                linewidth=1.1, linestyle=":", alpha=0.75, zorder=5)

        # 캔들 그리기 (한국식: 빨강 상승, 파랑 하락)
        n = len(df_view)
        width_days = max(0.6, min(1.0, 250.0 / n))
        for date, row in df_view.iterrows():
            is_bull = row["Close"] >= row["Open"]
            color = "#E24B4A" if is_bull else "#185FA5"
            ax.plot([date, date], [row["Low"], row["High"]],
                    color=color, linewidth=0.6, alpha=0.6, zorder=2)
            body_low = min(row["Open"], row["Close"])
            body_high = max(row["Open"], row["Close"])
            body_h = max(body_high - body_low, row["Close"] * 0.001)
            ax.bar(date, body_h, bottom=body_low, width=width_days,
                   color=color, alpha=0.85, edgecolor="none", zorder=3)

        # 50% 룰선 (마지막 60일 구간에만 표시)
        right_handles = []
        if signal.fifty_pct_rule != "none":
            color = "#E24B4A" if signal.fifty_pct_rule == "bull" else "#185FA5"
            label = (f"황소 50% 룰 "
                     f"{ParkChartVisualizer._fmt_price(signal.fifty_pct_level, result.ticker)}"
                     if signal.fifty_pct_rule == "bull"
                     else f"곰 50% 룰 "
                          f"{ParkChartVisualizer._fmt_price(signal.fifty_pct_level, result.ticker)}")
            recent_start = df_view.index[max(0, n - 60)]
            line = ax.hlines(signal.fifty_pct_level, recent_start, df_view.index[-1],
                             colors=color, linewidth=1.8, linestyles="--",
                             alpha=0.9, label=label, zorder=6)
            right_handles.append(line)

        # 손절/익절 (기존 swing.py 패턴 그대로)
        """
        if result.exit_strategy.full_exit_price:
            label = f"전량익절 {ParkChartVisualizer._fmt_price(result.exit_strategy.full_exit_price, result.ticker)}"
            line = ax.axhline(result.exit_strategy.full_exit_price,
                              color="blue", linewidth=0.8, linestyle="--",
                              label=label)
            right_handles.append(line)

        if result.exit_strategy.partial_exit_price:
            label = f"부분익절 {ParkChartVisualizer._fmt_price(result.exit_strategy.partial_exit_price, result.ticker)}"
            line = ax.axhline(result.exit_strategy.partial_exit_price,
                              color="green", linewidth=0.8, linestyle=":",
                              label=label)
            right_handles.append(line)

        if result.position.stop_loss:
            label = f"손절 {ParkChartVisualizer._fmt_price(result.position.stop_loss, result.ticker)}"
            line = ax.axhline(result.position.stop_loss,
                              color="coral", linewidth=0.8, linestyle=":",
                              label=label)
            right_handles.append(line)

        if result.exit_strategy.trailing_stop:
            label = f"트레일링 스톱 {ParkChartVisualizer._fmt_price(result.exit_strategy.trailing_stop, result.ticker)}"
            line = ax.axhline(result.exit_strategy.trailing_stop,
                              color="red", linewidth=0.8, linestyle="--",
                              label=label)
            right_handles.append(line)
        """

        # 현재가 마커
        ax.scatter([df_view.index[-1]], [result.current_price], s=90,
                   color="#0C447C", edgecolor="white", linewidth=2, zorder=10)

        # 왼쪽 범례: 이평선만
        all_handles, all_labels = ax.get_legend_handles_labels()
        left_handles = [h for h in all_handles if h not in right_handles]
        left_labels = [l for h, l in zip(all_handles, all_labels)
                       if h not in right_handles]
        ax.legend(left_handles, left_labels, loc="upper left", fontsize=7)

        # 오른쪽 범례: 50% 룰선 + 손절/익절
        if right_handles:
            ax.add_artist(
                ax.legend(right_handles,
                          [h.get_label() for h in right_handles],
                          loc="upper right", fontsize=6)
            )
            ax.legend(left_handles, left_labels, loc="upper left", fontsize=7)

        ax.set_title("Price + 이평선(5/20/60) + 50% 룰선",
                     fontsize=11, loc="left")
        ax.grid(True, alpha=0.2, linestyle="--")

    # ─────────────────────────────────────────────────────────
    # 패널 2: 거래량 (평균 2배 이상 강조)
    # ─────────────────────────────────────────────────────────
    @staticmethod
    def _plot_volume(ax, df: pd.DataFrame) -> None:
        vol_ma = df["Volume"].rolling(20).mean()
        is_surge = df["Volume"] >= vol_ma * 2.0

        # 색상: 급증=빨강, 전일대비 상승=연빨강, 하락=연파랑
        colors = []
        prev_vol = df["Volume"].shift(1).fillna(0)
        for v, pv, surge in zip(df["Volume"], prev_vol, is_surge):
            if surge:
                colors.append("#E24B4A")
            elif v > pv:
                colors.append("#F0997B")
            else:
                colors.append("#85B7EB")

        ax.bar(df.index, df["Volume"], color=colors, alpha=0.85,
               edgecolor="none")
        ax.plot(df.index, vol_ma, color="#444441", linewidth=0.9,
                linestyle="--", alpha=0.7, label="평균 거래량 (20일)")
        ax.plot(df.index, vol_ma * 2.0, color="#A32D2D", linewidth=0.8,
                linestyle=":", alpha=0.6, label="급증 임계 (평균×2)")
        ax.set_title("거래량 (■ 평균 2배 이상 급증)",
                     fontsize=10, loc="left")
        ax.legend(loc="upper left", fontsize=7)
        ax.grid(True, alpha=0.2, linestyle="--")

    # ─────────────────────────────────────────────────────────
    # 패널 3: 매물대 (이퀴볼륨) - 가로 막대
    # ─────────────────────────────────────────────────────────
    @staticmethod
    def _plot_volume_profile(ax, df: pd.DataFrame,
                              result: SwingAnalysisResult,
                              signal: ParkSignal) -> None:
        # 가격대별 누적 거래량 계산
        price_min, price_max = df["Low"].min(), df["High"].max()
        bins = 40
        edges = np.linspace(price_min, price_max, bins + 1)
        centers = (edges[:-1] + edges[1:]) / 2

        profile = np.zeros(bins)
        for _, row in df.iterrows():
            low_idx = max(0, min(bins - 1,
                                  np.searchsorted(edges, row["Low"]) - 1))
            high_idx = max(0, min(bins - 1,
                                   np.searchsorted(edges, row["High"]) - 1))
            n_bins = high_idx - low_idx + 1
            if n_bins > 0:
                profile[low_idx:high_idx + 1] += row["Volume"] / n_bins

        # 상위 30% 매물대는 강조
        nonzero = profile[profile > 0]
        if len(nonzero) > 0:
            threshold = np.percentile(nonzero, 70)
            colors = ["#A32D2D" if v >= threshold else "#85B7EB"
                      for v in profile]
        else:
            colors = ["#85B7EB"] * bins

        bar_height = (edges[1] - edges[0]) * 0.85
        ax.barh(centers, profile, height=bar_height, color=colors,
                alpha=0.75, edgecolor="none")

        # 현재가 수평선
        ax.axhline(result.current_price, color="#0C447C", linewidth=1.5,
                   linestyle="-", alpha=0.85,
                   label=f"현재가 {ParkChartVisualizer._fmt_price(result.current_price, result.ticker)}")

        # 50% 룰선 표시
        if signal.fifty_pct_rule != "none":
            color = "#E24B4A" if signal.fifty_pct_rule == "bull" else "#185FA5"
            label = (f"황소 50%선 {ParkChartVisualizer._fmt_price(signal.fifty_pct_level, result.ticker)}"
                     if signal.fifty_pct_rule == "bull"
                     else f"곰 50%선 {ParkChartVisualizer._fmt_price(signal.fifty_pct_level, result.ticker)}")
            ax.axhline(signal.fifty_pct_level, color=color, linewidth=1.2,
                       linestyle="--", alpha=0.8, label=label)

        ax.set_title("매물대 (이퀴볼륨) — 가격대별 누적 거래량",
                     fontsize=10, loc="left")
        ax.legend(loc="upper right", fontsize=7)
        ax.set_xlabel("누적 거래량", fontsize=8)
        ax.grid(True, alpha=0.2, linestyle="--", axis="x")

    # ─────────────────────────────────────────────────────────
    # 패널 4: 박병창 6축 점수 (수평 막대)
    # ─────────────────────────────────────────────────────────
    @staticmethod
    def _plot_six_axis(ax, signal: ParkSignal) -> None:
        labels = ["시간", "가격", "거래량", "움직임", "속도", "구조"]
        values = [signal.time_score, signal.price_score, signal.volume_score,
                  signal.motion_score, signal.velocity_score,
                  signal.structure_score]
        weights = [0.15, 0.25, 0.25, 0.15, 0.10, 0.10]

        y_pos = np.arange(len(labels))
        # 점수에 따른 색상 (50 기준)
        colors = ["#1D9E75" if v >= 65 else ("#BA7517" if v >= 45 else "#A32D2D")
                  for v in values]

        bars = ax.barh(y_pos, values, color=colors, alpha=0.85,
                       edgecolor="none", height=0.65)

        # 50점 기준선
        ax.axvline(50, color="#444441", linewidth=0.8, linestyle="--",
                   alpha=0.6, label="기준선 50")
        ax.axvline(65, color="#1D9E75", linewidth=0.6, linestyle=":",
                   alpha=0.4)

        # 값 + 가중치 표시
        for i, (val, w) in enumerate(zip(values, weights)):
            ax.text(val + 1.5, i, f"{val:.0f}  (w={w:.2f})",
                    va="center", fontsize=8, color="#444441")

        ax.set_yticks(y_pos)
        ax.set_yticklabels(labels, fontsize=9)
        ax.set_xlim(0, 110)
        ax.invert_yaxis()
        ax.set_title(
            f"박병창 6축 핵심 개념 점수 (총점 {signal.total_score:+.1f})",
            fontsize=10, loc="left")
        ax.legend(loc="lower right", fontsize=7)
        ax.grid(True, alpha=0.2, linestyle="--", axis="x")

    # ─────────────────────────────────────────────────────────
    # 패널 5: 매수 3원칙 게이지
    # ─────────────────────────────────────────────────────────
    @staticmethod
    def _plot_rule_gauge(ax, result: SwingAnalysisResult,
                         signal: ParkSignal) -> None:
        ax.axis("off")
        price = result.current_price

        # 가격 축 범위
        low_bound = min(signal.ma60, price * 0.85)
        high_bound = max(signal.ma5, signal.ma20, price) * 1.08
        span = max(high_bound - low_bound, 1.0)

        def to_x(p: float) -> float:
            return max(0.0, min(1.0, (p - low_bound) / span))

        # 두 이평선 중 낮은/높은 것
        ma_lower = min(signal.ma5, signal.ma20)
        ma_upper = max(signal.ma5, signal.ma20)
        x_lower = to_x(ma_lower)
        x_upper = to_x(ma_upper)

        # 게이지 바 (3원칙=빨강, 2원칙=노랑, 1원칙=초록)
        bar_y, bar_h = 0.35, 0.35
        ax.add_patch(Rectangle((0, bar_y), x_lower, bar_h,
                                facecolor="#FCEBEB", edgecolor="none",
                                transform=ax.transAxes))
        ax.add_patch(Rectangle((x_lower, bar_y), x_upper - x_lower, bar_h,
                                facecolor="#FAEEDA", edgecolor="none",
                                transform=ax.transAxes))
        ax.add_patch(Rectangle((x_upper, bar_y), 1.0 - x_upper, bar_h,
                                facecolor="#EAF3DE", edgecolor="none",
                                transform=ax.transAxes))

        # 이평선 마커 (수직 점선)
        for x, ma_val, name in [(x_lower, ma_lower,
                                 "20일선" if signal.ma5 > signal.ma20 else "5일선"),
                                (x_upper, ma_upper,
                                 "5일선" if signal.ma5 > signal.ma20 else "20일선")]:
            ax.plot([x, x], [bar_y - 0.04, bar_y + bar_h + 0.04],
                    color="#444441", linewidth=1, linestyle="--",
                    transform=ax.transAxes)
            ax.text(x, bar_y + bar_h + 0.08,
                    f"{name}\n{ParkChartVisualizer._fmt_price(ma_val, result.ticker)}",
                    ha="center", va="bottom", fontsize=8, color="#444441",
                    transform=ax.transAxes)

        # 영역 라벨
        ax.text(x_lower / 2, bar_y + bar_h / 2,
                "3원칙\n(20일선 아래)",
                ha="center", va="center", fontsize=9, color="#791F1F",
                fontweight="bold", transform=ax.transAxes)
        ax.text((x_lower + x_upper) / 2, bar_y + bar_h / 2,
                "2원칙\n(눌림목)",
                ha="center", va="center", fontsize=9, color="#633806",
                fontweight="bold", transform=ax.transAxes)
        ax.text((x_upper + 1.0) / 2, bar_y + bar_h / 2,
                "1원칙\n(5일선 위)",
                ha="center", va="center", fontsize=9, color="#27500A",
                fontweight="bold", transform=ax.transAxes)

        # 현재가 마커
        current_x = to_x(price)
        ax.scatter([current_x], [bar_y + bar_h / 2], s=160,
                   color="#0C447C", edgecolor="white", linewidth=2.5,
                   zorder=10, transform=ax.transAxes)
        ax.annotate(
            f"현재가\n{ParkChartVisualizer._fmt_price(price, result.ticker)}",
            xy=(current_x, bar_y),
            xytext=(current_x, 0.02),
            ha="center", fontsize=9, color="#0C447C", fontweight="bold",
            transform=ax.transAxes,
        )

        # 우측: 체크리스트
        x_check = 1.02
        ax.text(x_check, 0.92, "매매 시그널 체크",
                fontsize=10, fontweight="bold",
                transform=ax.transAxes)
        for i, (label, passed) in enumerate(signal.checklist[:5]):
            mark = "O" if passed else "X"
            color = "#0F6E56" if passed else "#A32D2D"
            ax.text(x_check, 0.75 - i * 0.15, f"{mark}  {label}",
                    fontsize=8.5, color=color, transform=ax.transAxes)

        ax.text(0.0, 0.92, "매수 3원칙 게이지 (현재가 위치)",
                fontsize=10, fontweight="bold", transform=ax.transAxes)