from __future__ import annotations
 
from dataclasses import dataclass
from enum import Enum
from typing import Optional
 
import pandas as pd

from .fifty_percent_rule import (
    FiftyPercentRule, FiftyRuleType, FiftyRuleResult, 
    MAZone, 
    RuleAction, RuleSignal
)


# ─────────────────────────────────────────────────────────────
# 지표 계산 헬퍼
# ─────────────────────────────────────────────────────────────
def ensure_ma(df: pd.DataFrame) -> pd.DataFrame:
    """5/20/60일 이동평균이 없으면 계산해서 추가 (원본 보존)."""
    out = df.copy()
    if "ma5" not in out:
        out["ma5"] = out["Close"].rolling(5).mean()
    if "ma20" not in out:
        out["ma20"] = out["Close"].rolling(20).mean()
    if "ma60" not in out:
        out["ma60"] = out["Close"].rolling(60).mean()
    return out
 
 
def classify_ma_zone(price: float, ma5: float, ma20: float) -> MAZone:
    """현재가의 이평선 기준 위치 분류."""
    if price >= ma5:
        return MAZone.ABOVE_MA5
    elif price >= ma20:
        return MAZone.BETWEEN_MA5_MA20
    return MAZone.BELOW_MA20


# ─────────────────────────────────────────────────────────────
# 2. 이평선 매수 3원칙
# ─────────────────────────────────────────────────────────────
class MABuyRule:
    """박병창 매수 3원칙 (이동평균선 기준).
 
    매수의 세 가지 타이밍 — 현재가의 이평선 위치에 따라 전략이 다르다:
 
    제1원칙 (5일선 위):
        상승 추세가 살아 있는 강세 구간. 황소가 우위.
        → 50% 룰 지지 + 거래량 동반 + 정배열이면 적극 매수(추세 추종).
        가장 안전하지만 이미 상승한 자리라 단기 변동성 주의.
 
    제2원칙 (5일선-20일선 사이):
        단기 조정(눌림목) 구간. 5일선을 깨고 20일선까지 밀린 상태.
        → 20일선 지지 + 50% 룰 지지 확인 시 매수(눌림목 매수).
        추세 유지 여부 판단이 핵심.
 
    제3원칙 (20일선 아래):
        추세 이탈/약세 구간. 곰이 우위.
        → 원칙적으로 신규 매수는 위험. 단, 과대 낙폭 후 거래량 급증 동반
          '바닥 반전 신호'가 명확할 때만 분할 매수(저점 매수, 고위험).
    """
 
    def __init__(self, fifty_rule: Optional[FiftyPercentRule] = None):
        self.fifty_rule = fifty_rule or FiftyPercentRule()
 
    def evaluate(self, df: pd.DataFrame) -> RuleSignal:
        if len(df) < 20:
            raise ValueError("최소 20거래일 데이터 필요")
 
        d = ensure_ma(df)
        curr = d.iloc[-1]
        price = float(curr["Close"])
        ma5 = float(curr["ma5"])
        ma20 = float(curr["ma20"])
        ma60 = float(curr["ma60"]) if pd.notna(curr["ma60"]) else None
 
        zone = classify_ma_zone(price, ma5, ma20)
        fifty = self.fifty_rule.evaluate(df)
 
        # 거래량 급증 여부
        vol_ma = d["Volume"].rolling(20).mean().iloc[-1]
        vol_ratio = float(curr["Volume"] / vol_ma) if vol_ma > 0 else 0.0
 
        # 5일선 기울기 (추세 방향)
        ma5_slope = float(d["ma5"].iloc[-1] - d["ma5"].iloc[-3])
 
        if zone == MAZone.ABOVE_MA5:
            return self._principle_1(price, ma5, ma20, ma60, fifty,
                                     vol_ratio, ma5_slope)
        elif zone == MAZone.BETWEEN_MA5_MA20:
            return self._principle_2(price, ma5, ma20, fifty, vol_ratio)
        else:
            return self._principle_3(price, ma5, ma20, fifty, vol_ratio)
 
    def _principle_1(self, price, ma5, ma20, ma60, fifty: FiftyRuleResult,
                     vol_ratio, ma5_slope) -> RuleSignal:
        """제1원칙: 5일선 위 — 추세 추종 매수."""
        conf = 0.5
        reasons = ["5일선 위 강세 구간 (매수 1원칙)"]
 
        # 황소 50% 룰 지지 → 강한 가점
        if fifty.is_support_held:
            conf += 0.2
            reasons.append(f"황소 50%선({fifty.midpoint:,.0f}) 지지")
 
        # 정배열 (5>20>60)
        aligned = ma60 is not None and ma5 > ma20 > ma60
        if aligned:
            conf += 0.15
            reasons.append("정배열 (5>20>60)")
 
        # 거래량 동반
        if vol_ratio >= 1.5:
            conf += 0.1
            reasons.append(f"거래량 동반 ({vol_ratio:.1f}배)")
 
        # 5일선 상승 기울기
        if ma5_slope > 0:
            conf += 0.05
            reasons.append("5일선 상승 기울기")
 
        conf = min(1.0, conf)
        # 손절: 5일선 또는 황소 50%선 중 가까운 쪽
        stop = max(ma5, fifty.midpoint) if fifty.is_support_held else ma5
        return RuleSignal(
            action=RuleAction.BUY,
            principle=1,
            zone=MAZone.ABOVE_MA5,
            confidence=round(conf, 2),
            entry_hint=price,
            stop_loss=round(stop * 0.99, 2),  # 지지선 -1% 이탈 시 손절
            rationale=" / ".join(reasons),
        )
 
    def _principle_2(self, price, ma5, ma20, fifty: FiftyRuleResult,
                     vol_ratio) -> RuleSignal:
        """제2원칙: 5일선-20일선 사이 — 눌림목 매수."""
        conf = 0.4
        reasons = ["5일선-20일선 사이 눌림목 구간 (매수 2원칙)"]
 
        # 20일선 지지 (현재가가 20일선 근처에서 지지받는가)
        dist_ma20 = (price - ma20) / ma20 * 100.0
        if 0 <= dist_ma20 <= 3.0:
            conf += 0.2
            reasons.append(f"20일선 지지 근접 (+{dist_ma20:.1f}%)")
 
        # 황소 50% 룰 지지 → 눌림목에서 반등 신호
        if fifty.is_support_held:
            conf += 0.2
            reasons.append(f"황소 50%선({fifty.midpoint:,.0f}) 지지 → 반등 기대")
        elif fifty.rule_type == FiftyRuleType.BEAR and not fifty.is_holding:
            # 곰 룰 저항을 뚫었으면 반등 신호
            conf += 0.1
            reasons.append("전일 음봉 50%선 회복")
 
        # 거래량 동반 (눌림목에서 거래량 실리면 반등 가능성)
        if vol_ratio >= 1.2:
            conf += 0.1
            reasons.append(f"거래량 회복 ({vol_ratio:.1f}배)")
 
        conf = min(1.0, conf)
        action = RuleAction.BUY if conf >= 0.55 else RuleAction.HOLD
        return RuleSignal(
            action=action,
            principle=2,
            zone=MAZone.BETWEEN_MA5_MA20,
            confidence=round(conf, 2),
            entry_hint=price,
            stop_loss=round(ma20 * 0.98, 2),  # 20일선 -2% 이탈 시 손절
            rationale=" / ".join(reasons),
        )
 
    def _principle_3(self, price, ma5, ma20, fifty: FiftyRuleResult,
                     vol_ratio) -> RuleSignal:
        """제3원칙: 20일선 아래 — 저점 매수 (고위험)."""
        conf = 0.2
        reasons = ["20일선 아래 약세 구간 (매수 3원칙, 고위험)"]
 
        # 바닥 반전 신호: 거래량 급증 + 황소 50% 룰 회복
        bottom_reversal = False
        if vol_ratio >= 2.0:
            conf += 0.15
            reasons.append(f"거래량 급증 ({vol_ratio:.1f}배) → 투매/반전 가능")
            bottom_reversal = True
 
        if fifty.is_support_held:
            conf += 0.15
            reasons.append(f"황소 50%선({fifty.midpoint:,.0f}) 회복 → 반전 신호")
            bottom_reversal = True
 
        # 반전 신호 없으면 매수 금지
        if bottom_reversal and conf >= 0.45:
            action = RuleAction.BUY
            reasons.append("→ 분할 매수만 권장")
        else:
            action = RuleAction.HOLD
            reasons.append("→ 반전 신호 부족, 신규 매수 회피")
 
        conf = min(1.0, conf)
        return RuleSignal(
            action=action,
            principle=3,
            zone=MAZone.BELOW_MA20,
            confidence=round(conf, 2),
            entry_hint=price if action == RuleAction.BUY else None,
            stop_loss=round(price * 0.95, 2),  # 진입가 -5% (변동성 큼)
            rationale=" / ".join(reasons),
        )
 
 
# ─────────────────────────────────────────────────────────────
# 3. 이평선 매도 2원칙
# ─────────────────────────────────────────────────────────────
class MASellRule:
    """박병창 매도 2원칙 (이동평균선 기준).
 
    매도의 두 가지 타이밍 — 보유 포지션의 청산 시점 판단:
 
    제1원칙 (5일선 위):
        아직 강세 구간이지만 과열/이탈 신호가 나오는 자리.
        → 곰 50% 룰 저항 + 5일선 이탈 임박 + 거래량 감소 시 (분할) 매도.
        추세가 살아 있으면 보유, 신호가 명확하면 일부 익절.
 
    제2원칙 (5일선-20일선 사이):
        5일선을 이미 깬 단기 약세 구간. 추세 둔화.
        → 20일선마저 이탈하면 추세 종료로 보고 매도(손절/익절).
        곰 50% 룰 저항에 눌리면 매도 강도 강화.
    """
 
    def __init__(self, fifty_rule: Optional[FiftyPercentRule] = None):
        self.fifty_rule = fifty_rule or FiftyPercentRule()
 
    def evaluate(self, df: pd.DataFrame) -> RuleSignal:
        if len(df) < 20:
            raise ValueError("최소 20거래일 데이터 필요")
 
        d = ensure_ma(df)
        curr = d.iloc[-1]
        price = float(curr["Close"])
        ma5 = float(curr["ma5"])
        ma20 = float(curr["ma20"])
 
        zone = classify_ma_zone(price, ma5, ma20)
        fifty = self.fifty_rule.evaluate(df)
 
        vol_ma = d["Volume"].rolling(20).mean().iloc[-1]
        vol_ratio = float(curr["Volume"] / vol_ma) if vol_ma > 0 else 0.0
        ma5_slope = float(d["ma5"].iloc[-1] - d["ma5"].iloc[-3])
 
        if zone == MAZone.ABOVE_MA5:
            return self._principle_1(price, ma5, ma20, fifty,
                                     vol_ratio, ma5_slope)
        elif zone == MAZone.BETWEEN_MA5_MA20:
            return self._principle_2(price, ma5, ma20, fifty,
                                     vol_ratio, ma5_slope)
        else:
            # 20일선 아래는 매도 원칙 범위 밖 (이미 청산되었어야 함)
            return RuleSignal(
                action=RuleAction.SELL,
                principle=2,
                zone=MAZone.BELOW_MA20,
                confidence=0.9,
                stop_loss=None,
                rationale="20일선 이탈 — 추세 종료, 잔여 물량 청산 권장",
            )
 
    def _principle_1(self, price, ma5, ma20, fifty: FiftyRuleResult,
                     vol_ratio, ma5_slope) -> RuleSignal:
        """제1원칙: 5일선 위 — 과열 익절."""
        conf = 0.2  # 강세 구간이라 기본 매도 신뢰도는 낮음
        reasons = ["5일선 위 강세 구간 (매도 1원칙)"]
 
        # 곰 50% 룰 저항 → 상승 둔화 신호
        if fifty.is_resistance_held:
            conf += 0.25
            reasons.append(f"곰 50%선({fifty.midpoint:,.0f}) 저항 → 상승 둔화")
 
        # 5일선 기울기 둔화/하락 전환
        if ma5_slope <= 0:
            conf += 0.2
            reasons.append("5일선 기울기 둔화/하락 전환")
 
        # 거래량 감소 (상승 동력 약화)
        if vol_ratio < 0.8:
            conf += 0.15
            reasons.append(f"거래량 감소 ({vol_ratio:.1f}배) → 매수세 약화")
 
        # 5일선 이탈 임박 (현재가가 5일선에 근접)
        dist_ma5 = (price - ma5) / ma5 * 100.0
        if dist_ma5 <= 1.0:
            conf += 0.15
            reasons.append(f"5일선 이탈 임박 (+{dist_ma5:.1f}%)")
 
        conf = min(1.0, conf)
        action = RuleAction.SELL if conf >= 0.5 else RuleAction.HOLD
        reasons.append("→ 분할 익절" if action == RuleAction.SELL
                       else "→ 추세 유지, 보유")
        return RuleSignal(
            action=action,
            principle=1,
            zone=MAZone.ABOVE_MA5,
            confidence=round(conf, 2),
            stop_loss=round(ma5 * 0.99, 2),
            rationale=" / ".join(reasons),
        )
 
    def _principle_2(self, price, ma5, ma20, fifty: FiftyRuleResult,
                     vol_ratio, ma5_slope) -> RuleSignal:
        """제2원칙: 5일선-20일선 사이 — 추세 종료 매도."""
        conf = 0.45  # 이미 5일선 깬 약세라 매도 신뢰도 높음
        reasons = ["5일선-20일선 사이 약세 구간 (매도 2원칙)"]
 
        # 20일선 이탈 임박
        dist_ma20 = (price - ma20) / ma20 * 100.0
        if dist_ma20 <= 1.0:
            conf += 0.25
            reasons.append(f"20일선 이탈 임박 (+{dist_ma20:.1f}%) → 추세 종료 위험")
 
        # 곰 50% 룰 저항에 눌림
        if fifty.is_resistance_held:
            conf += 0.2
            reasons.append(f"곰 50%선({fifty.midpoint:,.0f}) 저항 → 반등 실패")
 
        # 5일선 하락 기울기
        if ma5_slope < 0:
            conf += 0.1
            reasons.append("5일선 하락 추세")
 
        conf = min(1.0, conf)
        action = RuleAction.SELL if conf >= 0.55 else RuleAction.HOLD
        reasons.append("→ 매도/손절" if action == RuleAction.SELL
                       else "→ 20일선 지지 확인 시까지 관망")
        return RuleSignal(
            action=action,
            principle=2,
            zone=MAZone.BETWEEN_MA5_MA20,
            confidence=round(conf, 2),
            stop_loss=round(ma20 * 0.98, 2),
            rationale=" / ".join(reasons),
        )