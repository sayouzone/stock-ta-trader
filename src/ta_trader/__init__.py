"""TA Trader - Technical Analysis Trading System"""

from ta_trader.analyzer import MonthlyTradingAnalyzer
from ta_trader.models import MarketRegime, Signal, TradingDecision, TradingStyle

__version__ = "1.1.0"
__all__ = ["MonthlyTradingAnalyzer", "Signal", "MarketRegime", "TradingDecision", "TradingStyle"]
