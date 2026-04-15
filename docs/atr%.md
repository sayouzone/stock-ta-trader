# ATR% 임계값을 통한 시장 판단 방법

## ATR%란?

**ATR% (Average True Range Percentage)** = `ATR(n) / Close Price × 100`

절대값인 ATR을 주가 대비 퍼센트로 정규화한 지표로, 종목/시장 간 **변동성 비교**가 가능해집니다.

---

## 시장 국면 판단 임계값 체계

### 1. 변동성 레짐 분류

| ATR% 범위 | 시장 국면 | 특징 |
|-----------|-----------|------|
| < 1.5% | **저변동 / 횡보** | 좁은 레인지, 추세 부재 |
| 1.5% ~ 3.0% | **정상 변동 / 추세** | 트렌드 팔로잉 유리 |
| 3.0% ~ 5.0% | **고변동 / 모멘텀** | 브레이크아웃, 변동성 거래 |
| > 5.0% | **극단 변동 / 위기** | 리스크 축소, 포지션 縮小 |

> 임계값은 **시장(코스피/나스닥)** 및 **종목 섹터**에 따라 캘리브레이션 필요

---

## 전략별 ATR% 활용

### ① 레짐 기반 전략 전환 (Regime-Adaptive)

```python
def classify_regime(atr_pct: float) -> str:
    if atr_pct < 1.5:
        return "mean_reversion"   # 볼린저밴드 반전, RSI 역추세
    elif atr_pct < 3.0:
        return "trend_following"  # 이동평균 추세 추종
    elif atr_pct < 5.0:
        return "breakout"         # 변동성 브레이크아웃
    else:
        return "risk_off"         # 현금 비중 확대
```

### ② 동적 손절/익절 설정

```python
# ATR% 기반 손절 배수 조정
def get_stop_multiplier(atr_pct: float) -> float:
    if atr_pct < 1.5:
        return 1.5   # 타이트한 손절
    elif atr_pct < 3.0:
        return 2.0   # 표준
    elif atr_pct < 5.0:
        return 2.5   # 넓은 손절 (노이즈 회피)
    else:
        return 3.0   # 극단 변동성 대응

stop_loss = entry_price - (atr * get_stop_multiplier(atr_pct))
```

### ③ 포지션 사이징 연동

```python
# 변동성이 높을수록 포지션 축소 (Fixed Fractional + ATR%)
def position_size(capital, risk_pct, atr, atr_pct, price):
    # ATR%가 높을수록 리스크 비율 축소
    adjusted_risk = risk_pct * (2.0 / max(atr_pct, 0.5))
    adjusted_risk = min(adjusted_risk, risk_pct)  # 상한 캡
    
    risk_amount = capital * adjusted_risk
    stop_distance = atr * 2.0
    shares = risk_amount / (stop_distance)
    return shares
```

---

## ATR% 임계값 캘리브레이션 방법

### 백분위수 기반 동적 임계값

```python
import pandas as pd
import numpy as np

def dynamic_atr_threshold(atr_pct_series: pd.Series, 
                           window: int = 252) -> dict:
    """
    과거 1년 ATR% 분포 기반 동적 임계값 산출
    """
    recent = atr_pct_series.rolling(window).quantile
    return {
        "low":    atr_pct_series.rolling(window).quantile(0.25).iloc[-1],
        "normal": atr_pct_series.rolling(window).quantile(0.50).iloc[-1],
        "high":   atr_pct_series.rolling(window).quantile(0.75).iloc[-1],
        "extreme":atr_pct_series.rolling(window).quantile(0.90).iloc[-1],
    }
```

→ 고정 임계값보다 **현재 시장 상태에 적응적**으로 동작

---

## 복합 필터링: ATR% + ADX 조합

```
ATR% 높음 + ADX > 25 → 강한 추세 + 고변동 → 추세 추종 진입
ATR% 낮음 + ADX < 20 → 저변동 횡보          → 평균 회귀 전략
ATR% 급등 + ADX 낮음  → 방향성 없는 변동성   → 관망 (노이즈)
```

---

## 실전 주의사항

1. **ATR 기간**: 단기(7~10일)는 노이즈 민감, 장기(20~30일)는 반응 지연 → **14일이 표준**, 전략에 따라 조정
2. **갭 처리**: ATR은 갭을 포함하므로 실적발표/이벤트 시즌엔 임계값을 상향 조정
3. **섹터 차이**: 바이오/2차전지는 ATR% 자체가 높으므로 **종목별 Z-score 정규화** 권장
4. **임계값 히스테리시스**: 레짐 전환 시 노이즈 방지를 위해 확인봉(2~3일) 조건 추가
