"""Tests for indicator calculations in broker.py."""

import pandas as pd
import pytest

from ogaden.broker import Broker


@pytest.fixture
def broker(ohlcv_data: pd.DataFrame) -> Broker:
    b = Broker()
    b.data = ohlcv_data
    return b


class TestMACD:
    def test_columns_created(self, broker: Broker) -> None:
        broker.calculate_macd()
        assert "macd_line" in broker.data.columns
        assert "macd_signal" in broker.data.columns
        assert "macd_histogram" in broker.data.columns

    def test_histogram_equals_line_minus_signal(self, broker: Broker) -> None:
        broker.calculate_macd()
        diff = (broker.data["macd_line"] - broker.data["macd_signal"]) - broker.data[
            "macd_histogram"
        ]
        assert diff.abs().max() < 1e-9

    def test_signal_values(self, broker: Broker) -> None:
        broker.calculate_macd()
        broker.calculate_macd_signal()
        assert "signal_macd" in broker.data.columns
        valid = {"BUY", "SELL", "HOLD"}
        assert set(broker.data["signal_macd"].unique()).issubset(valid)

    def test_no_nan_in_tail(self, broker: Broker) -> None:
        broker.calculate_macd()
        # Last 30 rows should have computed values (enough warm-up)
        assert not broker.data["macd_line"].iloc[-30:].isna().any()


class TestBollingerBands:
    def test_columns_created(self, broker: Broker) -> None:
        broker.calculate_bollinger_bands()
        for col in ["bb_upper", "bb_middle", "bb_lower", "bb_width", "bb_percent_b"]:
            assert col in broker.data.columns

    def test_upper_above_lower(self, broker: Broker) -> None:
        broker.calculate_bollinger_bands()
        tail = broker.data.dropna(subset=["bb_upper", "bb_lower"])
        assert (tail["bb_upper"] >= tail["bb_lower"]).all()

    def test_width_non_negative(self, broker: Broker) -> None:
        broker.calculate_bollinger_bands()
        tail = broker.data.dropna(subset=["bb_width"])
        assert (tail["bb_width"] >= 0).all()

    def test_signal_values(self, broker: Broker) -> None:
        broker.calculate_bollinger_bands()
        broker.calculate_bollinger_signal()
        assert "signal_bb" in broker.data.columns
        valid = {"BUY", "SELL", "HOLD"}
        assert set(broker.data["signal_bb"].unique()).issubset(valid)


class TestStochastic:
    def test_columns_created(self, broker: Broker) -> None:
        broker.calculate_stochastic()
        assert "stoch_k" in broker.data.columns
        assert "stoch_d" in broker.data.columns

    def test_values_in_range(self, broker: Broker) -> None:
        broker.calculate_stochastic()
        tail = broker.data.dropna(subset=["stoch_k", "stoch_d"])
        assert (tail["stoch_k"] >= 0).all() and (tail["stoch_k"] <= 100).all()
        assert (tail["stoch_d"] >= 0).all() and (tail["stoch_d"] <= 100).all()

    def test_signal_values(self, broker: Broker) -> None:
        broker.calculate_stochastic()
        broker.calculate_stochastic_signal()
        assert "signal_stoch" in broker.data.columns
        valid = {"BUY", "SELL", "HOLD"}
        assert set(broker.data["signal_stoch"].unique()).issubset(valid)


class TestATR:
    def test_columns_created(self, broker: Broker) -> None:
        broker.calculate_atr()
        for col in [
            "tr",
            "atr",
            "stop_loss_long",
            "stop_loss_short",
            "take_profit_long",
            "take_profit_short",
        ]:
            assert col in broker.data.columns

    def test_atr_positive(self, broker: Broker) -> None:
        broker.calculate_atr()
        tail = broker.data.dropna(subset=["atr"])
        assert (tail["atr"] > 0).all()

    def test_stop_loss_below_close(self, broker: Broker) -> None:
        broker.calculate_atr()
        tail = broker.data.dropna(subset=["stop_loss_long"])
        assert (tail["stop_loss_long"] < tail["close"]).all()

    def test_take_profit_above_close(self, broker: Broker) -> None:
        broker.calculate_atr()
        tail = broker.data.dropna(subset=["take_profit_long"])
        assert (tail["take_profit_long"] > tail["close"]).all()


class TestVolumeIndicators:
    def test_columns_created(self, broker: Broker) -> None:
        broker.calculate_volume_indicators()
        for col in ["volume_sma", "volume_ratio", "obv", "vpt"]:
            assert col in broker.data.columns

    def test_volume_ratio_non_negative(self, broker: Broker) -> None:
        broker.calculate_volume_indicators()
        tail = broker.data.dropna(subset=["volume_ratio"])
        assert (tail["volume_ratio"] >= 0).all()

    def test_signal_values(self, broker: Broker) -> None:
        broker.calculate_volume_indicators()
        broker.calculate_volume_signal()
        assert "signal_volume" in broker.data.columns
        valid = {"BUY", "SELL", "HOLD"}
        assert set(broker.data["signal_volume"].unique()).issubset(valid)


class TestEMATrend:
    def test_columns_created(self, broker: Broker) -> None:
        broker.calculate_ema()
        broker.calculate_ema_trend()
        broker.calculate_ema_signal_trend()
        assert "trend_ema" in broker.data.columns
        assert "signal_ema_trend" in broker.data.columns

    def test_signal_values(self, broker: Broker) -> None:
        broker.calculate_ema()
        broker.calculate_ema_trend()
        broker.calculate_ema_signal_trend()
        valid = {"BUY", "SELL", "HOLD"}
        assert set(broker.data["signal_ema_trend"].unique()).issubset(valid)

    def test_trend_signal_not_all_hold(self, broker: Broker) -> None:
        """Oscillating price series should produce non-trivial trend signals."""
        broker.calculate_ema()
        broker.calculate_ema_trend()
        broker.calculate_ema_signal_trend()
        # At least some BUY or SELL signals expected with oscillating data
        non_hold = broker.data["signal_ema_trend"] != "HOLD"
        assert non_hold.any()


class TestSMASignal:
    def test_signal_values(self, broker: Broker) -> None:
        broker.calculate_sma()
        broker.calculate_sma_signal()
        valid = {"BUY", "SELL", "HOLD"}
        assert set(broker.data["signal_sma"].unique()).issubset(valid)

    def test_buy_when_fast_above_slow(self, broker: Broker) -> None:
        broker.calculate_sma()
        broker.calculate_sma_signal()
        tail = broker.data.dropna(subset=["fast_sma", "slow_sma"])
        buy_rows = tail[tail["signal_sma"] == "BUY"]
        assert (buy_rows["fast_sma"] > buy_rows["slow_sma"]).all()

    def test_sell_when_fast_below_slow(self, broker: Broker) -> None:
        broker.calculate_sma()
        broker.calculate_sma_signal()
        tail = broker.data.dropna(subset=["fast_sma", "slow_sma"])
        sell_rows = tail[tail["signal_sma"] == "SELL"]
        assert (sell_rows["fast_sma"] < sell_rows["slow_sma"]).all()


class TestRSIEdgeCases:
    def test_rsi_range(self, broker: Broker) -> None:
        broker.calculate_rsi()
        tail = broker.data.dropna(subset=["rsi"])
        assert (tail["rsi"] >= 0).all() and (tail["rsi"] <= 100).all()

    def test_buy_signal_when_oversold(self, broker: Broker) -> None:
        """RSI below buy threshold → signal_rsi == BUY."""
        broker.RSI_BUY_THRESHOLD = 60
        broker.RSI_SELL_THRESHOLD = 80
        broker.calculate_rsi()
        broker.calculate_rsi_signal()
        oversold = broker.data[broker.data["rsi"] < 60]
        if not oversold.empty:
            assert (oversold["signal_rsi"] == "BUY").all()

    def test_sell_signal_when_overbought(self, broker: Broker) -> None:
        """RSI above sell threshold → signal_rsi == SELL."""
        broker.RSI_BUY_THRESHOLD = 20
        broker.RSI_SELL_THRESHOLD = 40
        broker.calculate_rsi()
        broker.calculate_rsi_signal()
        overbought = broker.data[broker.data["rsi"] > 40]
        if not overbought.empty:
            assert (overbought["signal_rsi"] == "SELL").all()
