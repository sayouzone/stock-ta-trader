# MACD 히스토그램 및 크로스오버 기반 시장 판단 방법

## MACD 구성 요소

```python
MACD Line      = EMA(12) - EMA(26)          # 빠른 신호
Signal Line    = EMA(MACD, 9)               # 느린 신호 (트리거)
Histogram      = MACD Line - Signal Line    # 모멘텀 강도
```

---

## 히스토그램 상태 분류 (8단계 모멘텀 사이클)

```
강도  방향  히스토그램 상태        시장 해석
────────────────────────────────────────────────
 +   증가   양수 & 증가 중    →   상승 모멘텀 가속   ★ 추세 추종 매수
 +   감소   양수 & 감소 중    →   상승 모멘텀 약화       조기 청산 준비
 -   감소   음수 & 증가 중    →   하락 모멘텀 가속   ★ 추세 추종 매도
 -   증가   음수 & 감소 중    →   하락 모멘텀 약화       반등 준비
```

```python
def classify_histogram_state(hist: pd.Series) -> str:
    cur  = hist.iloc[-1]
    prev = hist.iloc[-2]

    if cur > 0 and cur > prev:
        return "bull_accelerating"    # 상승 가속
    elif cur > 0 and cur < prev:
        return "bull_decelerating"    # 상승 약화
    elif cur > 0 and cur == prev:
        return "bull_stable"
    elif cur < 0 and abs(cur) > abs(prev):
        return "bear_accelerating"    # 하락 가속
    elif cur < 0 and abs(cur) < abs(prev):
        return "bear_decelerating"    # 하락 약화
    else:
        return "neutral"
```

---

## 크로스오버 신호 유형

### ① 기본 크로스오버

```python
def detect_crossover(macd: pd.Series, signal: pd.Series) -> str:
    """
    골든 크로스: MACD가 Signal을 아래→위 돌파  → 매수
    데드 크로스: MACD가 Signal을 위→아래 돌파  → 매도
    """
    prev_diff = macd.iloc[-2] - signal.iloc[-2]
    curr_diff = macd.iloc[-1] - signal.iloc[-1]

    if prev_diff < 0 and curr_diff > 0:
        return "golden_cross"    # Histogram 0선 상향 돌파
    elif prev_diff > 0 and curr_diff < 0:
        return "dead_cross"      # Histogram 0선 하향 돌파
    else:
        return "no_cross"
```

### ② 제로라인 크로스오버 (MACD Line 기준)

```
MACD Line이 0선 상향 돌파  →  EMA12 > EMA26 확정  →  중기 상승 전환
MACD Line이 0선 하향 돌파  →  EMA12 < EMA26 확정  →  중기 하락 전환
```

```python
def zeroline_cross(macd: pd.Series) -> str:
    if macd.iloc[-2] < 0 and macd.iloc[-1] > 0:
        return "bullish_zeroline"   # 강도 높은 매수 확인 신호
    elif macd.iloc[-2] > 0 and macd.iloc[-1] < 0:
        return "bearish_zeroline"   # 강도 높은 매도 확인 신호
    return "none"
```

---

## MACD 다이버전스 — 추세 전환의 핵심

### 강세 다이버전스 (Bullish Divergence)

```
가격:  저점1 > 저점2  (신저가 갱신)
MACD:  저점1 < 저점2  (하락 모멘텀 약화)
→ 상승 전환 가능성 ↑
```

### 약세 다이버전스 (Bearish Divergence)

```
가격:  고점1 < 고점2  (신고가 갱신)
MACD:  고점1 > 고점2  (상승 모멘텀 약화)
→ 하락 전환 가능성 ↑
```

```python
def detect_divergence(price: pd.Series, 
                      macd: pd.Series, 
                      lookback: int = 20) -> str:
    p  = price.iloc[-lookback:]
    m  = macd.iloc[-lookback:]

    p_min_idx = p.idxmin()
    m_min_idx = m.idxmin()

    # 가격 신저가 but MACD 저점은 더 높음
    if p.iloc[-1] < p.min() * 1.02:          # 가격: 최저 근접
        if m.iloc[-1] > m[m_min_idx] * 0.8:  # MACD: 이전 저점보다 높음
            return "bullish_divergence"

    # 가격 신고가 but MACD 고점은 더 낮음
    if p.iloc[-1] > p.max() * 0.98:
        if m.iloc[-1] < m[m.idxmax()] * 0.8:
            return "bearish_divergence"

    return "none"
```

---

## 신호 강도 스코어링

```python
def macd_signal_score(row) -> int:
    """
    -4 ~ +4 점수로 매수/매도 강도 산출
    """
    score = 0

    hist        = row['histogram']
    hist_prev   = row['histogram_prev']
    macd_val    = row['macd']
    signal_val  = row['signal']
    divergence  = row['divergence']

    # 히스토그램 방향 (+1 / -1)
    if hist > hist_prev:   score += 1
    elif hist < hist_prev: score -= 1

    # 크로스오버 (+2 / -2)
    if row['crossover'] == 'golden_cross': score += 2
    elif row['crossover'] == 'dead_cross': score -= 2

    # 제로라인 위치 (+1 / -1)
    if macd_val > 0:  score += 1
    elif macd_val < 0: score -= 1

    # 다이버전스 (+2 / -2: 강한 전환 신호)
    if divergence == 'bullish_divergence':  score += 2
    elif divergence == 'bearish_divergence': score -= 2

    return score  # +3 이상: 강매수 / -3 이하: 강매도
```

---

## 레짐별 MACD 해석 전략

```
시장 레짐              MACD 활용법
──────────────────────────────────────────────────────
추세장  (ADX > 25)  →  크로스오버 + 제로라인 돌파 추종
횡보장  (ADX < 20)  →  다이버전스 위주 / 크로스오버 역추세
고변동  (ATR% > 4%) →  히스토그램 방향 전환만 사용 (노이즈 필터)
저변동  (BB Squeeze)→  크로스오버 대기 후 진입 타이밍 포착
```

---

## 종합 구현 코드

```python
import pandas as pd

def compute_macd(df: pd.DataFrame,
                 fast: int = 12,
                 slow: int = 26,
                 signal: int = 9) -> pd.DataFrame:
    df = df.copy()
    ema_fast = df['close'].ewm(span=fast, adjust=False).mean()
    ema_slow = df['close'].ewm(span=slow, adjust=False).mean()

    df['macd']      = ema_fast - ema_slow
    df['signal']    = df['macd'].ewm(span=signal, adjust=False).mean()
    df['histogram'] = df['macd'] - df['signal']

    # 전봉 히스토그램
    df['hist_prev'] = df['histogram'].shift(1)

    # 크로스오버
    df['crossover'] = df.apply(
        lambda r: 'golden_cross' 
            if r['hist_prev'] < 0 and r['histogram'] > 0
            else ('dead_cross' 
                if r['hist_prev'] > 0 and r['histogram'] < 0 
                else 'none'),
        axis=1
    )

    # 제로라인 크로스 (MACD Line 기준)
    df['zero_cross'] = df.apply(
        lambda r: 'bullish' 
            if df['macd'].shift(1)[r.name] < 0 and r['macd'] > 0
            else ('bearish' 
                if df['macd'].shift(1)[r.name] > 0 and r['macd'] < 0 
                else 'none'),
        axis=1
    )

    # 히스토그램 상태
    df['hist_state'] = df.apply(
        lambda r: classify_histogram_state(
            df['histogram'].loc[:r.name]
        ), axis=1
    )

    return df
```

---

## 실전 주의사항

1. **후행성 문제**: MACD는 본질적으로 후행 지표 → **진입보다 추세 확인**에 활용
2. **횡보장 가짜 신호**: ADX 필터 없이 크로스오버만 추종 시 Whipsaw 다발
3. **파라미터 최적화**: 단기(5,13,5) / 표준(12,26,9) / 장기(19,39,9) 전략별 구분
4. **다이버전스 단독 진입 금지**: 반드시 거래량, BB, RSI 중 하나 이상과 교차 확인
5. **히스토그램 1봉 전환에 과반응 주의**: 2~3봉 연속 방향 전환 확인 후 신뢰도 상승

---

ATR%, 볼린저 밴드, MACD 세 가지를 통합한 **레짐 어댑티브 복합 신호 시스템** 구현이 필요