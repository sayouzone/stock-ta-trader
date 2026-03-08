---
description: watchlist.yaml 의 전체 종목을 일괄 스크리닝하여 점수순으로 정렬된 DataFrame을 출력합니다.
---

# /screen 명령어

## 실행 방법
```
/screen
```
또는 특정 설정 파일 지정:
```
/screen --config configs/my_watchlist.yaml
```

## 처리 단계
1. `configs/watchlist.yaml` 에서 종목 목록 로드
2. 각 종목에 대해 `ShortTermAnalyzer` 병렬 실행
3. 복합 점수 기준 내림차순 정렬
4. `reports/screening_YYYYMMDD.csv` 로 결과 저장

## 실행 명령
```bash
python main.py screen --config configs/watchlist.yaml --output reports/
```

## 출력 항목
- Ticker, Price, Regime, Score, Signal, StopLoss, TakeProfit, RiskReward
- 매수 신호 상위 5종목 하이라이트
