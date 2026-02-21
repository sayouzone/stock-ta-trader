"""
tests/conftest.py
공통 픽스처 정의
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest


@pytest.fixture()
def sample_ohlcv() -> pd.DataFrame:
    """100일치 가상 OHLCV 데이터 (지표 계산 충분)"""
    rng = np.random.default_rng(42)
    dates = pd.date_range("2024-01-01", periods=100, freq="B")
    close = 60000 + np.cumsum(rng.normal(0, 500, 100))
    high  = close + rng.uniform(100, 800, 100)
    low   = close - rng.uniform(100, 800, 100)
    open_ = close + rng.normal(0, 200, 100)
    vol   = rng.integers(5_000_000, 20_000_000, 100)

    return pd.DataFrame(
        {"Open": open_, "High": high, "Low": low, "Close": close, "Volume": vol},
        index=dates,
    )
