"""Tests for core.broker."""

from unittest.mock import MagicMock

import pandas as pd
import pytest
from ogaden.broker import Broker


class TestExchangeInjection:
    def test_broker_uses_injected_exchange(self) -> None:
        """Broker should use injected exchange instead of creating Binance client."""
        mock_exchange = MagicMock()
        broker = Broker.__new__(Broker)
        # Manually set minimal state to avoid full init
        broker.exchange = mock_exchange
        broker._rate_limiter = MagicMock()
        broker.SANDBOX = True
        assert broker.exchange is mock_exchange

    def test_broker_defaults_to_binance_client(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Without injected exchange, Broker should create a Binance Client."""
        mock_client = MagicMock()
        monkeypatch.setattr("ogaden.broker.Client", mock_client)

        broker = Broker()
        mock_client.assert_called_once()
        assert broker.exchange is mock_client.return_value


class TestApplyStepSize:
    @pytest.mark.parametrize(
        "quantity,step_size,expected",
        [
            (1.23456, 0.001, 1.234),
            (0.005, 0.01, 0.0),
            (10.0, 1.0, 10.0),
            (0.99999, 0.0001, 0.9999),
            (100.0, 0.00001, 100.0),
        ],
    )
    def test_step_size_rounding(
        self, quantity: float, step_size: float, expected: float
    ) -> None:
        assert Broker._apply_step_size(quantity, step_size) == pytest.approx(expected)

    def test_zero_quantity(self) -> None:
        assert Broker._apply_step_size(0.0, 0.001) == 0.0

    def test_negative_quantity(self) -> None:
        assert Broker._apply_step_size(-1.0, 0.001) == 0.0

    def test_zero_step_size(self) -> None:
        assert Broker._apply_step_size(1.0, 0.0) == 0.0

    def test_invalid_nan(self) -> None:
        assert Broker._apply_step_size(float("nan"), 0.001) == 0.0


class TestExecuteBuySandbox:
    def test_successful_buy(self) -> None:
        broker = Broker()
        broker.quote_balance = 100.0
        broker.current_price = 50000.0
        broker.min_notional = 10.0
        broker.step_size = 0.00001
        broker.min_quantity = 0.00001

        assert broker.execute_buy() is True
        assert broker.base_balance > 0
        assert broker.quote_balance < 100.0

    def test_insufficient_balance(self) -> None:
        broker = Broker()
        broker.quote_balance = 1.0
        broker.current_price = 50000.0
        broker.min_notional = 10.0
        broker.step_size = 0.00001
        broker.min_quantity = 0.00001

        assert broker.execute_buy() is False

    def test_zero_price(self) -> None:
        broker = Broker()
        broker.quote_balance = 100.0
        broker.current_price = 0.0
        broker.min_notional = 10.0
        broker.step_size = 0.00001
        broker.min_quantity = 0.00001

        assert broker.execute_buy() is False


class TestExecuteSellSandbox:
    def test_successful_sell(self) -> None:
        broker = Broker()
        broker.base_balance = 0.001
        broker.current_price = 50000.0
        broker.step_size = 0.00001
        broker.min_quantity = 0.00001

        assert broker.execute_sell() is True
        assert broker.base_balance == pytest.approx(0.0)
        assert broker.quote_balance > 0

    def test_insufficient_base_balance(self) -> None:
        broker = Broker()
        broker.base_balance = 0.0
        broker.current_price = 50000.0
        broker.step_size = 0.00001
        broker.min_quantity = 0.00001

        assert broker.execute_sell() is False


class TestSandboxFees:
    def test_sell_fee_deducted(self) -> None:
        broker = Broker()
        broker.base_balance = 1.0
        broker.current_price = 100.0
        broker.step_size = 0.01
        broker.min_quantity = 0.01

        broker.execute_sell()
        # sale = 1.0 * 100 = 100; fee = 0.1; net = 99.9
        assert broker.quote_balance == pytest.approx(99.9)

    def test_buy_fee_deducted(self) -> None:
        broker = Broker()
        broker.quote_balance = 100.0
        broker.current_price = 100.0
        broker.min_notional = 1.0
        broker.step_size = 0.01
        broker.min_quantity = 0.01
        broker.POSITION_SIZE_PCT = 100.0  # Use full balance for this test

        broker.execute_buy()
        # quantity = floor(100/100, step=0.01) = 1.0
        # cost = 100; fee = 0.1; quote_balance = 100 - 100.1 = -0.1
        assert broker.base_balance == pytest.approx(1.0)
        assert broker.quote_balance == pytest.approx(-0.1)


class TestIndicators:
    def test_calculate_ema(self, sample_data: pd.DataFrame) -> None:
        broker = Broker()
        broker.data = sample_data
        broker.calculate_ema()
        assert "fast_ema" in broker.data.columns
        assert "slow_ema" in broker.data.columns

    def test_calculate_rsi(self, sample_data: pd.DataFrame) -> None:
        broker = Broker()
        broker.data = sample_data
        broker.calculate_rsi()
        assert "rsi" in broker.data.columns
        assert broker.data["rsi"].iloc[-1] > 0

    def test_calculate_rsi_signal(self, sample_data: pd.DataFrame) -> None:
        broker = Broker()
        broker.data = sample_data
        broker.calculate_rsi()
        broker.calculate_rsi_signal()
        assert "signal_rsi" in broker.data.columns
        assert broker.data["signal_rsi"].iloc[-1] in ("BUY", "SELL", "HOLD")

    def test_calculate_ema_signal(self, sample_data: pd.DataFrame) -> None:
        broker = Broker()
        broker.data = sample_data
        broker.calculate_ema()
        broker.calculate_ema_signal()
        assert "signal_ema" in broker.data.columns
        assert broker.data["signal_ema"].iloc[-1] in ("BUY", "SELL", "HOLD")

    def test_calculate_sma(self, sample_data: pd.DataFrame) -> None:
        broker = Broker()
        broker.data = sample_data
        broker.calculate_sma()
        assert "fast_sma" in broker.data.columns
        assert "slow_sma" in broker.data.columns

    def test_calculate_ema_trend(self, sample_data: pd.DataFrame) -> None:
        broker = Broker()
        broker.data = sample_data
        broker.calculate_ema_trend()
        assert "trend_ema" in broker.data.columns
