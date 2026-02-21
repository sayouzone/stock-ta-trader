# TA Trader - 아키텍처 문서

## 레이어 구조

```
┌──────────────────────────────────────────┐
│  CLI (main.py)                           │  ← Click 기반 진입점
├──────────────────────────────────────────┤
│  Facade (analyzer.py)                    │  ← MonthlyTradingAnalyzer
├──────────┬──────────┬────────────────────┤
│  Data    │Indicators│ Signals  │  Risk   │  ← 도메인 레이어
│  Layer   │  Layer   │  Layer   │  Layer  │
├──────────┴──────────┴──────────┴─────────┤
│  Models (models.py)                      │  ← 순수 데이터 구조
│  Constants (constants.py)                │
│  Exceptions (exceptions.py)              │
└──────────────────────────────────────────┘
```

## 데이터 흐름

```
yfinance
  ↓
DataFetcher.fetch(ticker) → pd.DataFrame (OHLCV)
  ↓
IndicatorCalculator → DataFrame + [rsi, macd, bb, adx 컬럼]
  ↓
ADXAnalyzer  ┐
RSIAnalyzer  ├→ IndicatorResult (score, signal, description)
MACDAnalyzer │
BollingerAnalyzer ┘
  ↓
SignalComposer.compose() → (composite_score, Signal, MarketRegime)
  ↓
RiskManager.calculate()  → RiskLevels (stop_loss, take_profit, rr)
  ↓
TradingDecision (최종 결과 데이터클래스)
```

## 핵심 설계 결정

### 1. 파사드 패턴 (Facade)
`MonthlyTradingAnalyzer`는 외부에서 보이는 유일한 인터페이스.
내부 모듈 교체 시 main.py·tests 수정 불필요.

### 2. 점수 기반 신호 (Score-based Signal)
Boolean 신호 충돌을 방지하기 위해 모든 지표를 -100~+100 점수로 정규화.
시장 국면에 따라 가중치를 동적으로 조정.

### 3. 불변 데이터 모델
`TradingDecision`, `IndicatorResult` 등은 `@dataclass`로 정의.
변경 시 새 인스턴스 생성 → 부작용(side effect) 방지.

### 4. 상수 집중 관리
모든 임계값·가중치는 `constants.py`에만 존재.
파라미터 튜닝 시 단일 파일만 수정.
