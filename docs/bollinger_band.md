# 볼린저 밴드 신호를 통한 시장 판단 방법

## 볼린저 밴드 구성

```
Upper Band  = MA(n) + k × σ
Middle Band = MA(n)          ← 기준선 (보통 20일 SMA)
Lower Band  = MA(n) - k × σ  (k = 2.0이 표준)

%B     = (Close - Lower) / (Upper - Lower)   # 밴드 내 위치 [0~1]
BW     = (Upper - Lower) / Middle × 100      # BandWidth: 밴드 폭 %
```

---

## 핵심 판단 지표: %B + BandWidth

### %B — 가격의 밴드 내 위치

| %B 값 | 의미 | 판단 |
|-------|------|------|
| > 1.0 | 상단 돌파 | 강한 상승 모멘텀 or 과매수 |
| 0.8 ~ 1.0 | 상단 근접 | 상승 압력 |
| 0.4 ~ 0.6 | 중심 | 중립 / 추세 없음 |
| 0.0 ~ 0.2 | 하단 근접 | 하락 압력 |
| < 0.0 | 하단 이탈 | 강한 하락 모멘텀 or 과매도 |

### BandWidth — 시장 변동성 상태

| BandWidth | 시장 상태 |
|-----------|-----------|
| 수축 (Squeeze) | 저변동성 → **폭발적 움직임 예고** |
| 확장 (Expansion) | 고변동성 → 추세 진행 중 |
| 정상 수준 복귀 | 변동성 정상화 → 추세 마무리 가능 |

---

## 5가지 핵심 신호 패턴

### ① Bollinger Squeeze → Breakout

```
BandWidth가 6개월 최저 수준으로 수축
→ 방향 불명 상태에서 에너지 축적
→ Upper 돌파 시 매수 / Lower 이탈 시 매도
```

```python
def detect_squeeze(bw_series: pd.Series, lookback: int = 126) -> bool:
    current_bw = bw_series.iloc[-1]
    min_bw = bw_series.rolling(lookback).min().iloc[-1]
    return current_bw <= min_bw * 1.05  # 최저점의 5% 이내
```

---

### ② %B 다이버전스 (추세 전환 신호)

```
[강세 다이버전스]
가격: 신저가 갱신
%B : 이전 저점보다 높음 (하락 모멘텀 약화)
→ 반등 가능성 ↑

[약세 다이버전스]
가격: 신고가 갱신
%B : 이전 고점보다 낮음 (상승 모멘텀 약화)
→ 조정 가능성 ↑
```

---

### ③ 밴드 워크 (Band Walk) — 추세 강도 판단

```python
def detect_band_walk(df: pd.DataFrame, window: int = 5) -> str:
    """
    연속 n봉이 상단 밴드 위 → 강한 상승 추세 (매도 자제)
    연속 n봉이 하단 밴드 아래 → 강한 하락 추세 (매수 자제)
    """
    recent = df.tail(window)
    if (recent['%B'] > 0.9).all():
        return "strong_uptrend"    # 상단 밴드 워크
    elif (recent['%B'] < 0.1).all():
        return "strong_downtrend"  # 하단 밴드 워크
    else:
        return "neutral"
```

> ⚠️ **흔한 실수**: 상단 터치 = 매도 신호로 해석 → **추세장에서 밴드 워크 발생 시 반대**

---

### ④ M-Top / W-Bottom 패턴

```
[M-Top: 천장 패턴]
1차 고점: %B > 1.0 (상단 돌파)
2차 고점: %B < 1.0 (상단 미돌파) + 가격은 유사
→ 하락 전환 신호

[W-Bottom: 바닥 패턴]
1차 저점: %B < 0.0 (하단 이탈)
2차 저점: %B > 0.0 (하단 미이탈) + 가격은 유사
→ 상승 전환 신호
```

---

### ⑤ Middle Band 방향성 판단

```python
def middle_band_signal(df: pd.DataFrame) -> str:
    mb = df['middle_band']
    slope = (mb.iloc[-1] - mb.iloc[-5]) / mb.iloc[-5] * 100

    if slope > 0.3:
        return "uptrend"       # 중심선 우상향 → 추세 추종
    elif slope < -0.3:
        return "downtrend"     # 중심선 우하향 → 공매도/현금
    else:
        return "sideways"      # 평탄 → 평균 회귀
```

---

## 레짐별 전략 매핑

```
BandWidth 수축 + 중심선 평탄    → 대기 (방향 돌파 확인 후 진입)
BandWidth 확장 + %B 상단 워크   → 추세 추종 매수 유지
BandWidth 확장 + %B 하단 워크   → 숏 or 현금
BandWidth 수축 후 급확장        → 브레이크아웃 진입
%B 0.0 이하 + BW 수축 중       → W-Bottom 탐색 (반전 준비)
```

---

## 복합 필터: BB + RSI + Volume

```python
def bb_composite_signal(row) -> str:
    pb   = row['pct_b']       # %B
    bw   = row['bandwidth']   # BandWidth
    rsi  = row['rsi']
    vol_ratio = row['vol_ratio']  # 거래량 / 20일 평균

    # 강한 매수
    if pb < 0.05 and rsi < 35 and vol_ratio > 1.5:
        return "strong_buy"    # 하단 이탈 + 과매도 + 거래량 확인

    # 강한 매도
    if pb > 0.95 and rsi > 65 and vol_ratio > 1.5:
        return "strong_sell"   # 상단 돌파 + 과매수 + 거래량 확인

    # Squeeze 브레이크아웃
    if bw < bw_threshold and pb > 0.8:
        return "breakout_long"

    return "hold"
```

---

## 구현: 핵심 계산 코드

```python
import pandas as pd
import numpy as np

def compute_bollinger(df: pd.DataFrame, 
                      period: int = 20, 
                      k: float = 2.0) -> pd.DataFrame:
    df = df.copy()
    df['middle'] = df['close'].rolling(period).mean()
    df['std']    = df['close'].rolling(period).std()
    df['upper']  = df['middle'] + k * df['std']
    df['lower']  = df['middle'] - k * df['std']
    
    # %B: 밴드 내 위치
    df['pct_b']  = (df['close'] - df['lower']) / \
                   (df['upper'] - df['lower'])
    
    # BandWidth: 변동성 지수
    df['bandwidth'] = (df['upper'] - df['lower']) / \
                       df['middle'] * 100
    
    # Squeeze 감지 (6개월 BW 최솟값 기준)
    df['bw_min_126'] = df['bandwidth'].rolling(126).min()
    df['squeeze']    = df['bandwidth'] <= df['bw_min_126'] * 1.05
    
    return df
```

---

## 실전 주의사항

1. **기간 설정**: 단기 매매 → BB(10, 1.5) / 스윙 → BB(20, 2.0) / 장기 → BB(50, 2.5)
2. **Squeeze 오신호**: 수축 후 반드시 **방향 확인 후** 진입 (방향 예측 금지)
3. **평균 회귀 vs 추세**: ADX < 20이면 평균 회귀, ADX > 25면 추세 추종 전략 선택
4. **%B 단독 사용 금지**: 반드시 거래량, RSI, ADX 중 하나 이상과 조합
5. **BandWidth 절대값**: 코스피/나스닥/개별 종목마다 기준치 상이 → 백분위수 기반 상대 비교 권장

---

`StrategyAgent`에 BB 레짐 분류를 통합