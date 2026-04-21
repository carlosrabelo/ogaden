"""Trading strategy implementations."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ogaden.trader import Trader

log = logging.getLogger(__name__)


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
    LEVEL1 signals — at least one must be BUY/SELL (primary gate).
    LEVEL2 signals — need at least LEVEL2_MIN agreeing (confirmations).
    LEVEL3 signals — all must agree if the set is non-empty (hard gate).
    """

    def __init__(self, trader: Trader) -> None:
        super().__init__(trader)
        self.signal_ema: str = "HOLD"
        self.signal_ema_trend: str = "HOLD"
        self.signal_sma: str = "HOLD"
        self.signal_rsi: str = "HOLD"
        self.signal_macd: str = "HOLD"
        self.signal_stoch: str = "HOLD"
        self.signal_bb: str = "HOLD"
        self.signal_volume: str = "HOLD"

    def _signals_dict(self) -> dict[str, str]:
        return {
            "EMA": self.signal_ema,
            "TREND": self.signal_ema_trend,
            "SMA": self.signal_sma,
            "RSI": self.signal_rsi,
            "MACD": self.signal_macd,
            "STOCH": self.signal_stoch,
            "BB": self.signal_bb,
            "VOL": self.signal_volume,
        }

    def evaluate(self) -> None:
        self.trader.calculate_ema()
        self.trader.calculate_ema_signal()

        self.trader.calculate_ema_trend()
        self.trader.calculate_ema_signal_trend()

        self.trader.calculate_sma()
        self.trader.calculate_sma_signal()

        self.trader.calculate_rsi()
        self.trader.calculate_rsi_signal()

        self.trader.calculate_atr()

        self.trader.calculate_macd()
        self.trader.calculate_macd_signal()

        self.trader.calculate_stochastic()
        self.trader.calculate_stochastic_signal()

        self.trader.calculate_bollinger_bands()
        self.trader.calculate_bollinger_signal()

        self.trader.calculate_volume_indicators()
        self.trader.calculate_volume_signal()

        self.signal_ema = self.trader.data["signal_ema"].iloc[-1]
        self.signal_ema_trend = self.trader.data["signal_ema_trend"].iloc[-1]
        self.signal_sma = self.trader.data["signal_sma"].iloc[-1]
        self.signal_rsi = self.trader.data["signal_rsi"].iloc[-1]
        self.signal_macd = self.trader.data["signal_macd"].iloc[-1]
        self.signal_stoch = self.trader.data["signal_stoch"].iloc[-1]
        self.signal_bb = self.trader.data["signal_bb"].iloc[-1]
        self.signal_volume = self.trader.data["signal_volume"].iloc[-1]

    def can_buy(self) -> bool:
        if self.trader.position != "READY":
            return False

        sigs = self._signals_dict()
        direction = "BUY"

        l1 = self.trader.LEVEL1_SIGNALS
        l2 = self.trader.LEVEL2_SIGNALS
        l3 = self.trader.LEVEL3_SIGNALS
        l2_min = self.trader.LEVEL2_MIN

        if l1 and not any(sigs.get(s) == direction for s in l1):
            log.debug("BUY blocked: no LEVEL1 signal (%s)", sorted(l1))
            return False

        if l2:
            count = sum(sigs.get(s) == direction for s in l2)
            if count < l2_min:
                log.debug("BUY blocked: %d/%d LEVEL2 confirmations", count, l2_min)
                return False

        if l3 and not all(sigs.get(s) == direction for s in l3):
            failing = [s for s in l3 if sigs.get(s) != direction]
            log.debug("BUY blocked: LEVEL3 gate failed: %s", failing)
            return False

        return True

    def can_sell(self) -> bool:
        if self.trader.position != "LONG":
            return False

        sigs = self._signals_dict()
        direction = "SELL"

        l1 = self.trader.LEVEL1_SIGNALS
        l2 = self.trader.LEVEL2_SIGNALS
        l3 = self.trader.LEVEL3_SIGNALS
        l2_min = self.trader.LEVEL2_MIN

        if l1 and not any(sigs.get(s) == direction for s in l1):
            log.debug("SELL blocked: no LEVEL1 signal (%s)", sorted(l1))
            return False

        if l2:
            count = sum(sigs.get(s) == direction for s in l2)
            if count < l2_min:
                log.debug("SELL blocked: %d/%d LEVEL2 confirmations", count, l2_min)
                return False

        if l3 and not all(sigs.get(s) == direction for s in l3):
            failing = [s for s in l3 if sigs.get(s) != direction]
            log.debug("SELL blocked: LEVEL3 gate failed: %s", failing)
            return False

        return True

    def get_signal_string(self) -> str:
        signals = [
            f"SMA:{self.signal_sma}",
            f"EMA:{self.signal_ema}",
            f"TREND:{self.signal_ema_trend}",
            f"RSI:{self.signal_rsi}",
            f"MACD:{self.signal_macd}",
            f"STOCH:{self.signal_stoch}",
            f"BB:{self.signal_bb}",
            f"VOL:{self.signal_volume}",
        ]
        return " / ".join(signals)
