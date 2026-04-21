"""Tests for RuleStrategy decision logic."""

from unittest.mock import MagicMock

import pytest

from ogaden.strategy import RuleStrategy


@pytest.fixture
def trader_mock() -> MagicMock:
    """Default fixture mirrors loader defaults: L1=SMA, L2 empty, L3 empty."""
    trader = MagicMock()
    trader.position = "READY"
    trader.LEVEL1_SIGNALS = frozenset({"SMA"})
    trader.LEVEL2_SIGNALS = frozenset()
    trader.LEVEL3_SIGNALS = frozenset()
    trader.LEVEL2_MIN = 1
    return trader


# ---------------------------------------------------------------------------
# RuleStrategy.can_buy — default config (L1=SMA, no confirmations)
# ---------------------------------------------------------------------------


class TestCanBuy:
    def test_sma_buy_signal_triggers(self, trader_mock: MagicMock) -> None:
        strategy = RuleStrategy(trader_mock)
        strategy.signal_sma = "BUY"
        assert strategy.can_buy() is True

    def test_no_l1_signal_blocks_buy(self, trader_mock: MagicMock) -> None:
        strategy = RuleStrategy(trader_mock)
        # SMA is HOLD (default) — L1 gate not satisfied
        assert strategy.can_buy() is False

    def test_wrong_position_blocks_buy(self, trader_mock: MagicMock) -> None:
        trader_mock.position = "LONG"
        strategy = RuleStrategy(trader_mock)
        strategy.signal_sma = "BUY"
        assert strategy.can_buy() is False

    def test_cooldown_blocks_buy(self, trader_mock: MagicMock) -> None:
        trader_mock.position = "COOLDOWN"
        strategy = RuleStrategy(trader_mock)
        strategy.signal_sma = "BUY"
        assert strategy.can_buy() is False

    def test_blocked_position_blocks_buy(self, trader_mock: MagicMock) -> None:
        trader_mock.position = "BLOCKED"
        strategy = RuleStrategy(trader_mock)
        strategy.signal_sma = "BUY"
        assert strategy.can_buy() is False

    # --- Custom LEVEL configurations ---

    def test_l1_ema_trend_with_confirmation(self, trader_mock: MagicMock) -> None:
        trader_mock.LEVEL1_SIGNALS = frozenset({"EMA", "TREND"})
        trader_mock.LEVEL2_SIGNALS = frozenset({"RSI", "MACD"})
        trader_mock.LEVEL2_MIN = 1
        strategy = RuleStrategy(trader_mock)
        strategy.signal_ema = "BUY"
        strategy.signal_rsi = "BUY"
        assert strategy.can_buy() is True

    def test_l1_present_but_no_l2_confirmation_blocks(
        self, trader_mock: MagicMock
    ) -> None:
        trader_mock.LEVEL1_SIGNALS = frozenset({"EMA"})
        trader_mock.LEVEL2_SIGNALS = frozenset({"RSI", "MACD"})
        trader_mock.LEVEL2_MIN = 1
        strategy = RuleStrategy(trader_mock)
        strategy.signal_ema = "BUY"
        # RSI and MACD are HOLD — no confirmations
        assert strategy.can_buy() is False

    def test_two_confirmations_required(self, trader_mock: MagicMock) -> None:
        trader_mock.LEVEL1_SIGNALS = frozenset({"EMA"})
        trader_mock.LEVEL2_SIGNALS = frozenset({"RSI", "MACD", "BB"})
        trader_mock.LEVEL2_MIN = 2
        strategy = RuleStrategy(trader_mock)
        strategy.signal_ema = "BUY"
        strategy.signal_rsi = "BUY"
        # Only 1 confirmation, need 2
        assert strategy.can_buy() is False

    def test_two_confirmations_present(self, trader_mock: MagicMock) -> None:
        trader_mock.LEVEL1_SIGNALS = frozenset({"EMA"})
        trader_mock.LEVEL2_SIGNALS = frozenset({"RSI", "MACD", "BB"})
        trader_mock.LEVEL2_MIN = 2
        strategy = RuleStrategy(trader_mock)
        strategy.signal_ema = "BUY"
        strategy.signal_rsi = "BUY"
        strategy.signal_macd = "BUY"
        assert strategy.can_buy() is True

    def test_l3_gate_blocks_when_failing(self, trader_mock: MagicMock) -> None:
        trader_mock.LEVEL3_SIGNALS = frozenset({"VOL"})
        strategy = RuleStrategy(trader_mock)
        strategy.signal_sma = "BUY"
        strategy.signal_volume = "HOLD"
        assert strategy.can_buy() is False

    def test_l3_gate_allows_when_satisfied(self, trader_mock: MagicMock) -> None:
        trader_mock.LEVEL3_SIGNALS = frozenset({"VOL"})
        strategy = RuleStrategy(trader_mock)
        strategy.signal_sma = "BUY"
        strategy.signal_volume = "BUY"
        assert strategy.can_buy() is True

    def test_empty_l1_bypasses_primary_gate(self, trader_mock: MagicMock) -> None:
        """When LEVEL1 is empty the primary gate is bypassed."""
        trader_mock.LEVEL1_SIGNALS = frozenset()
        strategy = RuleStrategy(trader_mock)
        strategy.signal_rsi = "BUY"
        assert strategy.can_buy() is True


# ---------------------------------------------------------------------------
# RuleStrategy.can_sell — default config (L1=SMA, no confirmations)
# ---------------------------------------------------------------------------


class TestCanSell:
    def test_sma_sell_signal_triggers(self, trader_mock: MagicMock) -> None:
        trader_mock.position = "LONG"
        strategy = RuleStrategy(trader_mock)
        strategy.signal_sma = "SELL"
        assert strategy.can_sell() is True

    def test_no_l1_signal_blocks_sell(self, trader_mock: MagicMock) -> None:
        trader_mock.position = "LONG"
        strategy = RuleStrategy(trader_mock)
        assert strategy.can_sell() is False

    def test_wrong_position_blocks_sell(self, trader_mock: MagicMock) -> None:
        trader_mock.position = "READY"
        strategy = RuleStrategy(trader_mock)
        strategy.signal_sma = "SELL"
        assert strategy.can_sell() is False

    def test_l1_ema_sell_with_confirmation(self, trader_mock: MagicMock) -> None:
        trader_mock.position = "LONG"
        trader_mock.LEVEL1_SIGNALS = frozenset({"EMA", "TREND"})
        trader_mock.LEVEL2_SIGNALS = frozenset({"RSI", "MACD"})
        trader_mock.LEVEL2_MIN = 1
        strategy = RuleStrategy(trader_mock)
        strategy.signal_ema = "SELL"
        strategy.signal_macd = "SELL"
        assert strategy.can_sell() is True

    def test_insufficient_confirmations_blocks_sell(
        self, trader_mock: MagicMock
    ) -> None:
        trader_mock.position = "LONG"
        trader_mock.LEVEL1_SIGNALS = frozenset({"EMA"})
        trader_mock.LEVEL2_SIGNALS = frozenset({"RSI", "MACD"})
        trader_mock.LEVEL2_MIN = 1
        strategy = RuleStrategy(trader_mock)
        strategy.signal_ema = "SELL"
        # no confirmations
        assert strategy.can_sell() is False


# ---------------------------------------------------------------------------
# Signal string
# ---------------------------------------------------------------------------


class TestSignalString:
    def test_format_contains_all_indicators(self, trader_mock: MagicMock) -> None:
        strategy = RuleStrategy(trader_mock)
        s = strategy.get_signal_string()
        for prefix in (
            "SMA:",
            "EMA:",
            "TREND:",
            "RSI:",
            "MACD:",
            "STOCH:",
            "BB:",
            "VOL:",
        ):  # noqa: E501
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
        assert s.count("HOLD") == 8
