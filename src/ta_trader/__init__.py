"""TA Trader - Technical Analysis Trading System"""

from ta_trader.analyzer import MonthlyTradingAnalyzer
from ta_trader.growth.analyzer import GrowthMomentumAnalyzer
from ta_trader.models import MarketRegime, Signal, TradingDecision, TradingStyle
from ta_trader.value.analyzer import ValueInvestingAnalyzer

__version__ = "1.5.0"
__all__ = [
    "MonthlyTradingAnalyzer",
    "GrowthMomentumAnalyzer",
    "ValueInvestingAnalyzer",
    "Signal",
    "MarketRegime",
    "TradingDecision",
    "TradingStyle",
]
