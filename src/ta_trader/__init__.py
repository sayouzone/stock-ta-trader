"""TA Trader - Technical Analysis Trading System"""

from ta_trader.analyzers.short import ShortTermAnalyzer
from ta_trader.analyzers.growth import GrowthMomentumAnalyzer
from ta_trader.analyzers.value import ValueInvestingAnalyzer
from ta_trader.models import MarketRegime, Signal, TradingDecision, TradingStyle

__version__ = "1.5.0"
__all__ = [
    "ShortTermAnalyzer",
    "GrowthMomentumAnalyzer",
    "ValueInvestingAnalyzer",
    "Signal",
    "MarketRegime",
    "TradingDecision",
    "TradingStyle",
]
