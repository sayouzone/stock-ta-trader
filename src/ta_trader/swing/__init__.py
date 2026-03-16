"""
ta_trader/swing/
스윙 트레이딩 6단계 프로세스 분석 모듈

6단계 프로세스:
  1. 시장 환경 판단  (ADX, SMA200, ATR%)
  2. 종목 스크리닝   (거래량, RS, +DI/-DI, 정배열)
  3. 진입 타이밍     (MACD, RSI, BB, 피보나치, EMA)
  4. 포지션 사이징   (ATR 손절/익절, R배수, 자본 배분)
  5. 익절/청산 전략  (트레일링 스톱, RSI/MACD/BB 기반)
  6. 매매 복기       (결과 요약)
"""

#from ta_trader.swing.analyzer import SwingTradingAnalyzer
#from ta_trader.swing.models import (
#    SwingAnalysisResult,
#    SwingSignal,
#    MarketEnvResult,
#    MarketEnvironment,
#    ScreeningResult,
#   ScreeningGrade,
#   EntryResult,
#    EntrySignalDetail,
#    PositionSizingResult,
#    ExitStrategyResult,
#)
from ta_trader.formatters.swing import format_swing_result, format_swing_report

__all__ = [
    #"SwingTradingAnalyzer",
    #"SwingAnalysisResult",
    #"SwingSignal",
    #"MarketEnvResult",
    #"MarketEnvironment",
    #"ScreeningResult",
    #"ScreeningGrade",
    #"EntryResult",
    #"EntrySignalDetail",
    #"PositionSizingResult",
    #"ExitStrategyResult",
    "format_swing_result",
    "format_swing_report",
]
