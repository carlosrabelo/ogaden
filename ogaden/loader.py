"""Environment-based configuration loader."""

import logging
import os
from pathlib import Path

from dotenv import load_dotenv

from ogaden.errors import ConfigError

log = logging.getLogger(__name__)

_VALID_INTERVALS = frozenset(
    {
        "1m",
        "3m",
        "5m",
        "15m",
        "30m",
        "1h",
        "2h",
        "4h",
        "6h",
        "8h",
        "12h",
        "1d",
        "3d",
        "1w",
        "1M",
    }
)

_VALID_STRATEGY_MODES = frozenset({"conservative", "balanced", "aggressive"})


def _validate_timezone(tz_name: str) -> None:
    """Raise ConfigError if *tz_name* is not a valid IANA timezone."""
    try:
        from zoneinfo import ZoneInfo

        ZoneInfo(tz_name)
    except Exception as exc:
        raise ConfigError(f"Invalid TIMEZONE: {tz_name!r}") from exc


class Loader:
    """Load and validate configuration from environment variables."""

    def __init__(self) -> None:
        load_dotenv()

        # Exchange
        self.API_KEY: str | None = os.getenv("API_KEY")
        self.API_SECRET: str | None = os.getenv("API_SECRET")
        self.SANDBOX: bool = os.getenv("SANDBOX", "true").lower() in (
            "true",
            "yes",
            "1",
        )

        if not self.SANDBOX and (not self.API_KEY or not self.API_SECRET):
            raise ConfigError(
                "API_KEY and API_SECRET are required when SANDBOX is disabled"
            )

        # Assets
        self.BASE_ASSET: str = os.getenv("BASE_ASSET", "BTC")
        self.QUOTE_ASSET: str = os.getenv("QUOTE_ASSET", "USDT")
        self.SYMBOL: str = f"{self.BASE_ASSET}{self.QUOTE_ASSET}"

        # Interval
        self.INTERVAL: str = os.getenv("INTERVAL", "15m")
        self.LIMIT: int = int(os.getenv("LIMIT", "500"))

        # Display
        self.TIMEZONE: str = os.getenv("TIMEZONE", "America/Cuiaba")

        # Balances
        self.BASE_BALANCE_DEFAULT: float = float(os.getenv("BASE_BALANCE", "0.0"))
        self.QUOTE_BALANCE_DEFAULT: float = float(os.getenv("QUOTE_BALANCE", "10.0"))

        # SMA
        self.FAST_SMA: int = int(os.getenv("FAST_SMA", "7"))
        self.SLOW_SMA: int = int(os.getenv("SLOW_SMA", "14"))
        self.TREND_SMA: int = int(os.getenv("TREND_SMA", "50"))

        # EMA
        self.FAST_EMA: int = int(os.getenv("FAST_EMA", "7"))
        self.SLOW_EMA: int = int(os.getenv("SLOW_EMA", "14"))
        self.TREND_EMA: int = int(os.getenv("TREND_EMA", "50"))

        # RSI
        self.RSI_PERIOD: int = int(os.getenv("RSI_PERIOD", "14"))
        self.RSI_BUY_THRESHOLD: int = int(os.getenv("RSI_BUY_THRESHOLD", "40"))
        self.RSI_SELL_THRESHOLD: int = int(os.getenv("RSI_SELL_THRESHOLD", "60"))

        # Strategy
        self.STRATEGY_MODE: str = os.getenv("STRATEGY_MODE", "balanced")

        if self.STRATEGY_MODE not in _VALID_STRATEGY_MODES:
            raise ConfigError(
                f"Invalid STRATEGY_MODE: {self.STRATEGY_MODE!r}. "
                f"Must be one of: {', '.join(sorted(_VALID_STRATEGY_MODES))}"
            )

        # Load strategy defaults first
        from ogaden.strategy import StrategyConfig

        strategy_config = StrategyConfig(self.STRATEGY_MODE)

        # Thresholds (use strategy defaults, allow .env override)
        profit_default = strategy_config.profit_threshold
        loss_default = strategy_config.loss_threshold
        self.PROFIT_THRESHOLD: float = float(
            os.getenv("PROFIT_THRESHOLD", str(profit_default))
        )
        self.LOSS_THRESHOLD: float = (
            float(os.getenv("LOSS_THRESHOLD", str(loss_default))) * -1.0
        )
        trailing_raw = float(os.getenv("TRAILING_THRESHOLD", "0.0"))

        self.PROFIT_ENABLE: bool = self.PROFIT_THRESHOLD != 0.0
        self.LOSS_ENABLE: bool = self.LOSS_THRESHOLD != 0.0
        self.TRAILING_ENABLE: bool = trailing_raw != 0.0
        self.TRAILING_THRESHOLD: float = 1.0 - trailing_raw / 100.0

        # Memcached
        self.MEMCACHED_HOST: str = os.getenv("MEMCACHED_HOST", "localhost")
        self.MEMCACHED_PORT: int = int(os.getenv("MEMCACHED_PORT", "11211"))

        # Persistence
        self.STATE_FILE: Path = Path(os.getenv("STATE_FILE", "data/state.json"))

        # --- Risk Management (mandatory) ---
        self.POSITION_SIZE_PCT: float = float(
            os.getenv("POSITION_SIZE_PCT", str(strategy_config.position_size_pct))
        )
        self.TREND_FILTER_EMA: int = int(
            os.getenv("TREND_FILTER_EMA", str(strategy_config.trend_filter_ema))
        )
        self.COOLDOWN_CYCLES: int = int(
            os.getenv("COOLDOWN_CYCLES", str(strategy_config.cooldown_cycles))
        )
        self.MIN_TRADE_MARGIN_PCT: float = float(
            os.getenv("MIN_TRADE_MARGIN_PCT", str(strategy_config.min_trade_margin_pct))
        )
        self.ATR_STOP_MULTIPLIER: float = float(
            os.getenv("ATR_STOP_MULTIPLIER", str(strategy_config.atr_stop_multiplier))
        )

        # --- Validate configuration ---
        if self.INTERVAL not in _VALID_INTERVALS:
            raise ConfigError(
                f"Invalid INTERVAL: {self.INTERVAL!r}. "
                f"Must be one of: {', '.join(sorted(_VALID_INTERVALS))}"
            )

        _validate_timezone(self.TIMEZONE)

        if not (1 <= self.LIMIT <= 1000):
            raise ConfigError(
                f"Invalid LIMIT: {self.LIMIT}. Must be between 1 and 1000."
            )

        if not (1.0 <= self.POSITION_SIZE_PCT <= 100.0):
            raise ConfigError(
                f"Invalid POSITION_SIZE_PCT: {self.POSITION_SIZE_PCT}. "
                f"Must be between 1.0 and 100.0."
            )

        if self.TREND_FILTER_EMA < 50:
            raise ConfigError(
                f"Invalid TREND_FILTER_EMA: {self.TREND_FILTER_EMA}. "
                f"Must be >= 50 (recommend 200)."
            )

        if self.COOLDOWN_CYCLES < 0:
            raise ConfigError(
                f"Invalid COOLDOWN_CYCLES: {self.COOLDOWN_CYCLES}. Must be >= 0."
            )

        if self.MIN_TRADE_MARGIN_PCT < 0.0:
            raise ConfigError(
                f"Invalid MIN_TRADE_MARGIN_PCT: {self.MIN_TRADE_MARGIN_PCT}. "
                f"Must be >= 0."
            )

        if self.ATR_STOP_MULTIPLIER < 1.0:
            raise ConfigError(
                f"Invalid ATR_STOP_MULTIPLIER: {self.ATR_STOP_MULTIPLIER}. "
                f"Must be >= 1.0 (recommend 2.0)."
            )

        log.info(
            "Config loaded: %s %s sandbox=%s strategy=%s",
            self.SYMBOL,
            self.INTERVAL,
            self.SANDBOX,
            self.STRATEGY_MODE,
        )
