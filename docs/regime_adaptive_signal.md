정상 동작 확인되었습니다. 전체 아키텍처를 정리하면 다음과 같습니다.

---

## 시스템 전체 아키텍처

```
OHLCV DataFrame
      │
      ▼
┌─────────────────────────────────────────────┐
│           RegimeAdaptiveSignalEngine        │
│                                             │
│  ① 지표 계산 (prepare)                        │
│     ATRCalculator   → atr, atr_pct          │
│     BollingerCalc   → %B, BW, squeeze       │
│     MACDCalculator  → hist, crossover       │
│     RSICalculator   → rsi, divergence       │
│     MACalculator    → alignment, slope      │
│                                             │
│  ② 레짐 분류 (RegimeClassifier)               │
│     ADX + ATR% + MA정배열 + BB Squeeze        │
│     → 8개 레짐 중 하나 선택                     │
│                                             │
│  ③ 가중치 조정 (WeightEngine)                 │
│     레짐별 5개 지표 가중치 동적 배정               │
│                                             │
│  ④ 복합 스코어 (CompositeScoreEngine)         │
│     각 지표 점수 정규화 [-1,+1]                 │
│     → 가중합 × 10 = [-10, +10]               │
│                                            │
│  ⑤ 액션 결정 (ActionDecider)                 │
│     스코어 + 레짐 → 액션                       │
│     ATR 기반 손절/익절/포지션 비율                │
└─────────────────────────────────────────────┘
      │
      ▼
  CompositeSignal
  (action, score, confidence,
   stop_pct, tp_pct, pos_size_pct)
```

---

## 레짐별 가중치 전략

| 레짐 | ATR | BB | MACD | RSI | MA | 핵심 논리 |
|------|-----|----|------|-----|----|-----------|
| STRONG_BULL | 5% | 15% | **30%** | 20% | **30%** | 추세 지표 극대화 |
| MILD_BULL | 10% | 20% | **25%** | **25%** | 20% |  |
| SIDEWAYS | 10% | **30%** | 15% | **35%** | 10% | 역추세 지표 극대화 |
| MILD_BEAR | 10% | 20% | **25%** | **25%** | 20% |  |
| STRONG_BEAR | 5% | 15% | **30%** | 20% | **30%** | 추세 지표 극대화 |
| HIGH_VOL | **30%** | 20% | 10% | 20% | 20% | 변동성 리스크 우선 |
| SQUEEZE | 15% | **40%** | 15% | 20% | 10% | BB 브레이크아웃 집중 |
| BREAKOUT | **20%** | **30%** | 20% | 15% | 15% | 방향 확인 중시 |

---

## `ta_trader` 통합 방법

```python
# StrategyAgent에서 사용
from regime_adaptive_signal_system import RegimeAdaptiveSignalEngine

engine = RegimeAdaptiveSignalEngine()

# 단일 종목
signal = engine.analyze(df)
print(signal.action, signal.composite_score)

# 다종목 스캔 (유니버스 전체)
result_df = engine.scan({"005930": df_samsung, "035720": df_kakao})
top_picks = result_df[result_df['score'] > 3]
```

---

추가로 **백테스트 프레임워크 연동**, **멀티 타임프레임 확장**, **실시간 스트리밍 적용** 구현이 필요