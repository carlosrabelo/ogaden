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


def _parse_signals(raw: str, env_var: str) -> frozenset[str]:
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


_PRESETS: dict[str, dict[str, str]] = {
    "CONSERVATIVE": {
        "LEVEL1_SIGNALS": "SMA,EMA",
        "LEVEL2_SIGNALS": "RSI,MACD",
        "LEVEL3_SIGNALS": "TREND",
        "LEVEL2_MIN": "1",
        "PROFIT_THRESHOLD": "1.5",
        "LOSS_THRESHOLD": "1.0",
        "TRAILING_THRESHOLD": "0.0",
        "TRAILING_STOP_PCT": "0.5",
        "POSITION_SIZE_PCT": "15.0",
        "TREND_FILTER_EMA": "200",
        "MIN_TRADE_MARGIN_PCT": "0.5",
        "ATR_STOP_MULTIPLIER": "2.5",
        "COOLDOWN_CYCLES": "10",
        "MAX_DRAWDOWN_PCT": "10.0",
        "MAX_CONSECUTIVE_LOSSES": "3",
    },
    "BALANCED": {
        "LEVEL1_SIGNALS": "SMA",
        "LEVEL2_SIGNALS": "",
        "LEVEL3_SIGNALS": "",
        "LEVEL2_MIN": "0",
        "PROFIT_THRESHOLD": "0.0",
        "LOSS_THRESHOLD": "0.0",
        "TRAILING_THRESHOLD": "0.0",
        "TRAILING_STOP_PCT": "0.0",
        "POSITION_SIZE_PCT": "25.0",
        "TREND_FILTER_EMA": "100",
        "MIN_TRADE_MARGIN_PCT": "0.3",
        "ATR_STOP_MULTIPLIER": "2.0",
        "COOLDOWN_CYCLES": "5",
        "MAX_DRAWDOWN_PCT": "15.0",
        "MAX_CONSECUTIVE_LOSSES": "5",
    },
    "AGGRESSIVE": {
        "LEVEL1_SIGNALS": "SMA",
        "LEVEL2_SIGNALS": "",
        "LEVEL3_SIGNALS": "",
        "LEVEL2_MIN": "0",
        "PROFIT_THRESHOLD": "0.0",
        "LOSS_THRESHOLD": "0.0",
        "TRAILING_THRESHOLD": "0.0",
        "TRAILING_STOP_PCT": "0.0",
        "POSITION_SIZE_PCT": "50.0",
        "TREND_FILTER_EMA": "50",
        "MIN_TRADE_MARGIN_PCT": "0.1",
        "ATR_STOP_MULTIPLIER": "1.5",
        "COOLDOWN_CYCLES": "2",
        "MAX_DRAWDOWN_PCT": "25.0",
        "MAX_CONSECUTIVE_LOSSES": "10",
    },
}


class Loader:
    """Load and validate configuration from environment variables."""

    def _get(self, var: str, default: str = "") -> str:
        if self._preset is not None:
            return os.getenv(var, self._preset.get(var, default))
        return os.getenv(var, default)

    def __init__(self) -> None:
        load_dotenv()

        _preset_name = os.getenv("PRESET", "").strip().upper()
        if _preset_name:
            if _preset_name not in _PRESETS:
                raise ConfigError(
                    f"Invalid PRESET: {_preset_name!r}. Valid: {sorted(_PRESETS)}"
                )
            self._preset: dict[str, str] | None = _PRESETS[_preset_name]
            log.info("Preset %r active — defaults overridable by individual env vars", _preset_name)
        else:
            self._preset = None
            log.info("No preset — using individual env vars and hardcoded defaults")
        self.PRESET: str = _preset_name

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
        self.LEVEL1_SIGNALS: frozenset[str] = _parse_signals(
            self._get("LEVEL1_SIGNALS", "SMA"), "LEVEL1_SIGNALS"
        )
        self.LEVEL2_SIGNALS: frozenset[str] = _parse_signals(
            self._get("LEVEL2_SIGNALS", ""), "LEVEL2_SIGNALS"
        )
        self.LEVEL3_SIGNALS: frozenset[str] = _parse_signals(
            self._get("LEVEL3_SIGNALS", ""), "LEVEL3_SIGNALS"
        )
        self.LEVEL2_MIN: int = int(self._get("LEVEL2_MIN", "1"))

        # Saída — alvo de lucro e limite de perda fixos
        self.PROFIT_THRESHOLD: float = float(self._get("PROFIT_THRESHOLD", "0.0"))
        self.LOSS_THRESHOLD: float = float(self._get("LOSS_THRESHOLD", "0.0")) * -1.0
        self.PROFIT_ENABLE: bool = self.PROFIT_THRESHOLD != 0.0
        self.LOSS_ENABLE: bool = self.LOSS_THRESHOLD != 0.0

        # Saída — trailing de saldo (% de queda sobre o pico do saldo esperado)
        _trailing_raw = float(self._get("TRAILING_THRESHOLD", "0.0"))
        self.TRAILING_THRESHOLD: float = 1.0 - _trailing_raw / 100.0
        self.TRAILING_ENABLE: bool = _trailing_raw != 0.0

        # Saída — trailing stop de preço (% de queda sobre o preço de pico)
        self.TRAILING_STOP_PCT: float = float(self._get("TRAILING_STOP_PCT", "0.0"))
        self.TRAILING_STOP_ENABLE: bool = self.TRAILING_STOP_PCT > 0.0

        # Gestão de risco — tamanho de posição e filtros de entrada
        self.POSITION_SIZE_PCT: float = float(self._get("POSITION_SIZE_PCT", "25.0"))
        self.TREND_FILTER_EMA: int = int(self._get("TREND_FILTER_EMA", "100"))
        self.MIN_TRADE_MARGIN_PCT: float = float(
            self._get("MIN_TRADE_MARGIN_PCT", "0.3")
        )
        self.FEE_PCT: float = float(os.getenv("FEE_PCT", "0.2"))
        self.ATR_STOP_MULTIPLIER: float = float(self._get("ATR_STOP_MULTIPLIER", "2.0"))

        # Gestão de risco — cooldown após perda
        self.COOLDOWN_CYCLES: int = int(self._get("COOLDOWN_CYCLES", "5"))

        # Circuit breaker — pausa permanente por drawdown excessivo
        self.MAX_DRAWDOWN_PCT: float = abs(float(self._get("MAX_DRAWDOWN_PCT", "15.0")))
        self.MAX_CONSECUTIVE_LOSSES: int = int(self._get("MAX_CONSECUTIVE_LOSSES", "5"))

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

        if self.LEVEL2_SIGNALS and self.LEVEL2_MIN < 0:
            raise ConfigError(f"Invalid LEVEL2_MIN: {self.LEVEL2_MIN}. Must be >= 0.")

        log.info(
            "Config loaded: %s %s sandbox=%s preset=%s L1=%s L2=%s L3=%s min=%d",
            self.SYMBOL,
            self.INTERVAL,
            self.SANDBOX,
            self.PRESET or "none",
            sorted(self.LEVEL1_SIGNALS),
            sorted(self.LEVEL2_SIGNALS),
            sorted(self.LEVEL3_SIGNALS),
            self.LEVEL2_MIN,
        )
