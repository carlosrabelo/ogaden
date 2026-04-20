"""Trading strategy implementations."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ogaden.trader import Trader

log = logging.getLogger(__name__)


class StrategyConfig:
    """Configuration for different strategy modes."""

    def __init__(self, mode: str = "balanced"):
        self.mode = mode

        if mode == "conservative":
            self.min_confirmations = 2
            self.volume_required = True
            self.trend_weight = 2
            self.rsi_buy = 35
            self.rsi_sell = 65
            self.fast_ema = 9
            self.slow_ema = 21
            self.trend_filter_ema = 200
            self.cooldown_cycles = 10
            self.min_trade_margin_pct = 0.5
            self.profit_threshold = 1.0
            self.loss_threshold = 1.0
            self.atr_stop_multiplier = 2.0
            self.position_size_pct = 15.0

        elif mode == "balanced":
            self.min_confirmations = 1
            self.volume_required = False
            self.trend_weight = 1
            self.rsi_buy = 40
            self.rsi_sell = 60
            self.fast_ema = 7
            self.slow_ema = 14
            self.trend_filter_ema = 100
            self.cooldown_cycles = 5
            self.min_trade_margin_pct = 0.3
            self.profit_threshold = 0.0
            self.loss_threshold = 0.0
            self.atr_stop_multiplier = 2.0
            self.position_size_pct = 25.0

        elif mode == "aggressive":
            self.min_confirmations = 1
            self.volume_required = False
            self.trend_weight = 1
            self.rsi_buy = 45
            self.rsi_sell = 55
            self.fast_ema = 5
            self.slow_ema = 10
            self.trend_filter_ema = 50
            self.cooldown_cycles = 2
            self.min_trade_margin_pct = 0.2
            self.profit_threshold = 0.0
            self.loss_threshold = 0.0
            self.atr_stop_multiplier = 1.5
            self.position_size_pct = 25.0

        else:
            raise ValueError(f"Unknown strategy mode: {mode!r}")


class BaseStrategy:
    """Abstract trading strategy."""

    def __init__(self, trader: Trader) -> None:
        self.trader = trader

    def evaluate(self) -> None:
        pass

    def can_buy(self) -> bool:
        return False

    def can_sell(self) -> bool:
        return False

    def get_signal_string(self) -> str:
        return "HOLD"


class RuleStrategy(BaseStrategy):
    """Indicator-based trading strategy.

    Decision logic
    --------------
    Primary signals  — EMA (positional) and TREND: at least one must be BUY/SELL.
    Confirmations    — RSI, MACD, BB, STOCH: need `min_confirmations` agreeing.
    Volume gate      — when `volume_required=True`, VOL must be BUY/SELL or the
                       trade is blocked regardless of other signals.
    """

    def __init__(self, trader: Trader, mode: str = "balanced") -> None:
        super().__init__(trader)
        self.config = StrategyConfig(mode)
        self.signal_ema: str = "HOLD"
        self.signal_rsi: str = "HOLD"
        self.signal_ema_trend: str = "HOLD"
        self.signal_volume: str = "HOLD"
        self.signal_macd: str = "HOLD"
        self.signal_bb: str = "HOLD"
        self.signal_stoch: str = "HOLD"

    def evaluate(self) -> None:
        # Apply mode-specific indicator parameters to the trader so that
        # calculate_* methods use the right windows and thresholds.
        self.trader.FAST_EMA = self.config.fast_ema
        self.trader.SLOW_EMA = self.config.slow_ema
        self.trader.RSI_BUY_THRESHOLD = self.config.rsi_buy
        self.trader.RSI_SELL_THRESHOLD = self.config.rsi_sell

        self.trader.calculate_rsi()
        self.trader.calculate_rsi_signal()

        self.trader.calculate_ema()
        self.trader.calculate_ema_signal()

        self.trader.calculate_ema_trend()
        self.trader.calculate_ema_signal_trend()

        self.trader.calculate_volume_indicators()
        self.trader.calculate_volume_signal()

        self.trader.calculate_atr()

        self.trader.calculate_macd()
        self.trader.calculate_macd_signal()

        self.trader.calculate_bollinger_bands()
        self.trader.calculate_bollinger_signal()

        self.trader.calculate_stochastic()
        self.trader.calculate_stochastic_signal()

        self.signal_ema = self.trader.data["signal_ema"].iloc[-1]
        self.signal_rsi = self.trader.data["signal_rsi"].iloc[-1]
        self.signal_ema_trend = self.trader.data["signal_ema_trend"].iloc[-1]
        self.signal_volume = self.trader.data["signal_volume"].iloc[-1]
        self.signal_macd = self.trader.data["signal_macd"].iloc[-1]
        self.signal_bb = self.trader.data["signal_bb"].iloc[-1]
        self.signal_stoch = self.trader.data["signal_stoch"].iloc[-1]

    def can_buy(self) -> bool:
        if self.trader.position != "SELL":
            return False

        # Volume gate: block the trade entirely if volume confirmation is required
        # but not present.
        if self.config.volume_required and self.signal_volume != "BUY":
            log.debug(
                "BUY blocked: volume_required=True but VOL=%s", self.signal_volume
            )
            return False

        # Primary signals: EMA (positional) and TREND must have at least one BUY.
        primary_buy = self.signal_ema == "BUY" or self.signal_ema_trend == "BUY"
        if not primary_buy:
            return False

        # Confirmation signals: RSI, MACD, BB, STOCH.
        confirmations = sum(
            [
                self.signal_rsi == "BUY",
                self.signal_macd == "BUY",
                self.signal_bb == "BUY",
                self.signal_stoch == "BUY",
            ]
        )

        if confirmations < self.config.min_confirmations:
            log.debug(
                "BUY blocked: %d/%d confirmations",
                confirmations,
                self.config.min_confirmations,
            )
            return False

        return True

    def can_sell(self) -> bool:
        if self.trader.position != "BUY":
            return False

        # Volume gate.
        if self.config.volume_required and self.signal_volume != "SELL":
            log.debug(
                "SELL blocked: volume_required=True but VOL=%s", self.signal_volume
            )
            return False

        # Primary signals.
        primary_sell = self.signal_ema == "SELL" or self.signal_ema_trend == "SELL"
        if not primary_sell:
            return False

        # Confirmation signals.
        confirmations = sum(
            [
                self.signal_rsi == "SELL",
                self.signal_macd == "SELL",
                self.signal_bb == "SELL",
                self.signal_stoch == "SELL",
            ]
        )

        if confirmations < self.config.min_confirmations:
            log.debug(
                "SELL blocked: %d/%d confirmations",
                confirmations,
                self.config.min_confirmations,
            )
            return False

        return True

    def get_signal_string(self) -> str:
        signals = [
            f"EMA:{self.signal_ema}",
            f"RSI:{self.signal_rsi}",
            f"TREND:{self.signal_ema_trend}",
            f"VOL:{self.signal_volume}",
            f"MACD:{self.signal_macd}",
            f"BB:{self.signal_bb}",
            f"STOCH:{self.signal_stoch}",
        ]
        return " / ".join(signals)
