"""Trading state machine and orchestration."""

import json
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING
from zoneinfo import ZoneInfo

from pymemcache.client import base

from ogaden.broker import Broker

if TYPE_CHECKING:
    from ogaden.exchange import ExchangeProtocol
from ogaden.errors import FetchError, OrderError
from ogaden.persistence import load_state, save_state
from ogaden.strategy import BaseStrategy, RuleStrategy

log = logging.getLogger(__name__)

CYCLE_SLEEP = 60
MEMCACHE_TTL = 120
PRICE_HISTORY_MAX = 40
PRICE_HISTORY_TTL = 3600  # 1 hour — survives engine pauses between cycles


def _dash_or(value: float, decimals: int) -> str:
    """Format *value* or return a dash if it is zero."""
    if value > 0:
        return f"{value:.{decimals}f}"
    return "-"


@dataclass
class Metrics:
    """Runtime metrics collected across trading cycles."""

    cycles: int = 0
    buys: int = 0
    sells: int = 0
    fetch_errors: int = 0
    order_errors: int = 0
    pnl_history: list[float] = field(default_factory=list)
    trade_history: list[dict[str, object]] = field(default_factory=list)

    def record_pnl(self, pnl_pct: float) -> None:
        """Append a closed-trade P&L percentage to history (capped at 1000 entries)."""
        self.pnl_history.append(round(pnl_pct, 4))
        if len(self.pnl_history) > 1000:
            self.pnl_history = self.pnl_history[-1000:]

    def record_trade(self, record: dict[str, object]) -> None:
        """Append a completed trade record (capped at 200 entries)."""
        self.trade_history.append(record)
        if len(self.trade_history) > 200:
            self.trade_history = self.trade_history[-200:]

    @property
    def total_pnl(self) -> float:
        """Sum of all recorded P&L percentages."""
        return round(sum(self.pnl_history), 4)

    @property
    def win_rate(self) -> float:
        """Fraction of profitable trades (0.0 – 1.0); 0.0 if no trades."""
        if not self.pnl_history:
            return 0.0
        wins = sum(1 for p in self.pnl_history if p > 0)
        return round(wins / len(self.pnl_history), 4)

    @property
    def rolling_drawdown(self) -> float:
        """Sum of negative P&L across the last 20 closed trades (always <= 0)."""
        if not self.pnl_history:
            return 0.0
        recent = self.pnl_history[-20:]
        return round(sum(p for p in recent if p < 0), 4)

    @property
    def consecutive_losses(self) -> int:
        """Current streak of consecutive losing trades."""
        count = 0
        for p in reversed(self.pnl_history):
            if p < 0:
                count += 1
            else:
                break
        return count


class Trader(Broker):
    """Orchestrates fetch → evaluate → act → report cycles."""

    def __init__(self, exchange: "ExchangeProtocol | None" = None) -> None:
        super().__init__(exchange=exchange)

        self.memcache = base.Client(
            server=(self.MEMCACHED_HOST, self.MEMCACHED_PORT),
            key_prefix="ogaden",
        )

        self.purchase_price: float = 0.0
        self.difference_price_v: float = 0.0
        self.difference_price_p: float = 0.0

        # Mandatory risk management: stop-loss / take-profit prices
        self.stop_loss_price: float = 0.0
        self.take_profit_price: float = 0.0
        self.trailing_stop_price: float = 0.0

        # Circuit breaker: set to True when drawdown thresholds are breached
        self.circuit_breaker_active: bool = False

        self.base_quote_balance: float = 0.0
        self.expected_balance: float = 0.0
        self.trailing_balance: float = 0.0

        # Cooldown after a losing trade
        self.cooldown_until_cycle: int = 0
        self.last_trade_pnl: float = 0.0

        # Trend filter value (long-term EMA)
        self.trend_ema_value: float = 0.0

        self.position: str = "READY"
        self.last_action: str = "HOLD"
        self.rsi_value: float = 0.0

        self._sell_reason: str = "SIGNAL"
        self._pending_entry: dict[str, object] = {}

        self.metrics = Metrics()

        self.strategy: BaseStrategy
        self.strategy = RuleStrategy(self)

    # -- Lifecycle -------------------------------------------------------------

    def setup(self) -> None:
        """Initialize balances, restore persisted state, and publish initial status."""
        self._running = False
        self._check_memcached()

        if self.SANDBOX:
            self.base_balance = self.BASE_BALANCE_DEFAULT
            self.quote_balance = self.QUOTE_BALANCE_DEFAULT

        self._load_state()
        self.status()

    def _check_memcached(self) -> None:
        """Verify Memcached is reachable or warn and continue."""
        try:
            self.memcache.set("_health", b"ok")
            self.memcache.delete("_health")
        except Exception as exc:
            log.warning(
                "Memcached unreachable at %s:%d — dashboard will not receive updates. "
                "Start Memcached or set MEMCACHED_HOST/MEMCACHED_PORT. Error: %s",
                self.MEMCACHED_HOST,
                self.MEMCACHED_PORT,
                exc,
            )

    def start(self) -> None:
        """Mark the trader as running (used by engine for graceful shutdown)."""
        self._running = True

    def stop(self) -> None:
        """Signal the trader to stop after the current cycle and release resources."""
        self._running = False
        try:
            self.memcache.close()
        except Exception:
            log.debug("Memcached close failed (ignored)", exc_info=True)

    @property
    def is_running(self) -> bool:
        """Check if the trader is currently running."""
        return getattr(self, "_running", False)

    # -- State persistence -----------------------------------------------------

    def _save_state(self) -> None:
        """Persist current trading state to the configured STATE_FILE."""
        state: dict[str, object] = {
            "symbol": self.SYMBOL,
            "position": self.position,
            "purchase_price": self.purchase_price,
            "trailing_balance": self.trailing_balance,
            "trailing_stop_price": self.trailing_stop_price,
            "stop_loss_price": self.stop_loss_price,
            "take_profit_price": self.take_profit_price,
            "cooldown_until_cycle": self.cooldown_until_cycle,
            "last_trade_pnl": self.last_trade_pnl,
            "circuit_breaker_active": self.circuit_breaker_active,
            "metrics": {
                "cycles": self.metrics.cycles,
                "buys": self.metrics.buys,
                "sells": self.metrics.sells,
                "fetch_errors": self.metrics.fetch_errors,
                "order_errors": self.metrics.order_errors,
                "pnl_history": self.metrics.pnl_history,
                "trade_history": self.metrics.trade_history,
            },
        }
        if self.SANDBOX:
            state["base_balance"] = self.base_balance
            state["quote_balance"] = self.quote_balance
        save_state(state, self.STATE_FILE)

    def _load_state(self) -> None:
        """Restore trading state from STATE_FILE if it exists.

        If the saved symbol differs from the current configuration,
        all indicators and state are reset — the saved state is ignored.
        """
        state = load_state(self.STATE_FILE)
        if not state:
            return

        saved_symbol = state.get("symbol", "")
        if saved_symbol and saved_symbol != self.SYMBOL:
            log.info(
                "Symbol changed (%s → %s) — resetting state and chart history",
                saved_symbol,
                self.SYMBOL,
            )
            try:
                self.memcache.delete("price_history")
                self.memcache.delete("trade_history")
            except Exception as exc:
                log.warning("Memcache reset on symbol change failed: %s", exc)
            return  # Start fresh

        _pos_migrate = {
            "WAITING": "READY",
            "HOLDING": "LONG",
            "SELL": "READY",
            "FLAT": "READY",
            "BUY": "LONG",
        }
        raw_pos = str(state.get("position", self.position))
        self.position = _pos_migrate.get(raw_pos, raw_pos)
        self.purchase_price = float(state.get("purchase_price", 0.0))  # type: ignore[arg-type]
        self.trailing_balance = float(state.get("trailing_balance", 0.0))  # type: ignore[arg-type]
        self.trailing_stop_price = float(state.get("trailing_stop_price", 0.0))  # type: ignore[arg-type]
        self.stop_loss_price = float(state.get("stop_loss_price", 0.0))  # type: ignore[arg-type]
        self.take_profit_price = float(state.get("take_profit_price", 0.0))  # type: ignore[arg-type]
        cooldown_raw = state.get("cooldown_until_cycle", 0)
        if isinstance(cooldown_raw, (int, float)):
            self.cooldown_until_cycle = int(cooldown_raw)
        else:
            self.cooldown_until_cycle = 0
        self.last_trade_pnl = float(state.get("last_trade_pnl", 0.0))  # type: ignore[arg-type]
        self.circuit_breaker_active = bool(state.get("circuit_breaker_active", False))

        if self.SANDBOX:
            if "base_balance" in state:
                self.base_balance = float(state["base_balance"])  # type: ignore[arg-type]
            if "quote_balance" in state:
                self.quote_balance = float(state["quote_balance"])  # type: ignore[arg-type]

        # Restore metrics if available
        metrics_state = state.get("metrics")
        if isinstance(metrics_state, dict):
            self.metrics.cycles = int(metrics_state.get("cycles", 0))
            self.metrics.buys = int(metrics_state.get("buys", 0))
            self.metrics.sells = int(metrics_state.get("sells", 0))
            self.metrics.fetch_errors = int(metrics_state.get("fetch_errors", 0))
            self.metrics.order_errors = int(metrics_state.get("order_errors", 0))
            pnl_history = metrics_state.get("pnl_history", [])
            if isinstance(pnl_history, list):
                self.metrics.pnl_history = [float(x) for x in pnl_history]

            trade_history = metrics_state.get("trade_history", [])
            if isinstance(trade_history, list):
                self.metrics.trade_history = [
                    r for r in trade_history if isinstance(r, dict)
                ]

        log.info(
            "State restored: position=%s purchase_price=%.8f "
            "stop_loss=%.8f take_profit=%.8f cooldown=%d",
            self.position,
            self.purchase_price,
            self.stop_loss_price,
            self.take_profit_price,
            self.cooldown_until_cycle,
        )

    def _is_circuit_breaker_active(self) -> bool:
        """Return True and halt trading if drawdown thresholds are breached."""
        if self.circuit_breaker_active:
            return True

        triggered = False
        drawdown = self.metrics.rolling_drawdown

        if self.MAX_DRAWDOWN_PCT > 0.0 and drawdown <= -self.MAX_DRAWDOWN_PCT:
            log.error(
                "CIRCUIT BREAKER: drawdown %.2f%% <= -%.2f%% — halting",
                drawdown,
                self.MAX_DRAWDOWN_PCT,
            )
            triggered = True

        consecutive = self.metrics.consecutive_losses
        if (
            self.MAX_CONSECUTIVE_LOSSES > 0
            and consecutive >= self.MAX_CONSECUTIVE_LOSSES
        ):
            log.error(
                "CIRCUIT BREAKER: %d consecutive losses >= %d threshold — halting",
                consecutive,
                self.MAX_CONSECUTIVE_LOSSES,
            )
            triggered = True

        if triggered:
            self.circuit_breaker_active = True
            self._save_state()

        return triggered

    def execute(self) -> None:
        """Run a single fetch → evaluate → act cycle, then sleep."""
        self.metrics.cycles += 1
        try:
            self.fetch_vars()
            self.fetch_data()
        except FetchError:
            self.metrics.fetch_errors += 1
            log.exception("Data fetch failed; skipping cycle")
            # Sleep with periodic shutdown checks
            for _ in range(CYCLE_SLEEP):
                if not self.is_running:
                    log.info("Shutdown requested, breaking execution cycle")
                    return
                time.sleep(1)
            return

        if self.data.empty or self.data["close"].isna().all():
            log.warning("No market data available; skipping cycle")
            time.sleep(CYCLE_SLEEP)
            return

        self._update_vars()
        self.strategy.evaluate()

        if "rsi" in self.data.columns and not self.data["rsi"].empty:
            self.rsi_value = self.data["rsi"].iloc[-1]

        self.status(quiet=False)

        try:
            if self.can_buy():
                self.last_action = "BUY"
                self._do_buy()
            elif self.can_sell():
                self.last_action = "SELL"
                self._do_sell()
            else:
                self.last_action = "HOLD"
                log.info("HOLD")
        except OrderError:
            self.metrics.order_errors += 1
            log.exception("Order execution failed")

        self._update_vars()
        self.status(quiet=True)

        # Sleep with periodic shutdown checks
        for _ in range(CYCLE_SLEEP):
            if not self.is_running:
                log.info("Shutdown requested, breaking execution cycle")
                return
            time.sleep(1)

    def can_buy(self) -> bool:
        if self.position != "READY":
            return False

        if self.trend_ema_value > 0 and self.current_price < self.trend_ema_value:
            log.debug(
                "BUY blocked: price %.4f below trend EMA %.4f",
                self.current_price,
                self.trend_ema_value,
            )
            return False

        if not self.data.empty and "atr" in self.data.columns:
            atr = self.data["atr"].iloc[-1]
            if atr > 0 and self.current_price > 0:
                expected_move_pct = (atr / self.current_price) * 100.0 * 2
                fee_buffer = 0.2
                if expected_move_pct < self.MIN_TRADE_MARGIN_PCT + fee_buffer:
                    log.debug(
                        "BUY blocked: expected move %.3f%% < min %.2f%% + fee %.2f%%",
                        expected_move_pct,
                        self.MIN_TRADE_MARGIN_PCT,
                        fee_buffer,
                    )
                    return False

        return self.strategy.can_buy()

    def can_sell(self) -> bool:
        if self.position != "LONG":
            return False

        # Forced stop-loss: exit immediately when price hits stop
        if self.stop_loss_price > 0 and self.current_price <= self.stop_loss_price:
            log.warning(
                "STOP-LOSS triggered: %.2f <= %.2f (loss: %.2f%%)",
                self.current_price,
                self.stop_loss_price,
                self.difference_price_p,
            )
            self._sell_reason = "STOP_LOSS"
            return True

        # Price-based trailing stop: exit when price falls below peak by threshold
        if (
            self.trailing_stop_price > 0
            and self.current_price <= self.trailing_stop_price
        ):
            log.info(
                "TRAILING STOP triggered: %.8f <= %.8f",
                self.current_price,
                self.trailing_stop_price,
            )
            self._sell_reason = "TRAILING_STOP"
            return True

        # Forced take-profit: exit when price reaches target
        if self.take_profit_price > 0 and self.current_price >= self.take_profit_price:
            log.info(
                "TAKE-PROFIT hit: %.2f >= %.2f (profit: %.2f%%)",
                self.current_price,
                self.take_profit_price,
                self.difference_price_p,
            )
            self._sell_reason = "TAKE_PROFIT"
            return True

        if self.PROFIT_ENABLE and self.difference_price_p > self.PROFIT_THRESHOLD:
            self._sell_reason = "PROFIT_THRESHOLD"
            return True

        if self.LOSS_ENABLE and self.difference_price_p < self.LOSS_THRESHOLD:
            self._sell_reason = "LOSS_THRESHOLD"
            return True

        if self.TRAILING_ENABLE and self.trailing_balance > self.expected_balance:
            self._sell_reason = "TRAILING_BALANCE"
            return True

        result = self.strategy.can_sell()
        if result:
            self._sell_reason = "SIGNAL"
        return result

    def _do_buy(self) -> None:
        pre_base = self.base_balance
        if self.execute_buy():
            self._pending_entry = {
                "entry_time": datetime.now().isoformat(timespec="seconds"),
                "entry_price": round(self.current_price, 8),
                "quantity": round(self.base_balance - pre_base, 8),
            }
            self._sell_reason = "SIGNAL"
            self.purchase_price = self.current_price
            self.position = "LONG"

            # Set ATR-based stop-loss and take-profit (2:1 reward ratio)
            if not self.data.empty and "atr" in self.data.columns:
                atr = self.data["atr"].iloc[-1]
                if atr > 0:
                    self.stop_loss_price = self.purchase_price - (
                        atr * self.ATR_STOP_MULTIPLIER
                    )
                    self.take_profit_price = self.purchase_price + (
                        atr * self.ATR_STOP_MULTIPLIER * 2
                    )
                    log.info(
                        "Risk set: SL=%.2f (%.1f%%) TP=%.2f (+%.1f%%) ATR=%.4f",
                        self.stop_loss_price,
                        (self.stop_loss_price / self.purchase_price - 1) * 100,
                        self.take_profit_price,
                        (self.take_profit_price / self.purchase_price - 1) * 100,
                        atr,
                    )
                else:
                    self._set_fallback_sl_tp()
            else:
                self._set_fallback_sl_tp()

            self.metrics.buys += 1
            self._save_state()

    def _set_fallback_sl_tp(self) -> None:
        """Set fixed % stop-loss/take-profit when ATR is unavailable."""
        self.stop_loss_price = self.purchase_price * 0.98  # 2% stop
        self.take_profit_price = self.purchase_price * 1.04  # 4% take-profit
        log.info(
            "Risk set (fallback): SL=%.2f (-2.0%%) TP=%.2f (+4.0%%)",
            self.stop_loss_price,
            self.take_profit_price,
        )

    def _do_sell(self) -> None:
        if self.execute_sell():
            pnl = self.difference_price_p
            self.metrics.record_pnl(pnl)
            self.last_trade_pnl = pnl

            if self._pending_entry:
                self.metrics.record_trade(
                    {
                        **self._pending_entry,
                        "exit_time": datetime.now().isoformat(timespec="seconds"),
                        "exit_price": round(self.current_price, 8),
                        "pnl_pct": round(pnl, 4),
                        "exit_reason": self._sell_reason,
                    }
                )
                self._pending_entry = {}

            # Set cooldown after a losing trade
            if pnl < 0:
                self.cooldown_until_cycle = self.metrics.cycles + self.COOLDOWN_CYCLES
                log.info(
                    "Loss recorded (%.2f%%) — cooldown for %d cycles",
                    pnl,
                    self.COOLDOWN_CYCLES,
                )

            # Reset position and risk management levels
            self.purchase_price = 0.0
            self.stop_loss_price = 0.0
            self.take_profit_price = 0.0
            self.trailing_stop_price = 0.0
            self.position = "READY"
            self.metrics.sells += 1
            self._save_state()

    def _refresh_flat_position(self) -> None:
        if self.position == "LONG":
            return
        if self._is_circuit_breaker_active():
            self.position = "BLOCKED"
        elif self.metrics.cycles < self.cooldown_until_cycle:
            self.position = "COOLDOWN"
        else:
            self.position = "READY"

    def _update_vars(self) -> None:
        """Recompute derived balances and price differences."""
        self.base_quote_balance = self.base_balance * self.current_price
        self.expected_balance = self.quote_balance + self.base_quote_balance

        self._refresh_flat_position()

        if self.position != "LONG":
            self.trailing_balance = 0.0
            self.difference_price_v = 0.0
            self.difference_price_p = 0.0

        if self.position == "LONG":
            trailing = self.expected_balance * self.TRAILING_THRESHOLD
            if trailing > self.trailing_balance:
                self.trailing_balance = trailing

            if self.TRAILING_STOP_ENABLE and self.current_price > 0:
                trail_distance = self.current_price * (self.TRAILING_STOP_PCT / 100.0)
                new_trail = self.current_price - trail_distance
                if new_trail > self.trailing_stop_price:
                    self.trailing_stop_price = new_trail
                    log.debug("Trailing stop updated: %.8f", self.trailing_stop_price)

            if self.purchase_price > 0:
                self.difference_price_v = self.current_price - self.purchase_price
                self.difference_price_p = (
                    self.difference_price_v / self.purchase_price * 100.0
                )
            else:
                self.difference_price_v = 0.0
                self.difference_price_p = 0.0

        # Calculate long-term trend EMA for buy filter
        self._update_trend_ema()

    def _update_trend_ema(self) -> None:
        """Calculate the trend-filter EMA and store the latest value."""
        if self.data.empty or "close" not in self.data.columns:
            self.trend_ema_value = 0.0
            return

        if len(self.data) < self.TREND_FILTER_EMA:
            # Not enough data for the full window — use what we have
            window = len(self.data)
        else:
            window = self.TREND_FILTER_EMA

        try:
            import ta as _ta

            self.trend_ema_value = (
                _ta.trend.EMAIndicator(close=self.data["close"], window=window)
                .ema_indicator()
                .iloc[-1]
            )
        except Exception:
            self.trend_ema_value = 0.0

    def status(self, quiet: bool = False) -> None:
        """Log current state and push snapshot to Memcached."""
        tz = ZoneInfo(self.TIMEZONE)
        update_time = datetime.now(tz).strftime("%d/%m/%Y %H:%M:%S")
        signal_str = self.strategy.get_signal_string()

        if not quiet:
            # Show signal legend on first run
            if not hasattr(self, "_legend_shown"):
                log.info("=== SIGNAL LEGEND ===")
                log.info(
                    "EMA: EMA Crossover (Fast/Slow) | RSI: Relative Strength Index"
                    " | TREND: EMA Trend Confirmation"
                )
                log.info(
                    "VOL: Volume Analysis | MACD: MACD Signal"
                    " | BB: Bollinger Bands | STOCH: Stochastic Oscillator"
                )
                log.info("===================")
                self._legend_shown = True
            log.info(
                "STATUS | %s | %s %s | pos=%s | signal=%s | "
                "base=%.8f quote=%.8f expected=%.8f | "
                "price=%.8f purchase=%.8f diff=%.8f/%.4f%%",
                update_time,
                self.SYMBOL,
                self.INTERVAL,
                self.position,
                signal_str,
                self.base_balance,
                self.quote_balance,
                self.expected_balance,
                self.current_price,
                self.purchase_price,
                self.difference_price_v,
                self.difference_price_p,
            )
            if self.stop_loss_price > 0:
                log.info(
                    "RISK    | SL=%.2f TP=%.2f trend_ema=%.2f cooldown=%d",
                    self.stop_loss_price,
                    self.take_profit_price,
                    self.trend_ema_value,
                    max(0, self.cooldown_until_cycle - self.metrics.cycles),
                )
            log.info(
                "METRICS | cycle=%d buys=%d sells=%d fetch_err=%d order_err=%d "
                "total_pnl=%.4f%% win_rate=%.1f%% drawdown=%.2f%% consec_losses=%d",
                self.metrics.cycles,
                self.metrics.buys,
                self.metrics.sells,
                self.metrics.fetch_errors,
                self.metrics.order_errors,
                self.metrics.total_pnl,
                self.metrics.win_rate * 100,
                self.metrics.rolling_drawdown,
                self.metrics.consecutive_losses,
            )
            if self.circuit_breaker_active:
                log.error(
                    "CIRCUIT BREAKER ACTIVE — trading halted. "
                    "Reset circuit_breaker_active in state file to resume."
                )

        data = {
            "update_time": update_time,
            "symbol": self.SYMBOL,
            "interval": self.INTERVAL,
            "position": self.position,
            "action": self.last_action,
            "strategy": (
                f"L1:{','.join(sorted(self.LEVEL1_SIGNALS)) or '-'}"
                f" L2:{','.join(sorted(self.LEVEL2_SIGNALS)) or '-'}"
                f"(min={self.LEVEL2_MIN})"
                f" L3:{','.join(sorted(self.LEVEL3_SIGNALS)) or '-'}"
            ),
            "signal": signal_str,
            "base_balance": f"{self.base_balance:.6f}",
            "quote_balance": f"{self.quote_balance:.2f}",
            "base_quote_balance": f"{self.base_quote_balance:.2f}",
            "expected_balance": f"{self.expected_balance:.2f}",
            "trailing_balance": f"{self.trailing_balance:.2f}",
            "current_price": f"{self.current_price:.8f}",
            "purchase_price": f"{self.purchase_price:.8f}",
            "difference_price": f"{self.difference_price_v:.8f}",
            "difference_price_p": f"{self.difference_price_p:+.2f}%",
            "cycle_sleep": str(CYCLE_SLEEP),
            "cycle": str(self.metrics.cycles),
            # Heartbeat: only written after a real API fetch (quiet=False).
            # The dashboard uses this to gate chart updates — one point per cycle.
            **({"price_heartbeat": str(self.metrics.cycles)} if not quiet else {}),
            # Risk management config
            "position_size_pct": f"{self.POSITION_SIZE_PCT:.0f}%",
            "atr_stop_mult": f"{self.ATR_STOP_MULTIPLIER:.1f}",
            "trend_filter_ema": str(self.TREND_FILTER_EMA),
            "cooldown_remaining": str(
                max(0, self.cooldown_until_cycle - self.metrics.cycles)
            ),
            "min_trade_margin_pct": f"{self.MIN_TRADE_MARGIN_PCT:.2f}%",
            "stop_loss": _dash_or(self.stop_loss_price, 2),
            "take_profit": _dash_or(self.take_profit_price, 2),
            "trailing_stop": _dash_or(self.trailing_stop_price, 2),
            "trend_ema_value": _dash_or(self.trend_ema_value, 2),
            "trade_history": json.dumps(self.metrics.trade_history[-50:]),
            "pending_trade": json.dumps(self._pending_entry)
            if self._pending_entry
            else "",
            "circuit_breaker": "true" if self.circuit_breaker_active else "false",
            "consecutive_losses": str(self.metrics.consecutive_losses),
            "rolling_drawdown": f"{self.metrics.rolling_drawdown:.2f}%",
            "win_rate": f"{self.metrics.win_rate * 100:.1f}%",
            "total_pnl": f"{self.metrics.total_pnl:.4f}%",
        }

        try:
            self.memcache.set_many(values=data, expire=MEMCACHE_TTL)
            log.debug("Memcache updated (%d keys)", len(data))
        except Exception as exc:
            log.warning("Memcache write failed: %s", exc)

        if not quiet:
            # Persist chart history so the dashboard can pre-populate on page load.
            # Written with a longer TTL so it survives brief engine pauses.
            try:
                raw = self.memcache.get("price_history")
                history: list[list[object]] = json.loads(raw) if raw else []
            except Exception:
                history = []
            time_label = (
                update_time.split(" ")[1] if " " in update_time else update_time
            )
            history.append([time_label, round(self.current_price, 2)])
            if len(history) > PRICE_HISTORY_MAX:
                history = history[-PRICE_HISTORY_MAX:]
            try:
                self.memcache.set(
                    "price_history", json.dumps(history), expire=PRICE_HISTORY_TTL
                )
            except Exception as exc:
                log.warning("Memcache price_history write failed: %s", exc)
