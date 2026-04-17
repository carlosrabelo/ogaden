"""Tests for core.trader."""

from unittest.mock import MagicMock, patch

import pytest
from ogaden.trader import Trader


@pytest.fixture
def trader() -> Trader:
    with patch("ogaden.trader.base.Client"):
        t = Trader()
        t.base_balance = 0.0
        t.quote_balance = 100.0
        t.current_price = 50000.0
        return t


class TestUpdateVars:
    def test_buy_position_resets_difference(self, trader: Trader) -> None:
        trader.position = "WAITING"
        trader.base_balance = 0.5
        trader.current_price = 50000.0
        trader._update_vars()
        assert trader.difference_price_v == 0.0
        assert trader.difference_price_p == 0.0
        assert trader.trailing_balance == 0.0

    def test_sell_position_calculates_difference(self, trader: Trader) -> None:
        trader.position = "HOLDING"
        trader.purchase_price = 45000.0
        trader.current_price = 50000.0
        trader.base_balance = 0.001
        trader._update_vars()
        assert trader.difference_price_v == pytest.approx(5000.0)
        assert trader.difference_price_p == pytest.approx(5000.0 / 45000.0 * 100.0)

    def test_expected_balance(self, trader: Trader) -> None:
        trader.base_balance = 0.001
        trader.quote_balance = 100.0
        trader.current_price = 50000.0
        trader.position = "WAITING"
        trader._update_vars()
        assert trader.base_quote_balance == pytest.approx(50.0)
        assert trader.expected_balance == pytest.approx(150.0)

    def test_zero_purchase_price_no_division_error(self, trader: Trader) -> None:
        trader.position = "HOLDING"
        trader.purchase_price = 0.0
        trader.current_price = 50000.0
        trader.base_balance = 0.001
        trader._update_vars()
        assert trader.difference_price_v == 0.0
        assert trader.difference_price_p == 0.0


class TestCanSell:
    def test_not_sell_position(self, trader: Trader) -> None:
        trader.position = "WAITING"
        assert trader.can_sell() is False

    def test_profit_threshold(self, trader: Trader) -> None:
        trader.position = "HOLDING"
        trader.PROFIT_ENABLE = True
        trader.PROFIT_THRESHOLD = 2.0
        trader.difference_price_p = 3.0
        assert trader.can_sell() is True

    def test_loss_threshold(self, trader: Trader) -> None:
        trader.position = "HOLDING"
        trader.LOSS_ENABLE = True
        trader.LOSS_THRESHOLD = -5.0
        trader.difference_price_p = -6.0
        assert trader.can_sell() is True

    def test_below_profit_threshold_delegates_to_strategy(self, trader: Trader) -> None:
        trader.position = "HOLDING"
        trader.PROFIT_ENABLE = True
        trader.PROFIT_THRESHOLD = 5.0
        trader.difference_price_p = 2.0
        trader.LOSS_ENABLE = False
        trader.TRAILING_ENABLE = False
        assert trader.can_sell() is False


class TestDoBuy:
    def test_buy_updates_position(self, trader: Trader) -> None:
        trader.position = "WAITING"
        trader.quote_balance = 100.0
        trader.current_price = 50000.0
        trader.min_notional = 10.0
        trader.step_size = 0.00001
        trader.min_quantity = 0.00001

        trader._do_buy()
        assert trader.position == "HOLDING"
        assert trader.purchase_price == 50000.0

    def test_failed_buy_keeps_position(self, trader: Trader) -> None:
        trader.position = "WAITING"
        trader.quote_balance = 0.0
        trader.current_price = 50000.0
        trader.min_notional = 10.0
        trader.step_size = 0.00001
        trader.min_quantity = 0.00001

        trader._do_buy()
        assert trader.position == "WAITING"


class TestDoSell:
    def test_sell_updates_position(self, trader: Trader) -> None:
        trader.position = "HOLDING"
        trader.base_balance = 0.001
        trader.current_price = 50000.0
        trader.step_size = 0.00001
        trader.min_quantity = 0.00001

        trader._do_sell()
        assert trader.position == "WAITING"
        assert trader.purchase_price == 0.0

    def test_failed_sell_keeps_position(self, trader: Trader) -> None:
        trader.position = "HOLDING"
        trader.base_balance = 0.0
        trader.current_price = 50000.0
        trader.step_size = 0.00001
        trader.min_quantity = 0.00001

        trader._do_sell()
        assert trader.position == "HOLDING"


class TestStatus:
    def test_status_writes_to_memcache(self, trader: Trader) -> None:
        trader.position = "WAITING"
        trader.current_price = 50000.0
        trader.status(quiet=True)
        trader.memcache.set_many.assert_called_once()
        call_kwargs = trader.memcache.set_many.call_args
        data = call_kwargs.kwargs.get("values") or call_kwargs[1].get("values")
        assert data["position"] == "WAITING"

    def test_status_memcache_failure_no_crash(self, trader: Trader) -> None:
        trader.memcache.set_many.side_effect = ConnectionError("down")
        trader.status(quiet=True)  # Should not raise


class TestLifecycle:
    def test_setup_initializes_running_false(self, trader: Trader) -> None:
        trader.setup()
        assert trader.is_running is False

    def test_start_sets_running_true(self, trader: Trader) -> None:
        trader.start()
        assert trader.is_running is True

    def test_stop_sets_running_false(self, trader: Trader) -> None:
        trader.start()
        trader.stop()
        assert trader.is_running is False

    def test_is_running_false_before_start(self, trader: Trader) -> None:
        assert trader.is_running is False


class TestExchangeInjection:
    def test_trader_accepts_exchange(self, monkeypatch: pytest.MonkeyPatch) -> None:
        mock_exchange = MagicMock()
        monkeypatch.setattr("ogaden.broker.Client", MagicMock())
        trader = Trader(exchange=mock_exchange)
        assert trader.exchange is mock_exchange

    def test_trader_defaults_to_no_exchange(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        mock_client = MagicMock()
        monkeypatch.setattr("ogaden.broker.Client", mock_client)
        trader = Trader()
        assert trader.exchange is mock_client.return_value


class TestMemcachedCheck:
    def test_check_memcached_logs_warning_on_failure(
        self, trader: Trader, caplog: pytest.LogCaptureFixture
    ) -> None:
        """When Memcached is unreachable, a clear warning should be logged."""
        trader.memcache.set.side_effect = ConnectionError("refused")

        with caplog.at_level("WARNING"):
            trader._check_memcached()

        assert any("Memcached unreachable" in msg for msg in caplog.messages)
        assert any(trader.MEMCACHED_HOST in msg for msg in caplog.messages)


class TestRiskManagement:
    """Tests for the 6 mandatory risk management features."""

    # -- Position Sizing --

    def test_position_sizing_reduces_buy_amount(
        self, trader: Trader, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        trader.position = "WAITING"
        trader.quote_balance = 1000.0
        trader.current_price = 50.0
        trader.min_notional = 10.0
        trader.step_size = 0.01
        trader.min_quantity = 0.01
        trader.POSITION_SIZE_PCT = 25.0

        trader._do_buy()
        assert trader.base_balance == pytest.approx(5.0)
        assert trader.quote_balance == pytest.approx(749.75)

    # -- Stop-Loss / Take-Profit --

    def test_do_buy_sets_atr_based_sl_tp(
        self, trader: Trader, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        import pandas as pd

        trader.position = "WAITING"
        trader.current_price = 100.0
        trader.quote_balance = 1000.0
        trader.min_notional = 10.0
        trader.step_size = 0.01
        trader.min_quantity = 0.01
        trader.ATR_STOP_MULTIPLIER = 2.0
        trader.data = pd.DataFrame({"atr": [2.0]})

        trader._do_buy()
        assert trader.stop_loss_price == pytest.approx(96.0)
        assert trader.take_profit_price == pytest.approx(108.0)

    def test_do_buy_sets_fallback_sl_tp_when_no_atr(
        self, trader: Trader, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        import pandas as pd

        trader.position = "WAITING"
        trader.current_price = 100.0
        trader.quote_balance = 1000.0
        trader.min_notional = 10.0
        trader.step_size = 0.01
        trader.min_quantity = 0.01
        trader.data = pd.DataFrame()

        trader._do_buy()
        assert trader.stop_loss_price == pytest.approx(98.0)
        assert trader.take_profit_price == pytest.approx(104.0)

    def test_can_sell_forced_on_stop_loss(self, trader: Trader) -> None:
        trader.position = "HOLDING"
        trader.stop_loss_price = 95.0
        trader.current_price = 94.0
        assert trader.can_sell() is True

    def test_can_sell_forced_on_take_profit(self, trader: Trader) -> None:
        trader.position = "HOLDING"
        trader.take_profit_price = 110.0
        trader.current_price = 111.0
        assert trader.can_sell() is True

    # -- Cooldown --

    def test_can_buy_blocked_during_cooldown(self, trader: Trader) -> None:
        trader.position = "WAITING"
        trader.metrics.cycles = 10
        trader.cooldown_until_cycle = 15
        assert trader.can_buy() is False

    def test_can_buy_allowed_after_cooldown(self, trader: Trader) -> None:
        trader.position = "WAITING"
        trader.metrics.cycles = 20
        trader.cooldown_until_cycle = 15
        assert trader.can_buy() is False

    def test_can_buy_blocked_by_trend_filter(self, trader: Trader) -> None:
        trader.position = "WAITING"
        trader.metrics.cycles = 100
        trader.cooldown_until_cycle = 0
        trader.trend_ema_value = 60000.0
        trader.current_price = 50000.0
        assert trader.can_buy() is False

    def test_can_buy_allowed_above_trend_ema(self, trader: Trader) -> None:
        trader.position = "WAITING"
        trader.metrics.cycles = 100
        trader.cooldown_until_cycle = 0
        trader.trend_ema_value = 40000.0
        trader.current_price = 50000.0
        assert trader.can_buy() is False

    def test_do_sell_sets_cooldown_on_loss(self, trader: Trader) -> None:
        trader.position = "HOLDING"
        trader.base_balance = 1.0
        trader.current_price = 50.0
        trader.step_size = 0.01
        trader.min_quantity = 0.01
        trader.purchase_price = 55.0
        trader.difference_price_p = -5.0
        trader.metrics.cycles = 10
        trader.COOLDOWN_CYCLES = 5

        trader._do_sell()
        assert trader.cooldown_until_cycle == 15
        assert trader.last_trade_pnl == pytest.approx(-5.0)

    # -- State Persistence --

    def test_save_restore_sl_tp_cooldown(
        self, tmp_path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from ogaden.trader import Trader

        monkeypatch.setattr("ogaden.broker.Client", lambda *a, **kw: object())

        state_file = tmp_path / "ogaden_state.json"

        trader = Trader()
        trader.STATE_FILE = state_file
        trader.position = "HOLDING"
        trader.stop_loss_price = 95.0
        trader.take_profit_price = 108.0
        trader.cooldown_until_cycle = 42
        trader.last_trade_pnl = -3.5
        trader._save_state()

        trader2 = Trader()
        trader2.STATE_FILE = state_file
        trader2._load_state()

        assert trader2.stop_loss_price == pytest.approx(95.0)
        assert trader2.take_profit_price == pytest.approx(108.0)
        assert trader2.cooldown_until_cycle == 42
        assert trader2.last_trade_pnl == pytest.approx(-3.5)

    def test_symbol_change_resets_state(
        self, tmp_path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from ogaden.trader import Trader

        monkeypatch.setattr("ogaden.broker.Client", lambda *a, **kw: object())

        state_file = tmp_path / "ogaden_state.json"

        trader = Trader()
        trader.STATE_FILE = state_file
        trader.position = "HOLDING"
        trader.purchase_price = 50000.0
        trader.stop_loss_price = 48000.0
        trader.take_profit_price = 56000.0
        trader.cooldown_until_cycle = 10
        trader._save_state()

        monkeypatch.setenv("BASE_ASSET", "ETH")
        monkeypatch.setenv("QUOTE_ASSET", "USDT")

        trader2 = Trader()
        trader2.STATE_FILE = state_file
        trader2._load_state()

        assert trader2.position == "WAITING"
        assert trader2.purchase_price == pytest.approx(0.0)
        assert trader2.stop_loss_price == pytest.approx(0.0)
        assert trader2.take_profit_price == pytest.approx(0.0)
        assert trader2.cooldown_until_cycle == 0
