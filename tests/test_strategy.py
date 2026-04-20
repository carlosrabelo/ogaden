"""Tests for RuleStrategy decision logic."""

from unittest.mock import MagicMock

import pytest

from ogaden.strategy import RuleStrategy, StrategyConfig


@pytest.fixture
def trader_mock() -> MagicMock:
    trader = MagicMock()
    trader.position = "SELL"
    return trader


# ---------------------------------------------------------------------------
# StrategyConfig
# ---------------------------------------------------------------------------


class TestStrategyConfig:
    def test_balanced_defaults(self) -> None:
        cfg = StrategyConfig("balanced")
        assert cfg.min_confirmations == 1
        assert cfg.volume_required is False

    def test_conservative_defaults(self) -> None:
        cfg = StrategyConfig("conservative")
        assert cfg.min_confirmations == 2
        assert cfg.volume_required is True

    def test_aggressive_defaults(self) -> None:
        cfg = StrategyConfig("aggressive")
        assert cfg.min_confirmations == 1
        assert cfg.cooldown_cycles == 2
        assert cfg.position_size_pct == 25.0
        assert cfg.volume_required is False

    def test_unknown_mode_raises(self) -> None:
        with pytest.raises(ValueError, match="Unknown strategy mode"):
            StrategyConfig("unknown")


# ---------------------------------------------------------------------------
# RuleStrategy.can_buy — balanced mode (min_confirmations=1)
# ---------------------------------------------------------------------------


class TestCanBuy:
    def test_all_buy_signals(self, trader_mock: MagicMock) -> None:
        strategy = RuleStrategy(trader_mock)
        strategy.signal_ema = "BUY"
        strategy.signal_ema_trend = "BUY"
        strategy.signal_rsi = "BUY"
        assert strategy.can_buy() is True

    def test_primary_ema_with_one_confirmation(self, trader_mock: MagicMock) -> None:
        """EMA crossover + one confirmation (MACD) is enough for balanced mode."""
        strategy = RuleStrategy(trader_mock)
        strategy.signal_ema = "BUY"
        strategy.signal_ema_trend = "HOLD"
        strategy.signal_macd = "BUY"
        assert strategy.can_buy() is True

    def test_primary_trend_with_one_confirmation(self, trader_mock: MagicMock) -> None:
        """TREND alone as primary + RSI confirmation."""
        strategy = RuleStrategy(trader_mock)
        strategy.signal_ema = "HOLD"
        strategy.signal_ema_trend = "BUY"
        strategy.signal_rsi = "BUY"
        assert strategy.can_buy() is True

    def test_no_primary_signal_blocks_buy(self, trader_mock: MagicMock) -> None:
        """Both EMA and TREND are HOLD → blocked even with confirmations."""
        strategy = RuleStrategy(trader_mock)
        strategy.signal_ema = "HOLD"
        strategy.signal_ema_trend = "HOLD"
        strategy.signal_rsi = "BUY"
        strategy.signal_macd = "BUY"
        assert strategy.can_buy() is False

    def test_insufficient_confirmations_blocks_buy(
        self, trader_mock: MagicMock
    ) -> None:
        """Primary signal present but no confirmations (balanced needs 1)."""
        strategy = RuleStrategy(trader_mock)
        strategy.signal_ema = "BUY"
        strategy.signal_ema_trend = "BUY"
        # all confirmations default to HOLD
        assert strategy.can_buy() is False

    def test_wrong_position_blocks_buy(self, trader_mock: MagicMock) -> None:
        trader_mock.position = "BUY"
        strategy = RuleStrategy(trader_mock)
        strategy.signal_ema = "BUY"
        strategy.signal_ema_trend = "BUY"
        strategy.signal_rsi = "BUY"
        assert strategy.can_buy() is False

    def test_volume_gate_blocks_when_required(self, trader_mock: MagicMock) -> None:
        strategy = RuleStrategy(trader_mock, mode="conservative")
        strategy.signal_ema = "BUY"
        strategy.signal_ema_trend = "BUY"
        strategy.signal_rsi = "BUY"
        strategy.signal_macd = "BUY"
        strategy.signal_volume = "HOLD"  # volume not confirming
        assert strategy.can_buy() is False

    def test_aggressive_mode_one_confirmation_needed(
        self, trader_mock: MagicMock
    ) -> None:
        strategy = RuleStrategy(trader_mock, mode="aggressive")
        strategy.signal_ema = "BUY"
        strategy.signal_ema_trend = "HOLD"
        strategy.signal_rsi = "BUY"
        assert strategy.can_buy() is True

    def test_aggressive_mode_no_confirmation_blocks(
        self, trader_mock: MagicMock
    ) -> None:
        strategy = RuleStrategy(trader_mock, mode="aggressive")
        strategy.signal_ema = "BUY"
        strategy.signal_ema_trend = "HOLD"
        # no confirmations
        assert strategy.can_buy() is False

    def test_conservative_needs_two_confirmations(self, trader_mock: MagicMock) -> None:
        strategy = RuleStrategy(trader_mock, mode="conservative")
        strategy.signal_ema = "BUY"
        strategy.signal_ema_trend = "BUY"
        strategy.signal_volume = "BUY"
        strategy.signal_rsi = "BUY"
        strategy.signal_macd = "HOLD"  # only 1 confirmation → not enough
        assert strategy.can_buy() is False

    def test_conservative_with_two_confirmations_buys(
        self, trader_mock: MagicMock
    ) -> None:
        strategy = RuleStrategy(trader_mock, mode="conservative")
        strategy.signal_ema = "BUY"
        strategy.signal_ema_trend = "BUY"
        strategy.signal_volume = "BUY"
        strategy.signal_rsi = "BUY"
        strategy.signal_macd = "BUY"
        assert strategy.can_buy() is True


# ---------------------------------------------------------------------------
# RuleStrategy.can_sell — balanced mode
# ---------------------------------------------------------------------------


class TestCanSell:
    def test_all_sell_signals(self, trader_mock: MagicMock) -> None:
        trader_mock.position = "BUY"
        strategy = RuleStrategy(trader_mock)
        strategy.signal_ema = "SELL"
        strategy.signal_ema_trend = "SELL"
        strategy.signal_rsi = "SELL"
        assert strategy.can_sell() is True

    def test_primary_ema_with_one_confirmation(self, trader_mock: MagicMock) -> None:
        trader_mock.position = "BUY"
        strategy = RuleStrategy(trader_mock)
        strategy.signal_ema = "SELL"
        strategy.signal_ema_trend = "HOLD"
        strategy.signal_macd = "SELL"
        assert strategy.can_sell() is True

    def test_no_primary_sell_blocks(self, trader_mock: MagicMock) -> None:
        trader_mock.position = "BUY"
        strategy = RuleStrategy(trader_mock)
        strategy.signal_ema = "HOLD"
        strategy.signal_ema_trend = "HOLD"
        strategy.signal_rsi = "SELL"
        assert strategy.can_sell() is False

    def test_wrong_position_blocks_sell(self, trader_mock: MagicMock) -> None:
        trader_mock.position = "SELL"
        strategy = RuleStrategy(trader_mock)
        strategy.signal_ema = "SELL"
        strategy.signal_ema_trend = "SELL"
        strategy.signal_rsi = "SELL"
        assert strategy.can_sell() is False

    def test_insufficient_confirmations_blocks_sell(
        self, trader_mock: MagicMock
    ) -> None:
        trader_mock.position = "BUY"
        strategy = RuleStrategy(trader_mock)
        strategy.signal_ema = "SELL"
        strategy.signal_ema_trend = "SELL"
        assert strategy.can_sell() is False


# ---------------------------------------------------------------------------
# Signal string
# ---------------------------------------------------------------------------


class TestSignalString:
    def test_format_contains_all_indicators(self, trader_mock: MagicMock) -> None:
        strategy = RuleStrategy(trader_mock)
        s = strategy.get_signal_string()
        for prefix in ("EMA:", "RSI:", "TREND:", "VOL:", "MACD:", "BB:", "STOCH:"):
            assert prefix in s

    def test_reflects_current_signals(self, trader_mock: MagicMock) -> None:
        strategy = RuleStrategy(trader_mock)
        strategy.signal_ema = "BUY"
        strategy.signal_rsi = "SELL"
        s = strategy.get_signal_string()
        assert "EMA:BUY" in s
        assert "RSI:SELL" in s

    def test_default_all_hold(self, trader_mock: MagicMock) -> None:
        strategy = RuleStrategy(trader_mock)
        s = strategy.get_signal_string()
        assert s.count("HOLD") == 7
