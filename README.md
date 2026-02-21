# stock-ta-trader using Claude Code 


**가중치 구성 (합계 100)**

| 지표 | 가중치 | 역할 |
|-----|-----|-----|
| ADX | 20% | 추세 강도 + 방향 (+DI/-DI) |
| RSI | 30% | 모멘텀 과매수/과매도 |
| MACD | 30% | 추세 전환 크로스 신호 |
| Bollinger Bands | 20% | 가격 위치 + 변동성 |


**시장 국면별 로직**

- **강한추세 (ADX ≥ 25)**: 추세 추종 → MACD/ADX 비중 강화
- **횡보 (ADX < 20)**: 평균회귀 → RSI/BB 비중 강화로 자동 재가중

**거래 결정**

- 5개 패널 차트 (가격·MACD·RSI·ADX·복합점수)
- BB 기반 손절 / 익절가 자동 산출


```
ta_trader/
├── CLAUDE.md                    ← Claude Code 핵심 메모리 (매 세션 자동 로드)
├── .claude/
│   ├── settings.json            ← Hooks: 문법 검사, main 브랜치 보호
│   └── commands/
│       ├── analyze.md           ← /analyze 슬래시 커맨드
│       ├── screen.md            ← /screen 슬래시 커맨드
│       ├── backtest.md          ← /backtest 슬래시 커맨드
│       └── update-deps.md       ← /update-deps 슬래시 커맨드
├── src/ta_trader/
│   ├── constants.py             ← 모든 임계값·가중치 (매직 넘버 0개)
│   ├── models.py                ← Signal·MarketRegime·TradingDecision
│   ├── analyzer.py              ← 파사드 (외부 유일 진입점)
│   ├── data/fetcher.py          ← yfinance 데이터 수집
│   ├── indicators/              ← ADX·RSI·MACD·Bollinger 개별 모듈
│   ├── llm/                     ← 
│   │   ├── __init__.py
│   │   ├── models.py            ← LLMAnalysis 데이터클래스
│   │   ├── prompt_builder.py    ← TradingDecision → 구조화 프롬프트
│   │   └── analyzer.py          ← Anthropic API 호출 (동기 + 스트리밍)
│   ├── signals/                 ← 복합 점수 합산·시장 국면 분류
│   ├── risk/manager.py          ← 손절·익절·RR 계산
│   └── visualization/chart.py  ← 5패널 차트
├── tests/                       ← 25개 단위 테스트 (커버리지 64%)
├── configs/watchlist.yaml       ← 관심 종목 목록
└── main.py                      ← CLI (python main.py analyze 005930.KS)
```

```bash
pip install -r requirements.txt
```

```bash
PYTHONPATH=src python main.py analyze 005930.KS --save-chart
```

```bash
# 환경변수 설정
export ANTHROPIC_API_KEY="sk-ant-..."

# 기술적 분석 + LLM 해석
python main.py analyze 005930.KS --llm

# 스트리밍으로 LLM 응답 실시간 출력 + 리포트 저장 + 차트 저장
python main.py analyze NVDA --llm-stream --save-chart --save-report

# 다른 모델 지정
python main.py analyze AAPL --llm --llm-model claude-opus-4-6
```

### 출력 예시
```
════════════════════════════════════════
  📊 005930.KS | 2024-12-31 | 현재가: 62,000
  시장 국면 : 강한추세
  최종 신호 : ★ 매수 ★
  ...
  ── LLM 분석 [claude-sonnet-4-20250514]  신뢰도: ████████░░ 78%
  【종합 판단】
    삼성전자는 ADX 28로 추세가 유효하며 ...
  【주요 리스크】
    ⚠ 반도체 업황 불확실성
  【액션 플랜】
    62,000원 진입, 59,000원 손절 ...
```