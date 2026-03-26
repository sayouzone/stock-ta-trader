# ta_trader/interfaces/api/routers/__init__.py

from ta_trader.interfaces.api.routers.alerts import router as alerts_router
from ta_trader.interfaces.api.routers.analysis import router as analysis_router
from ta_trader.interfaces.api.routers.ws import router as ws_router

__all__ = ["alerts_router", "analysis_router", "ws_router"]