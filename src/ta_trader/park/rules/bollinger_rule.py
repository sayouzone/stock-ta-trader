"""
ta_trader/rules/bollinger_rule.py
볼린저 밴드 매매 룰 - 박병창 core_rules.py와 동일한 RuleSignal 형식 출력

박병창 엔진(ParkCoreRuleEngine)과 나란히 비교/결합하기 위해
core_rules.py의 RuleAction / RuleSignal 구조를 그대로 재사용한다.

두 가지 매매 모드 지원:
    - MEAN_REVERSION (평균회귀): 하단 매수 / 상단 매도 (역추세)
    - BAND_RIDING    (밴드타기): 상단 지속 = 추세 매수 (추세추종, 박병창과 유사)

지표:
    %B    = (종가 - 하단) / (상단 - 하단)   ... 0=하단, 1=상단
    밴드폭 = (상단 - 하단) / 중심선          ... 변동성 (스퀴즈 판단)
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional

import pandas as pd

# 박병창 모듈의 구조 재사용
#from .core import RuleAction, RuleSignal, MAZone
from .fifty_percent_rule import RuleAction, RuleSignal, MAZone
from .core import CoreRuleEngine


class BollingerMode(Enum):
    MEAN_REVERSION = "평균회귀"   # 하단매수/상단매도 (역추세)
    BAND_RIDING = "밴드타기"      # 상단지속=추세매수 (추세추종)


@dataclass
class BollingerContext:
    """볼린저 지표 스냅샷"""
    price: float
    upper: float
    middle: float
    lower: float

    @property
    def pct_b(self) -> float:
        """%B: 밴드 내 위치 (0=하단, 0.5=중심, 1=상단)"""
        rng = self.upper - self.lower
        return (self.price - self.lower) / rng if rng > 0 else 0.5

    @property
    def band_width(self) -> float:
        """밴드폭: 변동성 (작을수록 스퀴즈)"""
        return (self.upper - self.lower) / self.middle if self.middle > 0 else 0.0


def _ensure_bollinger(df: pd.DataFrame, period: int = 20,
                      num_std: float = 2.0) -> pd.DataFrame:
    """볼린저 밴드 컬럼이 없으면 계산."""
    out = df.copy()
    if "bb_middle" not in out:
        mid = out["Close"].rolling(period).mean()
        std = out["Close"].rolling(period).std()
        out["bb_middle"] = mid
        out["bb_upper"] = mid + num_std * std
        out["bb_lower"] = mid - num_std * std
    return out


class BollingerRule:
    """볼린저 밴드 매매 룰.

    박병창 엔진과 동일하게 RuleSignal(action, confidence, rationale)을 반환해
    같은 화면/로직에서 비교 가능하다.
    """

    def __init__(self, mode: BollingerMode = BollingerMode.MEAN_REVERSION,
                 squeeze_threshold: float = 0.10):
        self.mode = mode
        self.squeeze_threshold = squeeze_threshold

    def _ctx(self, df: pd.DataFrame) -> BollingerContext:
        d = _ensure_bollinger(df)
        curr = d.iloc[-1]
        return BollingerContext(
            price=float(curr["Close"]),
            upper=float(curr["bb_upper"]),
            middle=float(curr["bb_middle"]),
            lower=float(curr["bb_lower"]),
        )

    def evaluate_buy(self, df: pd.DataFrame) -> RuleSignal:
        if len(df) < 20:
            raise ValueError("최소 20거래일 데이터 필요")
        ctx = self._ctx(df)
        pctb = ctx.pct_b
        width = ctx.band_width
        is_squeeze = width < self.squeeze_threshold

        if self.mode == BollingerMode.MEAN_REVERSION:
            return self._buy_mean_reversion(ctx, pctb, width, is_squeeze)
        else:
            return self._buy_band_riding(ctx, pctb, width, is_squeeze)

    def evaluate_sell(self, df: pd.DataFrame) -> RuleSignal:
        if len(df) < 20:
            raise ValueError("최소 20거래일 데이터 필요")
        ctx = self._ctx(df)
        pctb = ctx.pct_b
        return self._sell(ctx, pctb)

    # ── 평균회귀 매수: 하단에서 산다 (박병창과 정반대) ──
    def _buy_mean_reversion(self, ctx, pctb, width, squeeze) -> RuleSignal:
        conf = 0.0
        reasons = [f"평균회귀 모드 (%B={pctb:.2f})"]
        if pctb <= 0.0:
            conf = 0.7
            reasons.append("하단(-2σ) 이탈 → 과매도, 반등 기대")
        elif pctb <= 0.2:
            conf = 0.6
            reasons.append("하단 근접 → 매수 기회")
        elif pctb <= 0.4:
            conf = 0.35
            reasons.append("중심선 아래 → 약한 매수 관심")
        else:
            conf = 0.1
            reasons.append("중심선 위 → 평균회귀 매수 부적합")

        # 스퀴즈면 평균회귀 신호 신뢰도 낮춤 (곧 돌파 가능성)
        if squeeze:
            conf *= 0.7
            reasons.append(f"밴드 스퀴즈(폭 {width:.3f}) → 방향성 대기")

        action = RuleAction.BUY if conf >= 0.5 else RuleAction.HOLD
        return RuleSignal(
            action=action, principle=0,
            zone=self._zone(pctb), confidence=round(conf, 2),
            entry_hint=ctx.price if action == RuleAction.BUY else None,
            stop_loss=round(ctx.lower * 0.98, 2),
            rationale=" / ".join(reasons),
        )

    # ── 밴드타기 매수: 상단 지속 = 추세 (박병창과 유사) ──
    def _buy_band_riding(self, ctx, pctb, width, squeeze) -> RuleSignal:
        conf = 0.0
        reasons = [f"밴드타기 모드 (%B={pctb:.2f})"]
        if pctb >= 1.0:
            conf = 0.7
            reasons.append("상단(+2σ) 돌파 → 강한 추세, 밴드 타기")
        elif pctb >= 0.8:
            conf = 0.6
            reasons.append("상단 근접 → 추세 추종 매수")
        elif pctb >= 0.5:
            conf = 0.4
            reasons.append("중심선 위 → 추세 유효")
        else:
            conf = 0.15
            reasons.append("중심선 아래 → 추세 약함")

        # 스퀴즈 후 상단 돌파는 강력 신호
        if squeeze and pctb >= 0.8:
            conf = min(1.0, conf + 0.2)
            reasons.append(f"스퀴즈 후 돌파 → 변동성 확대 시작")

        action = RuleAction.BUY if conf >= 0.5 else RuleAction.HOLD
        return RuleSignal(
            action=action, principle=0,
            zone=self._zone(pctb), confidence=round(conf, 2),
            entry_hint=ctx.price if action == RuleAction.BUY else None,
            stop_loss=round(ctx.middle * 0.99, 2),  # 중심선 이탈 시 손절
            rationale=" / ".join(reasons),
        )

    # ── 매도 (두 모드 공통: 상단 과열 or 중심선 이탈) ──
    def _sell(self, ctx, pctb) -> RuleSignal:
        conf = 0.0
        reasons = [f"%B={pctb:.2f}"]
        if self.mode == BollingerMode.MEAN_REVERSION:
            if pctb >= 1.0:
                conf = 0.7; reasons.append("상단 돌파 → 과매수, 차익실현")
            elif pctb >= 0.8:
                conf = 0.55; reasons.append("상단 근접 → 매도 고려")
            else:
                conf = 0.1; reasons.append("매도 신호 약함")
        else:  # 밴드타기: 중심선 이탈이 매도 신호
            if pctb < 0.5:
                conf = 0.6; reasons.append("중심선 하향 이탈 → 추세 종료")
            elif pctb < 0.2:
                conf = 0.8; reasons.append("하단 근접 → 추세 붕괴")
            else:
                conf = 0.1; reasons.append("추세 유지 → 보유")

        action = RuleAction.SELL if conf >= 0.5 else RuleAction.HOLD
        return RuleSignal(
            action=action, principle=0,
            zone=self._zone(pctb), confidence=round(conf, 2),
            stop_loss=round(ctx.middle * 0.99, 2),
            rationale=" / ".join(reasons),
        )

    @staticmethod
    def _zone(pctb: float) -> MAZone:
        """%B를 박병창 MAZone에 대응 (비교 편의)."""
        if pctb >= 0.8:
            return MAZone.ABOVE_MA5
        elif pctb >= 0.2:
            return MAZone.BETWEEN_MA5_MA20
        return MAZone.BELOW_MA20


# ─────────────────────────────────────────────────────────────
# 박병창 vs 볼린저 동시 비교기
# ─────────────────────────────────────────────────────────────
def compare_signals(ticker: str, name: str, df: pd.DataFrame) -> str:
    """박병창 엔진과 볼린저 룰(두 모드)을 동시에 평가해 비교 출력."""
    park = CoreRuleEngine()
    verdict = park.evaluate(df)

    bb_mr = BollingerRule(BollingerMode.MEAN_REVERSION)
    bb_br = BollingerRule(BollingerMode.BAND_RIDING)

    lines = []
    lines.append("=" * 70)
    lines.append(f"{name} ({ticker})")
    lines.append(f"현재가 {df['Close'].iloc[-1]:,.0f}  /  구간: {verdict.zone.value}")
    lines.append("=" * 70)
    lines.append(f"[박병창]      매수: {verdict.buy_signal.action.value} "
                 f"(신뢰도 {verdict.buy_signal.confidence:.2f})")
    lines.append(f"              └ {verdict.buy_signal.rationale}")
    lines.append(f"              매도: {verdict.sell_signal.action.value} "
                 f"(신뢰도 {verdict.sell_signal.confidence:.2f})")

    b1 = bb_mr.evaluate_buy(df)
    lines.append(f"[볼린저-평균회귀] 매수: {b1.action.value} (신뢰도 {b1.confidence:.2f})")
    lines.append(f"              └ {b1.rationale}")

    b2 = bb_br.evaluate_buy(df)
    lines.append(f"[볼린저-밴드타기] 매수: {b2.action.value} (신뢰도 {b2.confidence:.2f})")
    lines.append(f"              └ {b2.rationale}")
    return "\n".join(lines)


if __name__ == "__main__":
    import numpy as np

    def make_df(scenario, n=60):
        np.random.seed(5)
        dates = pd.date_range("2026-03-01", periods=n, freq="B")
        if scenario == "강세추세":
            base = np.linspace(0, 0.5, n)
        elif scenario == "급락":
            base = np.concatenate([np.linspace(0, 0.3, n-10), np.linspace(0.3, 0.05, 10)])
        else:  # 횡보
            base = np.sin(np.linspace(0, 6*np.pi, n)) * 0.05
        noise = np.cumsum(np.random.randn(n) * 0.008)
        close = 10000 * np.exp(base + noise * 0.2)
        openp = close * (1 + np.random.randn(n) * 0.004)
        return pd.DataFrame({"Open": openp, "High": np.maximum(close, openp)*1.008,
                             "Low": np.minimum(close, openp)*0.992, "Close": close,
                             "Volume": np.random.gamma(3, 1e6, n)}, index=dates)

    for sc in ["강세추세", "급락", "횡보"]:
        print(f"\n########## 시나리오: {sc} ##########")
        print(compare_signals(make_df(sc)))
