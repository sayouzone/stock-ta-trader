---
description: 특정 종목에 대해 과거 기간 기준 백테스트를 실행하고 수익률, 승률, 샤프 비율을 계산합니다.
---

# /backtest 명령어

## 실행 방법
```
/backtest $TICKER --start 2023-01-01 --end 2024-12-31
```

## 처리 단계
1. 지정 기간 OHLCV 데이터 수집
2. 각 월 말일 기준으로 매매 신호 생성
3. 신호 기반 매매 시뮬레이션 실행
4. 성과 지표 계산 (수익률, 승률, MDD, Sharpe)

## 실행 명령
```bash
python main.py backtest $TICKER --start $START --end $END --capital 10000000
```

## 출력 항목
- 총 수익률, 연환산 수익률
- 승률, 총 매매 횟수
- 최대 낙폭 (MDD)
- 샤프 비율
- 월별 손익 히트맵
