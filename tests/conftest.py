"""Shared pytest fixtures."""

import pandas as pd
import pytest


@pytest.fixture(autouse=True)
def env_vars(monkeypatch: pytest.MonkeyPatch) -> None:
    """Set required environment variables for all tests."""
    monkeypatch.setattr("ogaden.loader.load_dotenv", lambda *a, **kw: None)
    monkeypatch.setenv("API_KEY", "test_key")
    monkeypatch.setenv("API_SECRET", "test_secret")
    monkeypatch.setenv("SANDBOX", "true")
    monkeypatch.setenv("BASE_ASSET", "BTC")
    monkeypatch.setenv("QUOTE_ASSET", "USDT")
    monkeypatch.setenv("BASE_BALANCE", "0")
    monkeypatch.setenv("QUOTE_BALANCE", "100")
    monkeypatch.setenv("STRATEGY", "RULES")
    monkeypatch.setenv("PROFIT_THRESHOLD", "0.0")
    monkeypatch.setenv("LOSS_THRESHOLD", "0.0")
    monkeypatch.setenv("TRAILING_THRESHOLD", "0.0")


@pytest.fixture
def sample_data() -> pd.DataFrame:
    """Sample close-price DataFrame with 50 rows (monotonically increasing)."""
    return pd.DataFrame(
        {
            "close_time": pd.date_range("2026-01-01", periods=50, freq="15min"),
            "close": [100.0 + i * 0.5 for i in range(50)],
        }
    )


@pytest.fixture
def ohlcv_data() -> pd.DataFrame:
    """Full OHLCV DataFrame with 100 rows needed for multi-indicator tests.

    Prices oscillate to produce varied signals (not all BUY or all SELL).
    """
    import math

    n = 100
    times = pd.date_range("2026-01-01", periods=n, freq="15min")
    close = [100.0 + 10.0 * math.sin(i * 0.2) for i in range(n)]
    high = [c + 1.5 for c in close]
    low = [c - 1.5 for c in close]
    open_ = [c - 0.3 for c in close]
    volume = [1000.0 + 200.0 * math.sin(i * 0.3) for i in range(n)]

    return pd.DataFrame(
        {
            "close_time": times,
            "open": open_,
            "high": high,
            "low": low,
            "close": close,
            "volume": volume,
        }
    )
