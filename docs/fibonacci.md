# 피보나치 기반 시장 판단 방법

## 피보나치 수열과 황금비율

```
수열:  0, 1, 1, 2, 3, 5, 8, 13, 21, 34, 55, 89, 144 ...
비율:  인접항 비율 → 0.618 (황금비율)
역수:  1 / 0.618  → 1.618 (황금비율 확장)

핵심 비율:
  되돌림 : 0.236 / 0.382 / 0.500 / 0.618 / 0.786
  확장   : 1.272 / 1.618 / 2.000 / 2.618
```

---

## 피보나치 도구 5종

```
① Retracement  — 추세 내 되돌림 지지/저항 수준
② Extension    — 추세 지속 시 다음 목표가 예측
③ Projection   — ABC 파동 기반 C파 목표가
④ Fan          — 시간+가격 결합 추세선
⑤ Time Zone    — 전환점 시간 예측
```

---

## 핵심 체계 1: 피보나치 되돌림 (Retracement)

### 되돌림 레벨 계산

```python
def calc_fib_retracement(swing_high: float,
                          swing_low: float,
                          trend: str = "up") -> dict:
    """
    상승 추세 되돌림: High → Low 구간 기준
    하락 추세 되돌림: Low  → High 구간 기준
    """
    diff   = swing_high - swing_low
    ratios = [0.0, 0.236, 0.382, 0.500, 0.618, 0.786, 1.0]

    levels = {}
    for r in ratios:
        if trend == "up":
            # 고점에서 되돌림 (지지선)
            levels[f"{r:.3f}"] = round(swing_high - diff * r, 4)
        else:
            # 저점에서 되돌림 (저항선)
            levels[f"{r:.3f}"] = round(swing_low + diff * r, 4)

    return levels
```

### 되돌림 레벨별 시장 해석

```
레벨       시장 해석                    전략
────────────────────────────────────────────────────────
0.236   얕은 되돌림 → 강한 추세 신호    추세 추종 진입 (강세)
0.382   1차 지지    → 일반 눌림목        분할 매수 1차
0.500   중간 지지   → 추세 강도 시험     추세 지속 여부 판단 기준
0.618   황금 되돌림 → 가장 중요한 지지   분할 매수 2차 (핵심)
0.786   깊은 되돌림 → 추세 약화 경고     소량 매수 / 손절 검토
> 0.786 추세 파괴   → 반전 가능성        포지션 청산
```

```python
def assess_retracement_level(current_price: float,
                              fib_levels: dict,
                              tolerance: float = 0.005) -> dict:
    """
    현재가가 어느 피보나치 레벨에 근접했는지 판단
    """
    for label, level in fib_levels.items():
        proximity = abs(current_price - level) / level
        if proximity <= tolerance:
            ratio = float(label)
            return {
                "level":     label,
                "price":     level,
                "proximity": round(proximity * 100, 3),
                "strength":  _retracement_strength(ratio),
                "action":    _retracement_action(ratio),
            }
    return {"level": "none", "action": "monitor"}


def _retracement_strength(ratio: float) -> str:
    if ratio == 0.618:   return "★★★★★ 황금 되돌림"
    if ratio == 0.382:   return "★★★★  강한 지지"
    if ratio == 0.500:   return "★★★   중간 지지"
    if ratio == 0.786:   return "★★    약한 지지"
    if ratio == 0.236:   return "★★★   얕은 되돌림 (추세 강함)"
    return "★      참고 수준"


def _retracement_action(ratio: float) -> str:
    if ratio <= 0.382:   return "추세 강함 — 눌림목 매수"
    if ratio <= 0.500:   return "중립 — 추가 확인 후 진입"
    if ratio <= 0.618:   return "황금 되돌림 — 핵심 매수 구간"
    if ratio <= 0.786:   return "깊은 되돌림 — 소량 매수"
    return "추세 붕괴 위험 — 관망"
```

---

## 핵심 체계 2: 피보나치 확장 (Extension)

### 확장 목표가 계산

```python
def calc_fib_extension(swing_low: float,
                        swing_high: float,
                        retracement: float,
                        trend: str = "up") -> dict:
    """
    상승 추세 확장:
      Base  = swing_high - swing_low
      Entry = swing_high - (Base × retracement_ratio)
      Target = Entry + Base × extension_ratio

    주요 확장 비율: 1.272 / 1.414 / 1.618 / 2.000 / 2.618
    """
    base    = swing_high - swing_low
    entry   = swing_high - base * retracement
    ratios  = [1.000, 1.272, 1.414, 1.618, 2.000, 2.618]

    targets = {}
    for r in ratios:
        if trend == "up":
            targets[f"{r:.3f}"] = round(entry + base * r, 4)
        else:
            targets[f"{r:.3f}"] = round(entry - base * r, 4)

    return {
        "base_range": round(base, 4),
        "entry_price": round(entry, 4),
        "targets": targets,
    }
```

### 확장 레벨별 익절 전략

```
확장 레벨   의미                    익절 전략
──────────────────────────────────────────────────────
1.000    이전 고점 돌파 확인       20% 부분 익절
1.272    1차 목표가               30% 익절
1.618    황금 확장 (핵심 목표)    30% 익절 (나머지 트레일링)
2.000    강한 추세 지속 목표      10% 익절
2.618    파동 완성 구간           전량 청산 고려
```

---

## 핵심 체계 3: 피보나치 프로젝션 (Projection)

### ABC 파동 기반 C파 목표 계산

```python
def calc_fib_projection(point_a: float,
                         point_b: float,
                         point_c: float,
                         trend: str = "up") -> dict:
    """
    A → B → C 3점 기반 D(목표) 계산
    엘리어트 파동, 조화 패턴에 활용

    상승 추세:
      A = 직전 저점  B = 고점  C = 되돌림 저점
      D = C + (A→B 파동 × 확장비율)
    """
    ab_range = abs(point_b - point_a)
    ratios   = [0.618, 0.786, 1.000, 1.272, 1.618]

    projections = {}
    for r in ratios:
        if trend == "up":
            projections[f"{r:.3f}"] = round(point_c + ab_range * r, 4)
        else:
            projections[f"{r:.3f}"] = round(point_c - ab_range * r, 4)

    return {
        "ab_range":    round(ab_range, 4),
        "projections": projections,
    }
```

---

## 핵심 체계 4: 피보나치 클러스터 (Confluence)

```
피보나치의 가장 강력한 활용 = 여러 레벨의 집중 구간
클러스터 강도가 높을수록 지지/저항 신뢰도 ↑↑
```

```python
def find_fib_clusters(level_sets: list[dict],
                       tolerance: float = 0.01) -> list[dict]:
    """
    다수의 피보나치 레벨셋에서 근접 가격대 클러스터 탐지

    level_sets 예시:
      [retracement_levels, extension_levels, projection_levels, ...]
    """
    all_levels = []
    for level_set in level_sets:
        for label, price in level_set.items():
            if isinstance(price, (int, float)):
                all_levels.append({"label": label, "price": price})

    # 가격순 정렬
    all_levels.sort(key=lambda x: x["price"])

    clusters = []
    used     = set()

    for i, base in enumerate(all_levels):
        if i in used:
            continue
        cluster = [base]
        for j, other in enumerate(all_levels[i+1:], i+1):
            if j in used:
                continue
            proximity = abs(base["price"] - other["price"]) \
                        / base["price"]
            if proximity <= tolerance:
                cluster.append(other)
                used.add(j)

        if len(cluster) >= 2:
            avg_price = sum(l["price"] for l in cluster) / len(cluster)
            clusters.append({
                "cluster_price": round(avg_price, 4),
                "count":         len(cluster),
                "labels":        [l["label"] for l in cluster],
                "strength":      "★" * min(len(cluster), 5),
            })
        used.add(i)

    return sorted(clusters, key=lambda x: x["count"], reverse=True)
```

### 클러스터 활용 전략

```
클러스터 구성 레벨 수   신뢰도    전략
─────────────────────────────────────────────
2개 레벨 집중          ★★       일반 지지/저항
3개 레벨 집중          ★★★      강한 반전 구간
4개 레벨 집중          ★★★★     핵심 매매 구간
5개 이상               ★★★★★    매우 강한 전환점
```

---

## 핵심 체계 5: 피보나치 타임 존 (Time Zone)

```python
def calc_fib_time_zones(start_date: pd.Timestamp,
                         df: pd.DataFrame) -> list[dict]:
    """
    시작일로부터 피보나치 수열 봉수 이후를 전환점 후보로 표시
    Fib 수열: 1, 2, 3, 5, 8, 13, 21, 34, 55, 89, 144
    """
    fib_seq   = [1, 2, 3, 5, 8, 13, 21, 34, 55, 89, 144]
    start_idx = df.index.get_loc(
        df.index[df.index >= start_date][0]
    )

    time_zones = []
    for f in fib_seq:
        target_idx = start_idx + f
        if target_idx < len(df):
            time_zones.append({
                "fib_num":    f,
                "date":       df.index[target_idx],
                "importance": "높음" if f in [8, 13, 21, 34, 55]
                              else "보통",
            })
    return time_zones
```

---

## 핵심 체계 6: 조화 패턴 (Harmonic Patterns)

```
패턴명       X→A   A→B       B→C       C→D         신호
──────────────────────────────────────────────────────────────
Gartley     0.618  0.382~0.886  0.382~0.886  0.786   반전
Butterfly   0.786  0.382~0.886  0.382~0.886  1.272~1.618 반전
Bat         0.382~0.500  0.382~0.886  0.382~0.886  0.886  반전
Crab        0.382~0.618  0.382~0.886  0.382~0.886  1.618  가장 강한 반전
Cypher      0.382~0.618  1.130~1.414  0.382~0.618  0.786  반전
```

```python
def detect_gartley(x: float, a: float,
                    b: float, c: float,
                    d: float,
                    tolerance: float = 0.05) -> bool:
    """
    Gartley 패턴 검증
    XA 하락 후 ABCD 조화 구조에서 D점이 반전 진입
    """
    xa = abs(a - x)
    ab = abs(b - a)
    bc = abs(c - b)
    cd = abs(d - c)

    def in_range(val, lo, hi):
        return lo * (1 - tolerance) <= val <= hi * (1 + tolerance)

    ab_xa = ab / xa if xa else 0
    bc_ab = bc / ab if ab else 0
    cd_bc = cd / bc if bc else 0
    ad_xa = abs(d - a) / xa if xa else 0

    return (
        in_range(ab_xa, 0.618, 0.618) and  # AB = 0.618 XA
        in_range(bc_ab, 0.382, 0.886) and  # BC = 0.382~0.886 AB
        in_range(cd_bc, 1.272, 1.618) and  # CD = 1.272~1.618 BC
        in_range(ad_xa, 0.786, 0.786)      # AD = 0.786 XA (D점)
    )
```

---

## 종합 구현: 피보나치 시그널 엔진

```python
import pandas as pd
import numpy as np
from dataclasses import dataclass, field


@dataclass
class FibSignal:
    current_price:    float
    nearest_support:  dict      # 가장 가까운 지지 레벨
    nearest_resist:   dict      # 가장 가까운 저항 레벨
    clusters:         list      # 클러스터 집중 구간
    extension_targets: dict     # 확장 목표가
    regime:           str       # retracement_zone / extension_zone
    action:           str
    confidence:       str


class FibonacciEngine:
    """
    스윙 포인트 자동 감지 + 되돌림/확장/클러스터 복합 분석
    """

    def __init__(self, swing_lookback: int = 20,
                 tolerance: float = 0.008):
        self.lookback  = swing_lookback
        self.tolerance = tolerance

    # ── 스윙 포인트 자동 감지 ──────────────────────────────
    def find_swing_points(self, df: pd.DataFrame) -> dict:
        high  = df['high']
        low   = df['low']
        n     = self.lookback

        swing_highs, swing_lows = [], []

        for i in range(n, len(df) - n):
            if high.iloc[i] == high.iloc[i-n:i+n+1].max():
                swing_highs.append((df.index[i], float(high.iloc[i])))
            if low.iloc[i] == low.iloc[i-n:i+n+1].min():
                swing_lows.append((df.index[i], float(low.iloc[i])))

        # 최근 유효 스윙 포인트 추출
        last_high = swing_highs[-1][1] if swing_highs else float(df['high'].max())
        last_low  = swing_lows[-1][1]  if swing_lows  else float(df['low'].min())

        # 추세 방향 판단
        trend = "up" if df['close'].iloc[-1] > df['close'].iloc[-20] \
                     else "down"

        return {
            "swing_high":   last_high,
            "swing_low":    last_low,
            "trend":        trend,
            "all_highs":    swing_highs[-5:],
            "all_lows":     swing_lows[-5:],
        }

    # ── 복합 분석 ──────────────────────────────────────────
    def analyze(self, df: pd.DataFrame) -> FibSignal:
        close  = float(df['close'].iloc[-1])
        swings = self.find_swing_points(df)

        sh = swings["swing_high"]
        sl = swings["swing_low"]
        trend = swings["trend"]

        # 되돌림 레벨
        retrace = calc_fib_retracement(sh, sl, trend)

        # 확장 레벨 (되돌림 0.382 기준)
        retrace_ratio = 0.382
        ext = calc_fib_extension(sl, sh, retrace_ratio, trend)

        # 프로젝션 (스윙 3점 기반)
        if len(swings["all_lows"]) >= 2 and len(swings["all_highs"]) >= 1:
            pa = swings["all_lows"][-2][1]
            pb = swings["all_highs"][-1][1]
            pc = swings["all_lows"][-1][1]
            proj = calc_fib_projection(pa, pb, pc, trend)
        else:
            proj = {"projections": {}}

        # 클러스터 탐지
        retrace_clean = {k: v for k, v in retrace.items()
                         if isinstance(v, float)}
        ext_clean     = {k: v for k, v in ext["targets"].items()}
        proj_clean    = proj.get("projections", {})

        clusters = find_fib_clusters(
            [retrace_clean, ext_clean, proj_clean],
            self.tolerance
        )

        # 현재가 기준 가장 가까운 지지/저항
        below = {k: v for k, v in retrace_clean.items() if v <= close}
        above = {k: v for k, v in retrace_clean.items() if v > close}

        nearest_support = (
            max(below.items(), key=lambda x: x[1])
            if below else ("none", 0)
        )
        nearest_resist  = (
            min(above.items(), key=lambda x: x[1])
            if above else ("none", float("inf"))
        )

        # 레짐 판단
        # 현재가가 0.618 이상 유지 → 확장 구간
        # 현재가가 0.618 아래 → 되돌림 구간
        retrace_618 = retrace_clean.get("0.618", sl)
        if close > retrace_618:
            regime = "extension_zone"
            action = f"확장 목표: {ext['targets'].get('1.618', 'N/A')}"
        else:
            regime = "retracement_zone"
            level_info = assess_retracement_level(close, retrace_clean)
            action     = level_info.get("action", "모니터링")

        # 신뢰도: 클러스터 집중도
        top_cluster = clusters[0] if clusters else {}
        confidence  = (
            "HIGH"   if top_cluster.get("count", 0) >= 3 else
            "MEDIUM" if top_cluster.get("count", 0) == 2 else
            "LOW"
        )

        return FibSignal(
            current_price=close,
            nearest_support={
                "level": nearest_support[0],
                "price": nearest_support[1],
                "strength": _retracement_strength(
                    float(nearest_support[0])
                    if nearest_support[0] != "none" else 0
                )
            },
            nearest_resist={
                "level": nearest_resist[0],
                "price": nearest_resist[1],
            },
            clusters=clusters[:3],        # 상위 3개 클러스터
            extension_targets=ext["targets"],
            regime=regime,
            action=action,
            confidence=confidence,
        )

    def report(self, sig: FibSignal) -> str:
        lines = [
            "=" * 56,
            "  피보나치 시그널 리포트",
            "=" * 56,
            f"  현재가        : {sig.current_price}",
            f"  구간 레짐     : {sig.regime}",
            f"  신뢰도        : {sig.confidence}",
            f"  권장 액션     : {sig.action}",
            "-" * 56,
            "  [지지 / 저항]",
            f"  직하 지지     : {sig.nearest_support['price']}  "
            f"(Fib {sig.nearest_support['level']})  "
            f"{sig.nearest_support['strength']}",
            f"  직상 저항     : {sig.nearest_resist['price']}  "
            f"(Fib {sig.nearest_resist['level']})",
            "-" * 56,
            "  [확장 목표가]",
        ]
        for k, v in sig.extension_targets.items():
            lines.append(f"    Fib {k}  →  {v}")

        lines += [
            "-" * 56,
            "  [피보나치 클러스터 (집중 구간)]",
        ]
        for c in sig.clusters:
            lines.append(
                f"    가격 {c['cluster_price']}  "
                f"강도 {c['strength']}  "
                f"({', '.join(c['labels'])})"
            )
        lines.append("=" * 56)
        return "\n".join(lines)
```

---

## 레짐 어댑티브 시스템 연동

```python
# ATR%, BB, MACD, RSI, MA 복합 신호 + 피보나치 레벨 통합
def fib_integrated_signal(composite_signal,   # CompositeSignal
                           fib_signal: FibSignal) -> dict:
    score  = composite_signal.composite_score
    regime = composite_signal.regime.value
    action = composite_signal.action

    support_level = fib_signal.nearest_support.get("level", "none")
    confidence    = fib_signal.confidence

    # 피보나치 클러스터 구간에서 복합 신호 일치 → 가중 강화
    at_key_level = support_level in ["0.382", "0.500", "0.618"]

    if at_key_level and confidence == "HIGH":
        boost = 1.5 if score > 0 else 0.7
        adj_score = round(score * boost, 2)
        action_final = "STRONG_BUY" if adj_score >= 4 else action
    else:
        adj_score    = score
        action_final = action

    return {
        "original_score":  score,
        "adjusted_score":  adj_score,
        "fib_level":       support_level,
        "fib_confidence":  confidence,
        "action_final":    action_final,
        "stop_loss":       fib_signal.nearest_support["price"],
        "target_1":        fib_signal.extension_targets.get("1.272"),
        "target_2":        fib_signal.extension_targets.get("1.618"),
    }
```

---

## 실전 주의사항

1. **스윙 포인트 선택이 핵심**: 되돌림 레벨의 정확도는 고점/저점 선택에 달려있음 — 명확한 구조적 고점/저점 사용
2. **0.618 황금비율 절대화 금지**: 시장은 0.50~0.65 범위에서 반응하는 경우가 많음 — ±0.5% 허용 오차 적용
3. **클러스터 없는 단일 레벨 신뢰도 낮음**: 반드시 2개 이상 레벨 집중 구간에서만 진입
4. **RSI + 피보나치 조합**: 0.618 지지 + RSI 과매도 동시 충족 시 가장 강한 매수 신호
5. **타임 존 단독 사용 금지**: 시간 예측은 참고용이며 가격 레벨과 반드시 결합

---

지금까지 **ATR%, 볼린저 밴드, MACD, RSI, 이동평균, 피보나치** 6개 지표 체계를 모두 다루었습니다.
다음으로 **거래량 기반 지표 (OBV, VWAP, MFI)** 또는 전체 지표를 통합한 **멀티 팩터 스코어링 대시보드** 구현을 진행할까요?