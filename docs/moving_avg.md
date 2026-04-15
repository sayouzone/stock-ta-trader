# 이동평균 기반 시장 판단 방법

## 이동평균 종류 및 특성

```python
# 단순 이동평균 (SMA) - 모든 기간 동일 가중치
SMA(n) = sum(Close, n) / n

# 지수 이동평균 (EMA) - 최근 데이터 가중치 높음
EMA(n) = Close × k + EMA_prev × (1 - k),  k = 2/(n+1)

# 가중 이동평균 (WMA) - 선형 가중치
WMA(n) = Σ(Close_i × i) / Σ(i),  i = 1..n

# 헐 이동평균 (HMA) - 지연 최소화
HMA(n) = WMA(2 × WMA(n/2) - WMA(n), sqrt(n))

# VWMA - 거래량 가중 이동평균
VWMA(n) = Σ(Close_i × Volume_i) / Σ(Volume_i)
```

| MA 종류 | 반응 속도 | 노이즈 | 적합 용도 |
|---------|-----------|--------|-----------|
| SMA | 느림 | 적음 | 추세 확인, 지지/저항 |
| EMA | 빠름 | 많음 | 진입 타이밍, 크로스오버 |
| HMA | 매우 빠름 | 적음 | 단기 추세 전환 포착 |
| VWMA | 보통 | 적음 | 거래량 기반 추세 확인 |

---

## 핵심 판단 체계 1: 정배열 / 역배열

### 이동평균 정배열 / 역배열

```
[완전 정배열 — 강한 상승 추세]
MA5 > MA20 > MA60 > MA120 > MA200
→ 단기 ~ 장기 모두 상승 방향 정렬
→ 추세 추종 매수, 눌림목 매수 전략 유효

[완전 역배열 — 강한 하락 추세]
MA5 < MA20 < MA60 < MA120 < MA200
→ 모든 구간 하락 정렬
→ 반등 시 매도, 숏 전략 유효

[혼합 배열 — 추세 전환 / 횡보 구간]
단기 정배열 + 장기 역배열 → 하락 추세 중 반등
단기 역배열 + 장기 정배열 → 상승 추세 중 조정
```

```python
def classify_ma_alignment(df: pd.DataFrame) -> str:
    ma5   = df['ma5'].iloc[-1]
    ma20  = df['ma20'].iloc[-1]
    ma60  = df['ma60'].iloc[-1]
    ma120 = df['ma120'].iloc[-1]
    ma200 = df['ma200'].iloc[-1]

    if ma5 > ma20 > ma60 > ma120 > ma200:
        return "full_bullish"         # 완전 정배열
    elif ma5 < ma20 < ma60 < ma120 < ma200:
        return "full_bearish"         # 완전 역배열
    elif ma5 > ma20 > ma60 and ma60 < ma120:
        return "short_bull_long_bear" # 단기 정배열 + 장기 역배열
    elif ma5 < ma20 < ma60 and ma60 > ma120:
        return "short_bear_long_bull" # 단기 역배열 + 장기 정배열
    else:
        return "mixed"                # 혼합 (횡보/전환 구간)
```

---

## 핵심 판단 체계 2: 골든크로스 / 데드크로스

### 크로스오버 유형별 신뢰도

```python
def detect_ma_crossover(df: pd.DataFrame) -> list[dict]:
    """
    크로스오버 감지 + 신뢰도 등급 산출
    """
    signals = []
    cross_pairs = [
        ('ma5',  'ma20',  1, "단기 크로스"),   # 신뢰도 낮음
        ('ma20', 'ma60',  2, "중기 크로스"),   # 표준 신호
        ('ma50', 'ma200', 3, "장기 크로스"),   # 가장 강한 신호
    ]

    for fast, slow, weight, label in cross_pairs:
        prev_diff = df[fast].iloc[-2] - df[slow].iloc[-2]
        curr_diff = df[fast].iloc[-1] - df[slow].iloc[-1]

        if prev_diff < 0 and curr_diff > 0:
            signals.append({
                "type":   "golden_cross",
                "pair":   label,
                "weight": weight,
            })
        elif prev_diff > 0 and curr_diff < 0:
            signals.append({
                "type":   "dead_cross",
                "pair":   label,
                "weight": weight,
            })

    return signals
```

### MA200 골든크로스 — 시장 국면 전환의 핵심

```
MA50  상향 돌파 MA200 → 강세장 전환 확인 신호 (1~3개월 선행)
MA50  하향 이탈 MA200 → 약세장 전환 확인 신호
Price 상향 돌파 MA200 → 단기 국면 전환 (MA50 크로스 선행 신호)
```

---

## 핵심 판단 체계 3: 가격 대비 MA 위치

```python
def price_vs_ma_signal(df: pd.DataFrame) -> dict:
    """
    현재가가 각 이동평균 대비 얼마나 위/아래인지 % 산출
    → 이격도 기반 과열/침체 판단
    """
    close = df['close'].iloc[-1]
    result = {}

    for period in [20, 60, 120, 200]:
        ma_key = f'ma{period}'
        ma_val = df[ma_key].iloc[-1]

        # 이격도 (Disparity)
        disparity = (close - ma_val) / ma_val * 100
        result[ma_key] = {
            "disparity": round(disparity, 2),
            "signal":    _disparity_signal(disparity, period)
        }

    return result


def _disparity_signal(disparity: float, period: int) -> str:
    # 기간이 길수록 이격도 임계값 확대
    threshold = {20: 5, 60: 8, 120: 12, 200: 15}
    t = threshold.get(period, 10)

    if disparity > t:
        return "overheated"    # 과열 — 단기 조정 가능성
    elif disparity < -t:
        return "oversold"      # 침체 — 반등 가능성
    elif disparity > 0:
        return "above_ma"      # MA 위 — 강세
    else:
        return "below_ma"      # MA 아래 — 약세
```

---

## 핵심 판단 체계 4: MA 기울기 (Slope) 분석

```python
def ma_slope_analysis(df: pd.DataFrame, 
                       period: int = 20,
                       lookback: int = 5) -> dict:
    """
    MA 기울기로 추세 강도 및 방향 정량화
    """
    ma = df[f'ma{period}']
    
    # 기울기 (n봉 전 대비 변화율)
    slope_pct = (ma.iloc[-1] - ma.iloc[-lookback]) \
                / ma.iloc[-lookback] * 100

    # 기울기 가속도 (2차 미분)
    prev_slope = (ma.iloc[-lookback] - ma.iloc[-lookback*2]) \
                 / ma.iloc[-lookback*2] * 100
    acceleration = slope_pct - prev_slope

    return {
        "slope":        round(slope_pct, 3),
        "acceleration": round(acceleration, 3),
        "trend":        _slope_to_trend(slope_pct),
        "momentum":     "accelerating" if acceleration > 0 
                        else "decelerating"
    }


def _slope_to_trend(slope: float) -> str:
    if slope > 1.0:    return "strong_up"
    elif slope > 0.3:  return "mild_up"
    elif slope > -0.3: return "flat"
    elif slope > -1.0: return "mild_down"
    else:              return "strong_down"
```

---

## 핵심 판단 체계 5: MA 지지/저항 강도 평가

```python
def ma_support_resistance(df: pd.DataFrame, 
                           tolerance: float = 0.02) -> dict:
    """
    현재가가 주요 MA에 근접 시 지지/저항 강도 산출
    이전 터치 횟수가 많을수록 신뢰도 높음
    """
    close   = df['close']
    signals = {}

    for period in [20, 60, 120, 200]:
        ma     = df[f'ma{period}']
        ma_cur = ma.iloc[-1]
        p_cur  = close.iloc[-1]

        # 근접도 확인
        proximity = abs(p_cur - ma_cur) / ma_cur

        if proximity <= tolerance:
            # 이전 N봉 중 MA 지지 횟수 카운트
            touch_count = sum(
                abs(close.iloc[i] - ma.iloc[i]) / ma.iloc[i] <= tolerance
                for i in range(-50, -1)
            )
            signals[f'ma{period}'] = {
                "proximity_pct": round(proximity * 100, 2),
                "touch_count":   touch_count,
                "strength":      "strong" if touch_count >= 3 else "weak",
                "position":      "at_support" if p_cur > ma_cur 
                                 else "at_resistance"
            }

    return signals
```

---

## 핵심 판단 체계 6: 리본 지표 (MA Ribbon)

```python
def compute_ma_ribbon(df: pd.DataFrame) -> dict:
    """
    MA10 ~ MA100까지 10개 MA 간격으로 리본 구성
    → 리본 확장/수축으로 추세 강도 판단
    """
    periods = [10, 20, 30, 40, 50, 60, 70, 80, 90, 100]
    ma_values = {p: df['close'].ewm(span=p).mean().iloc[-1]
                 for p in periods}

    # 리본 폭 (최상단 MA - 최하단 MA) / 중간값
    ribbon_width = (max(ma_values.values()) - 
                    min(ma_values.values())) / \
                    ma_values[50] * 100

    # 리본 방향 (모든 MA가 같은 방향으로 기울어지는지)
    slopes = []
    for p in periods:
        ma = df['close'].ewm(span=p).mean()
        slopes.append(ma.iloc[-1] - ma.iloc[-5])

    all_positive = all(s > 0 for s in slopes)
    all_negative = all(s < 0 for s in slopes)

    return {
        "ribbon_width":    round(ribbon_width, 2),
        "ribbon_direction": "aligned_bull"  if all_positive else
                            "aligned_bear"  if all_negative else
                            "mixed",
        "trend_strength":  "strong" if ribbon_width > 5 else
                           "moderate" if ribbon_width > 2 else
                           "weak"
    }
```

---

## 종합 MA 신호 스코어링 시스템

```python
def ma_composite_score(df: pd.DataFrame) -> dict:
    """
    -10 ~ +10 통합 스코어
    """
    score = 0
    details = {}

    # ① 정배열 상태 (+3 / -3)
    alignment = classify_ma_alignment(df)
    alignment_score = {
        "full_bullish":         +3,
        "short_bull_long_bull": +2,
        "short_bull_long_bear": +1,
        "mixed":                 0,
        "short_bear_long_bull": -1,
        "short_bear_long_bear": -2,
        "full_bearish":         -3,
    }.get(alignment, 0)
    score += alignment_score
    details['alignment'] = alignment

    # ② 크로스오버 누적 가중치 (+1~+3 / -1~-3)
    crossovers = detect_ma_crossover(df)
    cross_score = sum(
        c['weight'] if c['type'] == 'golden_cross'
        else -c['weight']
        for c in crossovers
    )
    score += max(-3, min(3, cross_score))
    details['crossovers'] = crossovers

    # ③ MA200 이격도 (+1 / -1)
    close  = df['close'].iloc[-1]
    ma200  = df['ma200'].iloc[-1]
    if close > ma200:  score += 1
    else:              score -= 1
    details['vs_ma200'] = round((close - ma200) / ma200 * 100, 2)

    # ④ MA20 기울기 (+1~+2 / -1~-2)
    slope_info = ma_slope_analysis(df, period=20)
    slope_score = {
        "strong_up":   +2,
        "mild_up":     +1,
        "flat":         0,
        "mild_down":   -1,
        "strong_down": -2,
    }.get(slope_info['trend'], 0)
    score += slope_score
    details['slope'] = slope_info

    # ⑤ 리본 방향 (+1 / -1)
    ribbon = compute_ma_ribbon(df)
    if ribbon['ribbon_direction'] == 'aligned_bull':   score += 1
    elif ribbon['ribbon_direction'] == 'aligned_bear': score -= 1
    details['ribbon'] = ribbon

    return {
        "score":   score,
        "signal":  "strong_buy"  if score >= 6  else
                   "buy"         if score >= 3  else
                   "neutral"     if score >= -2 else
                   "sell"        if score >= -5 else
                   "strong_sell",
        "details": details
    }
```

---

## 레짐별 MA 전략 매핑

```
시장 레짐                 MA 전략
───────────────────────────────────────────────────────────
완전 정배열               MA20 눌림목 매수 (지지 확인 후)
완전 역배열               MA20 반등 매도 (저항 확인 후)
MA50/200 골든크로스 직후  중장기 매수 진입 (추세 초기)
MA 혼합 배열              방향 확인 전까지 관망
이격도 과열 (>+15%)       부분 익절 / 신규 진입 자제
이격도 침체 (<-15%)       분할 매수 준비
리본 수축 + 평탄화        추세 소멸 → 횡보 전략 전환
```

---

## 실전 주의사항

1. **SMA vs EMA 선택**: 지지/저항선은 SMA, 진입 타이밍은 EMA — 혼용 시 기준 명확히
2. **크로스오버 후행성**: MA50/200 크로스는 확인 신호이지 예측 신호가 아님 — 이미 30~40% 이동 후 발생
3. **이격도 임계값**: 코스피 대형주 ≠ 코스닥 소형주 — **종목별 역사적 분포 기반 캘리브레이션 필수**
4. **리본 교차 구간**: MA가 뒤엉키는 구간은 추세 전환의 노이즈 구간 — 포지션 축소
5. **멀티 타임프레임**: 주봉 정배열 확인 후 일봉 진입 타이밍 포착 — 방향 일치 시 신뢰도 대폭 상승

---

**ATR%, 볼린저 밴드, MACD, RSI, 이동평균** 다섯 가지 지표를 통합한 **레짐 어댑티브 복합 신호 시스템** 전체 설계 및 구현 필요