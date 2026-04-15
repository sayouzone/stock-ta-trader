# RSI 기반 과매수/과매도 신호로 시장 판단하는 방법

## RSI 구성 원리

```python
RS  = Average Gain(n) / Average Loss(n)
RSI = 100 - (100 / (1 + RS))

# Wilder 스무딩 (표준)
avg_gain = prev_avg_gain * (n-1)/n + current_gain * 1/n
avg_loss = prev_avg_loss * (n-1)/n + current_loss * 1/n
```

> 범위: **0 ~ 100** / 기준 기간: **14일 (표준)**

---

## 핵심 임계값 체계

### 표준 임계값

| RSI 범위 | 시장 상태 | 전략 방향 |
|----------|-----------|-----------|
| > 80 | 극단 과매수 | 강한 매도 신호 or 추세 가속 |
| 70 ~ 80 | 과매수 | 부분 청산 / 신규 매수 자제 |
| 55 ~ 70 | 강세 구간 | 상승 추세 추종 유지 |
| 45 ~ 55 | 중립 | 방향성 대기 |
| 30 ~ 45 | 약세 구간 | 하락 추세 추종 유지 |
| 20 ~ 30 | 과매도 | 부분 매수 / 신규 매도 자제 |
| < 20 | 극단 과매도 | 강한 매수 신호 or 추세 가속 |

### 레짐별 임계값 재조정

```python
def get_rsi_thresholds(regime: str) -> dict:
    """
    추세장에서는 임계값 비대칭 조정
    → 상승 추세: 과매도 기준 상향 (50/70)
    → 하락 추세: 과매수 기준 하향 (30/50)
    """
    thresholds = {
        "bull_trend":  {"oversold": 40, "overbought": 80},  # 상승장
        "bear_trend":  {"oversold": 20, "overbought": 60},  # 하락장
        "sideways":    {"oversold": 30, "overbought": 70},  # 횡보장 (표준)
        "high_vol":    {"oversold": 25, "overbought": 75},  # 고변동
    }
    return thresholds.get(regime, thresholds["sideways"])
```

---

## 5가지 핵심 신호 패턴

### ① 과매수/과매도 단순 신호

```python
def rsi_basic_signal(rsi: float, 
                     overbought: float = 70, 
                     oversold: float = 30) -> str:
    if rsi >= overbought:
        return "overbought"    # 매도 고려
    elif rsi <= oversold:
        return "oversold"      # 매수 고려
    elif rsi >= 55:
        return "bullish_zone"  # 강세 구간
    elif rsi <= 45:
        return "bearish_zone"  # 약세 구간
    else:
        return "neutral"
```

---

### ② RSI 다이버전스 — 추세 전환 핵심 신호

```
[강세 다이버전스 (Bullish Divergence)]
가격: 신저가 갱신      ↘ ↘
RSI : 저점 높아짐      ↘ ↗  ← 하락 모멘텀 소진
→ 상승 반전 가능성 ↑↑

[약세 다이버전스 (Bearish Divergence)]
가격: 신고가 갱신      ↗ ↗
RSI : 고점 낮아짐      ↗ ↘  ← 상승 모멘텀 소진
→ 하락 반전 가능성 ↑↑

[히든 강세 다이버전스 (Hidden Bullish)]
가격: 저점 높아짐      ↘ ↗  ← 눌림목
RSI : 신저가 갱신      ↘ ↘
→ 상승 추세 지속 확인

[히든 약세 다이버전스 (Hidden Bearish)]
가격: 고점 낮아짐      ↗ ↘  ← 되돌림
RSI : 신고가 갱신      ↗ ↗
→ 하락 추세 지속 확인
```

```python
def detect_rsi_divergence(price: pd.Series, 
                           rsi: pd.Series,
                           lookback: int = 20) -> str:
    p = price.iloc[-lookback:]
    r = rsi.iloc[-lookback:]

    p_cur, p_prev_low  = p.iloc[-1], p.min()
    r_cur, r_prev_low  = r.iloc[-1], r.min()
    p_prev_high        = p.max()
    r_prev_high        = r.max()

    # 강세 다이버전스: 가격 신저 but RSI 저점 상승
    if p_cur <= p_prev_low * 1.02 and r_cur > r_prev_low + 5:
        return "bullish_divergence"

    # 약세 다이버전스: 가격 신고 but RSI 고점 하락
    if p_cur >= p_prev_high * 0.98 and r_cur < r_prev_high - 5:
        return "bearish_divergence"

    # 히든 강세: 가격 저점 상승 but RSI 저점 하락
    if p_cur > p_prev_low * 1.05 and r_cur < r_prev_low:
        return "hidden_bullish"

    # 히든 약세: 가격 고점 하락 but RSI 고점 상승
    if p_cur < p_prev_high * 0.95 and r_cur > r_prev_high:
        return "hidden_bearish"

    return "none"
```

---

### ③ RSI 50선 크로스 — 추세 전환 확인

```python
def rsi_midline_cross(rsi: pd.Series) -> str:
    """
    50선 상향 돌파 → 매수 우위 전환 (중기 추세 상승)
    50선 하향 돌파 → 매도 우위 전환 (중기 추세 하락)
    """
    prev = rsi.iloc[-2]
    curr = rsi.iloc[-1]

    if prev < 50 and curr >= 50:
        return "bullish_cross"    # 상승 추세 전환 확인
    elif prev > 50 and curr <= 50:
        return "bearish_cross"    # 하락 추세 전환 확인
    elif curr > 50:
        return "above_midline"    # 강세 구간 유지
    else:
        return "below_midline"    # 약세 구간 유지
```

---

### ④ RSI 스윙 실패 패턴 (Swing Failure Pattern)

```
[매수 SFP]
RSI가 과매도(30) 이하 진입     ① 저점 A
RSI 반등 후 다시 하락          ② 반등 고점 B
RSI가 A 고점(B)을 상향 돌파    ③ 돌파 확인
→ 이전 저점 방어 성공 → 강한 매수 신호

[매도 SFP]
RSI가 과매수(70) 이상 진입     ① 고점 A
RSI 하락 후 다시 상승          ② 되돌림 저점 B
RSI가 A 저점(B)을 하향 돌파    ③ 돌파 확인
→ 이전 고점 방어 실패 → 강한 매도 신호
```

```python
def detect_swing_failure(rsi: pd.Series,
                          ob: float = 70,
                          os: float = 30) -> str:
    r = rsi.iloc[-5:]  # 최근 5봉 기준

    # 매수 SFP
    if (r.iloc[0] < os and           # 과매도 진입
        r.iloc[1] > r.iloc[0] and    # 반등
        r.iloc[2] < r.iloc[1] and    # 재하락
        r.iloc[-1] > r.iloc[1]):     # 반등 고점 돌파
        return "buy_sfp"

    # 매도 SFP
    if (r.iloc[0] > ob and           # 과매수 진입
        r.iloc[1] < r.iloc[0] and    # 하락
        r.iloc[2] > r.iloc[1] and    # 재상승
        r.iloc[-1] < r.iloc[1]):     # 하락 저점 돌파
        return "sell_sfp"

    return "none"
```

---

### ⑤ RSI 추세선 이탈 (Trendline Break)

```python
def rsi_trendline_break(rsi: pd.Series, 
                         window: int = 14) -> str:
    """
    RSI 자체에 추세선을 그어 이탈 시 조기 신호 포착
    → 가격보다 RSI 추세선이 먼저 이탈하는 경우 선행 신호
    """
    r = rsi.iloc[-window:]
    x = range(len(r))

    # 선형 회귀로 추세선 기울기 산출
    slope = np.polyfit(x, r.values, 1)[0]

    curr   = r.iloc[-1]
    fitted = np.polyval(np.polyfit(x, r.values, 1), len(r)-1)

    if slope > 0 and curr > fitted + 3:
        return "uptrend_breakout"     # RSI 상향 이탈
    elif slope < 0 and curr < fitted - 3:
        return "downtrend_breakdown"  # RSI 하향 이탈
    return "none"
```

---

## RSI 신호 강도 스코어링

```python
def rsi_composite_score(row) -> int:
    """
    -6 ~ +6 점수로 매수/매도 강도 산출
    """
    score = 0
    rsi   = row['rsi']
    div   = row['divergence']
    mid   = row['midline_cross']
    sfp   = row['swing_failure']

    # ① 과매수/과매도 위치 (-2 ~ +2)
    if rsi < 25:    score += 2
    elif rsi < 35:  score += 1
    elif rsi > 75:  score -= 2
    elif rsi > 65:  score -= 1

    # ② 50선 크로스 (-1 ~ +1)
    if mid == "bullish_cross":   score += 1
    elif mid == "bearish_cross": score -= 1
    elif mid == "above_midline": score += 0.5
    elif mid == "below_midline": score -= 0.5

    # ③ 다이버전스 (-2 ~ +2)
    if div == "bullish_divergence":  score += 2
    elif div == "bearish_divergence": score -= 2
    elif div == "hidden_bullish":    score += 1
    elif div == "hidden_bearish":    score -= 1

    # ④ 스윙 실패 패턴 (-2 ~ +2)
    if sfp == "buy_sfp":   score += 2
    elif sfp == "sell_sfp": score -= 2

    return round(score)
    # +4 이상 → 강한 매수
    # -4 이하 → 강한 매도
    # -2 ~ +2 → 중립 / 대기
```

---

## 종합 구현 코드

```python
import pandas as pd
import numpy as np

def compute_rsi(df: pd.DataFrame, period: int = 14) -> pd.DataFrame:
    df    = df.copy()
    delta = df['close'].diff()

    gain  = delta.clip(lower=0)
    loss  = -delta.clip(upper=0)

    # Wilder 스무딩 (EWM 방식)
    avg_gain = gain.ewm(alpha=1/period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1/period, adjust=False).mean()

    rs          = avg_gain / avg_loss
    df['rsi']   = 100 - (100 / (1 + rs))

    # 신호 계산
    df['rsi_signal']     = df['rsi'].apply(rsi_basic_signal)
    df['midline_cross']  = rsi_midline_cross(df['rsi'])

    # 다이버전스 (롤링 20봉)
    df['divergence'] = "none"
    for i in range(20, len(df)):
        df.iloc[i, df.columns.get_loc('divergence')] = \
            detect_rsi_divergence(
                df['close'].iloc[i-20:i+1],
                df['rsi'].iloc[i-20:i+1]
            )

    # 스윙 실패 패턴
    df['swing_failure'] = "none"
    for i in range(5, len(df)):
        df.iloc[i, df.columns.get_loc('swing_failure')] = \
            detect_swing_failure(df['rsi'].iloc[i-5:i+1])

    # 복합 스코어
    df['rsi_score'] = df.apply(rsi_composite_score, axis=1)

    return df
```

---

## 레짐별 RSI 전략 매핑

```
시장 레짐                RSI 활용 전략
──────────────────────────────────────────────────────────
추세장  (ADX > 25)  →  50선 크로스 + 히든 다이버전스 추세 추종
횡보장  (ADX < 20)  →  30/70 과매수/과매도 역추세 매매
BB Squeeze          →  RSI 50선 방향으로 브레이크아웃 방향 예측
고변동  (ATR% > 4%) →  스윙 실패 패턴만 사용 (노이즈 필터)
하락장  (MA 정배열 역전) → 임계값 하향 조정 (20/60) + 약세 다이버전스 우선
```

---

## 실전 주의사항

1. **단독 사용 금지**: RSI 30 = 무조건 매수가 아님 → **하락 추세 중 30 도달은 추가 하락 가능**
2. **기간 파라미터**: 단기(7) 민감 / 표준(14) 균형 / 장기(21) 안정 → 전략 타임프레임과 일치
3. **다이버전스 확인봉**: 신호 발생 후 **최소 1~2봉 방향 확인** 후 진입
4. **SFP 오신호**: 변동성 급등 구간에서 빈번 발생 → ATR% 필터 병행
5. **멀티 타임프레임**: 일봉 RSI + 주봉 RSI 방향 일치 시 신뢰도 대폭 상승

---

**ATR%, 볼린저 밴드, MACD, RSI** 네 가지 지표를 통합한 **레짐 어댑티브 복합 신호 시스템** 전체 아키텍처 설계 및 구현이 필요