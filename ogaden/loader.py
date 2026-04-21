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

_VALID_SIGNALS = frozenset({"EMA", "TREND", "SMA", "RSI", "MACD", "STOCH", "BB", "VOL"})


def _validate_timezone(tz_name: str) -> None:
    """Raise ConfigError if *tz_name* is not a valid IANA timezone."""
    try:
        from zoneinfo import ZoneInfo

        ZoneInfo(tz_name)
    except Exception as exc:
        raise ConfigError(f"Invalid TIMEZONE: {tz_name!r}") from exc


def _parse_signals(env_var: str, default: str) -> frozenset[str]:
    raw = os.getenv(env_var, default)
    if not raw.strip():
        return frozenset()
    names = frozenset(s.strip().upper() for s in raw.split(",") if s.strip())
    invalid = names - _VALID_SIGNALS
    if invalid:
        raise ConfigError(
            f"Invalid signals in {env_var}: {sorted(invalid)}. "
            f"Valid: {sorted(_VALID_SIGNALS)}"
        )
    return names


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

        # Assets e mercado
        self.BASE_ASSET: str = os.getenv("BASE_ASSET", "BTC")
        self.QUOTE_ASSET: str = os.getenv("QUOTE_ASSET", "USDT")
        self.SYMBOL: str = f"{self.BASE_ASSET}{self.QUOTE_ASSET}"
        self.INTERVAL: str = os.getenv("INTERVAL", "15m")
        self.LIMIT: int = int(os.getenv("LIMIT", "500"))

        # Display
        self.TIMEZONE: str = os.getenv("TIMEZONE", "America/Cuiaba")

        # Saldos iniciais (sandbox)
        self.BASE_BALANCE_DEFAULT: float = float(os.getenv("BASE_BALANCE", "0.0"))
        self.QUOTE_BALANCE_DEFAULT: float = float(os.getenv("QUOTE_BALANCE", "10.0"))

        # Indicadores — SMA
        self.FAST_SMA: int = int(os.getenv("FAST_SMA", "7"))
        self.SLOW_SMA: int = int(os.getenv("SLOW_SMA", "14"))
        self.TREND_SMA: int = int(os.getenv("TREND_SMA", "50"))

        # Indicadores — EMA
        self.FAST_EMA: int = int(os.getenv("FAST_EMA", "7"))
        self.SLOW_EMA: int = int(os.getenv("SLOW_EMA", "14"))
        self.TREND_EMA: int = int(os.getenv("TREND_EMA", "50"))

        # Indicadores — RSI
        self.RSI_PERIOD: int = int(os.getenv("RSI_PERIOD", "14"))
        self.RSI_BUY_THRESHOLD: int = int(os.getenv("RSI_BUY_THRESHOLD", "40"))
        self.RSI_SELL_THRESHOLD: int = int(os.getenv("RSI_SELL_THRESHOLD", "60"))

        # Estratégia — roteamento de sinais por nível
        self.LEVEL1_SIGNALS: frozenset[str] = _parse_signals("LEVEL1_SIGNALS", "SMA")
        self.LEVEL2_SIGNALS: frozenset[str] = _parse_signals("LEVEL2_SIGNALS", "")
        self.LEVEL3_SIGNALS: frozenset[str] = _parse_signals("LEVEL3_SIGNALS", "")
        self.LEVEL2_MIN: int = int(os.getenv("LEVEL2_MIN", "1"))

        # Saída — alvo de lucro e limite de perda fixos
        self.PROFIT_THRESHOLD: float = float(os.getenv("PROFIT_THRESHOLD", "0.0"))
        self.LOSS_THRESHOLD: float = float(os.getenv("LOSS_THRESHOLD", "0.0")) * -1.0
        self.PROFIT_ENABLE: bool = self.PROFIT_THRESHOLD != 0.0
        self.LOSS_ENABLE: bool = self.LOSS_THRESHOLD != 0.0

        # Saída — trailing de saldo (% de queda sobre o pico do saldo esperado)
        _trailing_raw = float(os.getenv("TRAILING_THRESHOLD", "0.0"))
        self.TRAILING_THRESHOLD: float = 1.0 - _trailing_raw / 100.0
        self.TRAILING_ENABLE: bool = _trailing_raw != 0.0

        # Saída — trailing stop de preço (% de queda sobre o preço de pico)
        self.TRAILING_STOP_PCT: float = float(os.getenv("TRAILING_STOP_PCT", "0.0"))
        self.TRAILING_STOP_ENABLE: bool = self.TRAILING_STOP_PCT > 0.0

        # Gestão de risco — tamanho de posição e filtros de entrada
        self.POSITION_SIZE_PCT: float = float(os.getenv("POSITION_SIZE_PCT", "25.0"))
        self.TREND_FILTER_EMA: int = int(os.getenv("TREND_FILTER_EMA", "100"))
        self.MIN_TRADE_MARGIN_PCT: float = float(
            os.getenv("MIN_TRADE_MARGIN_PCT", "0.3")
        )
        self.ATR_STOP_MULTIPLIER: float = float(os.getenv("ATR_STOP_MULTIPLIER", "2.0"))

        # Gestão de risco — cooldown após perda
        self.COOLDOWN_CYCLES: int = int(os.getenv("COOLDOWN_CYCLES", "5"))

        # Circuit breaker — pausa permanente por drawdown excessivo
        self.MAX_DRAWDOWN_PCT: float = abs(float(os.getenv("MAX_DRAWDOWN_PCT", "15.0")))
        self.MAX_CONSECUTIVE_LOSSES: int = int(os.getenv("MAX_CONSECUTIVE_LOSSES", "5"))

        # Infraestrutura
        self.MEMCACHED_HOST: str = os.getenv("MEMCACHED_HOST", "localhost")
        self.MEMCACHED_PORT: int = int(os.getenv("MEMCACHED_PORT", "11211"))
        self.STATE_FILE: Path = Path(os.getenv("STATE_FILE", "data/state.json"))

        # --- Validate ---
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

        if self.LEVEL2_MIN < 0:
            raise ConfigError(f"Invalid LEVEL2_MIN: {self.LEVEL2_MIN}. Must be >= 0.")

        if self.LEVEL2_MIN > 0 and not self.LEVEL2_SIGNALS:
            log.warning(
                "LEVEL2_MIN=%d has no effect because LEVEL2_SIGNALS is empty",
                self.LEVEL2_MIN,
            )

        log.info(
            "Config loaded: %s %s sandbox=%s L1=%s L2=%s L3=%s min=%d",
            self.SYMBOL,
            self.INTERVAL,
            self.SANDBOX,
            sorted(self.LEVEL1_SIGNALS),
            sorted(self.LEVEL2_SIGNALS),
            sorted(self.LEVEL3_SIGNALS),
            self.LEVEL2_MIN,
        )
