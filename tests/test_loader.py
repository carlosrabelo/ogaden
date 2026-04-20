"""Tests for core.loader."""

import pytest

from ogaden.errors import ConfigError
from ogaden.loader import Loader


class TestLoaderDefaults:
    def test_default_symbol(self) -> None:
        loader = Loader()
        assert loader.SYMBOL == "BTCUSDT"

    def test_default_interval(self) -> None:
        loader = Loader()
        assert loader.INTERVAL == "15m"

    def test_default_sandbox(self) -> None:
        loader = Loader()
        assert loader.SANDBOX is True

    def test_default_ema_windows(self) -> None:
        loader = Loader()
        assert loader.FAST_EMA == 7
        assert loader.SLOW_EMA == 14
        assert loader.TREND_EMA == 50


class TestLoaderOverrides:
    def test_custom_symbol(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("BASE_ASSET", "ETH")
        monkeypatch.setenv("QUOTE_ASSET", "BTC")
        loader = Loader()
        assert loader.SYMBOL == "ETHBTC"

    def test_custom_interval(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("INTERVAL", "1h")
        loader = Loader()
        assert loader.INTERVAL == "1h"

    def test_sandbox_disabled(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("SANDBOX", "false")
        loader = Loader()
        assert loader.SANDBOX is False


class TestLoaderValidation:
    def test_missing_api_key_live_mode(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("SANDBOX", "false")
        monkeypatch.delenv("API_KEY")
        with pytest.raises(ConfigError, match="API_KEY"):
            Loader()

    def test_missing_api_secret_live_mode(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("SANDBOX", "false")
        monkeypatch.delenv("API_SECRET")
        with pytest.raises(ConfigError, match="API_KEY"):
            Loader()

    def test_invalid_interval(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("INTERVAL", "2x")
        with pytest.raises(ConfigError, match="Invalid INTERVAL"):
            Loader()

    def test_invalid_strategy_mode(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("STRATEGY_MODE", "ultra_aggressive")
        with pytest.raises(ConfigError, match="Invalid STRATEGY_MODE"):
            Loader()

    def test_invalid_timezone(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("TIMEZONE", "Mars/Olympus")
        with pytest.raises(ConfigError, match="Invalid TIMEZONE"):
            Loader()

    def test_limit_too_low(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("LIMIT", "0")
        with pytest.raises(ConfigError, match="Invalid LIMIT"):
            Loader()

    def test_limit_too_high(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("LIMIT", "1001")
        with pytest.raises(ConfigError, match="Invalid LIMIT"):
            Loader()

    def test_valid_interval_accepted(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("INTERVAL", "4h")
        loader = Loader()
        assert loader.INTERVAL == "4h"


class TestRiskManagementConfig:
    def test_position_size_pct_default(self) -> None:
        loader = Loader()
        assert loader.POSITION_SIZE_PCT == 25.0

    def test_position_size_pct_invalid_too_low(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("POSITION_SIZE_PCT", "0.5")
        with pytest.raises(ConfigError, match="POSITION_SIZE_PCT"):
            Loader()

    def test_position_size_pct_invalid_too_high(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("POSITION_SIZE_PCT", "150")
        with pytest.raises(ConfigError, match="POSITION_SIZE_PCT"):
            Loader()

    def test_trend_filter_ema_too_low(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("TREND_FILTER_EMA", "20")
        with pytest.raises(ConfigError, match="TREND_FILTER_EMA"):
            Loader()

    def test_cooldown_cycles_negative(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("COOLDOWN_CYCLES", "-1")
        with pytest.raises(ConfigError, match="COOLDOWN_CYCLES"):
            Loader()

    def test_min_trade_margin_negative(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("MIN_TRADE_MARGIN_PCT", "-0.5")
        with pytest.raises(ConfigError, match="MIN_TRADE_MARGIN_PCT"):
            Loader()

    def test_atr_stop_multiplier_too_low(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("ATR_STOP_MULTIPLIER", "0.5")
        with pytest.raises(ConfigError, match="ATR_STOP_MULTIPLIER"):
            Loader()

    def test_all_risk_config_defaults(self) -> None:
        loader = Loader()
        assert loader.POSITION_SIZE_PCT == 25.0
        assert loader.TREND_FILTER_EMA == 100
        assert loader.COOLDOWN_CYCLES == 5
        assert loader.MIN_TRADE_MARGIN_PCT == 0.3
        assert loader.ATR_STOP_MULTIPLIER == 2.0


class TestLoaderThresholds:
    def test_profit_enable(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("PROFIT_THRESHOLD", "2.5")
        loader = Loader()
        assert loader.PROFIT_ENABLE is True
        assert loader.PROFIT_THRESHOLD == 2.5

    def test_profit_disabled_at_zero(self) -> None:
        loader = Loader()
        assert loader.PROFIT_ENABLE is False

    def test_loss_threshold_negated(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("LOSS_THRESHOLD", "3.0")
        loader = Loader()
        assert loader.LOSS_THRESHOLD == -3.0
        assert loader.LOSS_ENABLE is True

    def test_trailing_threshold_conversion(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("TRAILING_THRESHOLD", "5.0")
        loader = Loader()
        assert loader.TRAILING_ENABLE is True
        assert loader.TRAILING_THRESHOLD == pytest.approx(0.95)
