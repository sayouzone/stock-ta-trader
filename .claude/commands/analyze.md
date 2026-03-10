---
description: 단일 종목 기술적 분석 실행. 티커 심볼을 입력받아 ADX/MACD/RSI/BB 복합 분석 후 매매 신호와 차트를 생성합니다.
---

# /analyze 명령어

## 실행 방법
```
/analyze $TICKER
```
예시: `/analyze 005930.KS` 또는 `/analyze AAPL`

## 처리 단계
1. `src/ta_trader/analyzers/short.py` 의 `ShortTermAnalyzer` 로 데이터 수집
2. 4개 지표 계산 및 신호 분석
3. 복합 점수 산출 및 최종 신호 결정
4. 손절/익절가 계산
5. `reports/` 에 차트 PNG 저장
6. 터미널에 분석 결과 출력

## 실행 명령
```bash
python main.py analyze $TICKER --save-chart
```

## 출력 항목
- 현재가, 시장 국면, 복합 점수, 최종 신호
- 개별 지표 점수 및 설명
- 손절가, 목표가, 위험보상비율
- 차트 파일 경로
