# TA Trader - Claude Code Project Memory

## 프로젝트 개요
ADX · MACD · RSI · Bollinger Bands 기반 **1개월 단위 기술적 분석 트레이딩 시스템**  
한국(KRX/DART) 및 미국 주식 시장 지원. yfinance 데이터 소스.

## 아키텍처 원칙
- **단일 책임 원칙**: 각 모듈은 하나의 역할만 담당
- **타입 힌트 필수**: 모든 함수/메서드에 완전한 type annotation
- **데이터클래스 우선**: 결과 전달에 `@dataclass` 사용, dict 지양
- **상수는 constants.py**: 매직 넘버/문자열 절대 금지
- **예외 계층**: 커스텀 예외는 `TATraderError` 상속

## 디렉토리 구조
```
ta_trader/
├── CLAUDE.md                    ← 이 파일 (Claude Code 메모리)
├── CLAUDE.local.md              ← 로컬 개인 설정 (gitignore)
├── .claude/
│   ├── settings.json            ← hooks, 권한 설정
│   └── commands/                ← 커스텀 슬래시 명령어
│       ├── analyze.md           ← /analyze - 종목 분석
│       ├── backtest.md          ← /backtest - 백테스트 실행
│       ├── screen.md            ← /screen - 포트폴리오 스크리닝
│       └── update-deps.md       ← /update-deps - 의존성 업데이트
├── src/ta_trader/
│   ├── __init__.py
│   ├── constants.py             ← 모든 상수 (임계값, 가중치)
│   ├── exceptions.py            ← 커스텀 예외 계층
│   ├── models.py                ← 데이터클래스 (Signal, TradingDecision 등)
│   ├── data/
│   │   ├── fetcher.py           ← yfinance 데이터 수집
│   │   └── validator.py         ← 데이터 검증
│   ├── indicators/
│   │   ├── calculator.py        ← 모든 지표 계산 (ta 라이브러리)
│   │   ├── adx.py               ← ADX 신호 분석
│   │   ├── rsi.py               ← RSI 신호 분석
│   │   ├── macd.py              ← MACD 신호 분석
│   │   └── bollinger.py         ← Bollinger Bands 신호 분석
│   ├── signals/
│   │   ├── composer.py          ← 복합 점수 합산 및 시장 국면 분류
│   │   └── regime.py            ← 시장 국면별 가중치 조정
│   ├── risk/
│   │   └── manager.py           ← 손절/익절가 산출, 리스크/리워드
│   ├── llm/                     ← LLM 기반 자연어 분석 모듈 ★
│   │   ├── __init__.py
│   │   ├── models.py            ← LLMAnalysis 데이터클래스
│   │   ├── prompt_builder.py    ← TradingDecision → LLM 프롬프트 변환
│   │   └── analyzer.py          ← Anthropic API 호출 (동기/스트리밍)
│   ├── visualization/
│   │   └── chart.py             ← 5패널 차트 (가격·MACD·RSI·ADX·점수)
│   ├── utils/
│   │   ├── logger.py            ← 로깅 설정
│   │   └── formatter.py         ← 결과 출력 포매터
│   └── analyzer.py              ← 메인 MonthlyTradingAnalyzer (파사드)
├── tests/
│   ├── conftest.py
│   ├── test_indicators.py
│   ├── test_signals.py
│   ├── test_risk.py
│   └── test_llm.py              ← LLM 모듈 모킹 테스트 ★
├── configs/
│   └── watchlist.yaml           ← 관심 종목 목록
├── docs/
│   ├── architecture.md          ← 상세 설계 문서
│   └── indicators.md            ← 지표 파라미터 설명
├── reports/                     ← 자동 생성 분석 리포트 (gitignore)
├── logs/                        ← 실행 로그 (gitignore)
├── pyproject.toml
├── requirements.txt
└── main.py                      ← CLI 진입점
```

## 핵심 모듈 관계
```
main.py
  └─► MonthlyTradingAnalyzer (analyzer.py)
        ├─► DataFetcher (data/fetcher.py)
        ├─► IndicatorCalculator (indicators/calculator.py)
        │     ├─► ADXAnalyzer
        │     ├─► RSIAnalyzer
        │     ├─► MACDAnalyzer
        │     └─► BollingerAnalyzer
        ├─► SignalComposer (signals/composer.py)
        │     └─► RegimeClassifier (signals/regime.py)
        ├─► RiskManager (risk/manager.py)
        └─► ChartVisualizer (visualization/chart.py)
```

## 지표 파라미터 (constants.py 기준)
| 지표 | 파라미터 | 기본값 |
|------|----------|--------|
| ADX | window | 14 |
| RSI | window | 14 |
| MACD | fast/slow/signal | 12/26/9 |
| Bollinger Bands | window/std | 20/2.0 |

## 가중치 체계
- **추세장** (ADX ≥ 25): ADX=25%, RSI=25%, MACD=35%, BB=15%
- **횡보장** (ADX < 20): ADX=10%, RSI=35%, MACD=25%, BB=30%
- **기본값**: ADX=20%, RSI=30%, MACD=30%, BB=20%

## 점수 → 신호 매핑
| 복합 점수 | 신호 |
|-----------|------|
| ≥ 60 | STRONG_BUY |
| 20 ~ 59 | BUY |
| -19 ~ 19 | NEUTRAL |
| -60 ~ -20 | SELL |
| ≤ -61 | STRONG_SELL |

## 코딩 규칙
- Python 3.11+
- Black 포매터 (line-length = 100)
- isort import 정렬
- 모든 public 함수에 docstring
- 테스트는 pytest + pytest-cov
- 로그는 `structlog` 사용 (logger.py 참고)

## 한국 주식 티커 형식
- KRX: `005930.KS` (삼성전자), `000660.KS` (SK하이닉스)
- KOSDAQ: `035420.KQ` (카카오)
- 미국: `AAPL`, `NVDA`, `TSLA`

## 자주 쓰는 명령어
```bash
# 단일 종목 분석
python main.py analyze 005930.KS

# LLM 해석 포함 분석
python main.py analyze 005930.KS --llm

# 스트리밍 LLM + 리포트 저장 + 차트 저장
python main.py analyze NVDA --llm-stream --save-chart --save-report

# 포트폴리오 스크리닝
python main.py screen --config configs/watchlist.yaml

# 테스트 실행
PYTHONPATH=src pytest tests/ -v --cov=src/ta_trader

# 포매터
black src/ tests/ && isort src/ tests/
```

## 변경 이력
- 2026-02-19: 초기 Claude Code 프로젝트 구조 설정
- 2026-02-19: 차트에서 한국어 출력 오류 해결
- 2026-02-21: LLM 분석 기능 추가