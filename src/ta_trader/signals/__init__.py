# ta_trader/signals/__init__.py
from ta_trader.signals.regime import RegimeContext, classify_regime, detect_regime, get_weights
from ta_trader.signals.strategy import (
    BaseStrategy,
    TrendFollowingStrategy,
    MeanReversionStrategy,
    BreakoutMomentumStrategy,
    AdaptiveDefaultStrategy,
    create_strategy,
)
from ta_trader.signals.composer import SignalComposer

__all__ = [
    "RegimeContext",
    "classify_regime",
    "detect_regime",
    "get_weights",
    "BaseStrategy",
    "TrendFollowingStrategy",
    "MeanReversionStrategy",
    "BreakoutMomentumStrategy",
    "AdaptiveDefaultStrategy",
    "create_strategy",
    "SignalComposer",
]
