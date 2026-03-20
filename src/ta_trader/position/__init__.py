"""
ta_trader/position/
포지션 트레이딩 7단계 프로세스 분석 모듈

7단계 프로세스:
  1. 시장 환경 판단   (200MA, ADX, 정배열, ATR%, SMA50>SMA200)
  2. 섹터/테마 선정   (섹터 RS, 자금 흐름)
  3. 종목 선정        (RS, Stage2, ADX≥25, 52주 신고가, SMA50/200 위)
  4. 매수 타이밍      (MA Pullback, Breakout+거래량, MACD, BB Squeeze)
  5. 리스크 관리      (ATR×2.5 손절, 분할매수 1/3씩, 포지션 사이징)
  6. 보유 관리        (트레일링 스톱, 파라볼릭 SAR, 피라미딩)
  7. 매도/청산        (50MA 이탈, MACD/RSI 다이버전스, ADX 하락)
"""