"""Order execution, sandbox simulation, and exchange API interaction."""

import logging
from decimal import ROUND_DOWN, Decimal, InvalidOperation
from typing import TYPE_CHECKING

import pandas as pd
from binance.client import Client

from ogaden.errors import FetchError, OrderError
from ogaden.indicators import IndicatorMixin
from ogaden.loader import Loader
from ogaden.rate_limiter import RateLimiter
from ogaden.retry import with_retry

if TYPE_CHECKING:
    from ogaden.exchange import ExchangeProtocol

log = logging.getLogger(__name__)

# One API call per 200 ms maximum (5 req/s, well within Binance weight limits).
_API_RATE_LIMITER = RateLimiter(min_interval=0.2)


class Broker(IndicatorMixin, Loader):
    """Manages exchange API interaction, balance tracking, and order execution.

    Inherits indicator methods from :class:`~ogaden.indicators.IndicatorMixin`.
    """

    def __init__(self, exchange: "ExchangeProtocol | None" = None) -> None:
        super().__init__()

        # Use injected exchange or default to Binance client
        if exchange is not None:
            self.exchange = exchange
        else:
            self.exchange = Client(self.API_KEY, self.API_SECRET)

        self._rate_limiter = _API_RATE_LIMITER

        self.base_balance: float = 0.0
        self.quote_balance: float = 0.0
        self.current_price: float = 0.0
        self.min_notional: float = 0.0
        self.step_size: float = 0.0
        self.min_quantity: float = 0.0

        self.data: pd.DataFrame = pd.DataFrame()

    # -- Exchange data fetching ------------------------------------------------

    @with_retry(
        max_attempts=3, base_delay=2.0, max_delay=30.0, exceptions=(FetchError,)
    )
    def fetch_vars(self) -> None:
        """Refresh balances, price, and exchange filter constraints.

        Retries up to 3 times with exponential backoff (2 s → 4 s → fail)
        on any :class:`~ogaden.errors.FetchError`.
        """
        if not self.SANDBOX:
            self.base_balance = self._fetch_balance(self.BASE_ASSET)
            self.quote_balance = self._fetch_balance(self.QUOTE_ASSET)

        self.current_price = self._fetch_current_price(self.SYMBOL)
        self.min_notional = self._fetch_minimum_notional(self.SYMBOL)
        self.step_size = self._fetch_step_size(self.SYMBOL)
        self.min_quantity = self._fetch_minimum_quantity(self.SYMBOL)

    def _fetch_balance(self, asset: str) -> float:
        """Return the free balance of *asset* from the exchange account."""
        self._rate_limiter.acquire()
        try:
            account_info = self.exchange.get_account()
            return float(
                next(
                    (
                        b["free"]
                        for b in account_info["balances"]
                        if b["asset"] == asset
                    ),
                    0.0,
                )
            )
        except Exception as exc:
            raise FetchError(f"Failed to fetch balance for {asset}") from exc

    def _fetch_current_price(self, symbol: str) -> float:
        """Return the latest trade price for *symbol*."""
        self._rate_limiter.acquire()
        try:
            ticker = self.exchange.get_symbol_ticker(symbol=symbol)
            return float(ticker["price"])
        except Exception as exc:
            raise FetchError(f"Failed to fetch price for {symbol}") from exc

    def _fetch_minimum_notional(self, symbol: str) -> float:
        """Return the NOTIONAL filter minimum value for *symbol*."""
        self._rate_limiter.acquire()
        try:
            info = self.exchange.get_symbol_info(symbol=symbol)
            result = next(
                (
                    f["minNotional"]
                    for f in info["filters"]
                    if f["filterType"] == "NOTIONAL"
                ),
                None,
            )
            if result is None:
                raise FetchError(
                    f"NOTIONAL filter not found for {symbol}. "
                    f"Available filters: {[f['filterType'] for f in info['filters']]}"
                )
            return float(result)
        except FetchError:
            raise
        except Exception as exc:
            raise FetchError(f"Failed to fetch minimum notional for {symbol}") from exc

    def _fetch_step_size(self, symbol: str) -> float:
        """Return the LOT_SIZE stepSize for *symbol*."""
        self._rate_limiter.acquire()
        try:
            info = self.exchange.get_symbol_info(symbol=symbol)
            result = next(
                (
                    f["stepSize"]
                    for f in info["filters"]
                    if f["filterType"] == "LOT_SIZE"
                ),
                None,
            )
            if result is None:
                raise FetchError(
                    f"LOT_SIZE filter not found for {symbol}. "
                    f"Available filters: {[f['filterType'] for f in info['filters']]}"
                )
            return float(result)
        except FetchError:
            raise
        except Exception as exc:
            raise FetchError(f"Failed to fetch step size for {symbol}") from exc

    def _fetch_minimum_quantity(self, symbol: str) -> float:
        """Return the LOT_SIZE minQty for *symbol*."""
        self._rate_limiter.acquire()
        try:
            info = self.exchange.get_symbol_info(symbol=symbol)
            result = next(
                (f["minQty"] for f in info["filters"] if f["filterType"] == "LOT_SIZE"),
                None,
            )
            if result is None:
                raise FetchError(
                    f"LOT_SIZE filter not found for {symbol}. "
                    f"Available filters: {[f['filterType'] for f in info['filters']]}"
                )
            return float(result)
        except FetchError:
            raise
        except Exception as exc:
            raise FetchError(f"Failed to fetch minimum quantity for {symbol}") from exc

    @with_retry(
        max_attempts=3, base_delay=2.0, max_delay=30.0, exceptions=(FetchError,)
    )
    def fetch_data(self) -> None:
        """Fetch klines and build the OHLCV DataFrame.

        Retries up to 3 times with exponential backoff on
        :class:`~ogaden.errors.FetchError`.
        """
        self._rate_limiter.acquire()
        try:
            klines = self.exchange.get_klines(
                symbol=self.SYMBOL,
                interval=self.INTERVAL,
                limit=self.LIMIT,
            )

            if not klines:
                raise FetchError(f"No klines data for {self.SYMBOL} {self.INTERVAL}")

            df = pd.DataFrame(
                klines,
                columns=[
                    "open_time",
                    "open",
                    "high",
                    "low",
                    "close",
                    "volume",
                    "close_time",
                    "quote_asset_volume",
                    "number_of_trades",
                    "taker_buy_base_asset_volume",
                    "taker_buy_quote_asset_volume",
                    "ignore",
                ],
            )

            # Keep OHLCV data for better indicators
            df = df[["close_time", "open", "high", "low", "close", "volume"]]

            # Convert to float
            for col in ["open", "high", "low", "close", "volume"]:
                df[col] = df[col].astype(float)

            df["close_time"] = (
                pd.to_datetime(df["close_time"], unit="ms", utc=True)
                .dt.tz_convert(self.TIMEZONE)
                .dt.floor("s")
                .dt.tz_localize(None)
            )

            self.data = df

        except FetchError:
            raise
        except Exception as exc:
            self.data = pd.DataFrame()
            raise FetchError(f"Failed to fetch candle data: {exc}") from exc

    # -- Order execution -------------------------------------------------------

    def execute_buy(self) -> bool:
        """Execute a market buy. Returns True if the order was placed.

        Uses position sizing based on :attr:`POSITION_SIZE_PCT` — only a
        fraction of the available quote balance is spent per trade.
        """
        # Effective buy power after position sizing
        effective_balance = self.quote_balance * (self.POSITION_SIZE_PCT / 100.0)

        if effective_balance < self.min_notional:
            log.warning(
                "Insufficient effective balance (%.2f%% of %.8f = %.8f) "
                "< min notional %.8f",
                self.POSITION_SIZE_PCT,
                self.quote_balance,
                effective_balance,
                self.min_notional,
            )
            return False

        if self.current_price <= 0:
            log.warning("Invalid current price; skipping buy order")
            return False

        if self.step_size <= 0:
            log.warning("Invalid step size; skipping buy order")
            return False

        quantity = self._apply_step_size(
            effective_balance / self.current_price, self.step_size
        )

        if quantity <= 0:
            log.warning("Calculated quantity is zero after step size; skipping buy")
            return False

        if quantity < self.min_quantity:
            log.warning(
                "Quantity %.8f below minimum %.8f",
                quantity,
                self.min_quantity,
            )
            return False

        if self.SANDBOX:
            total_cost = quantity * self.current_price
            fee = total_cost * 0.001
            self.base_balance += quantity
            self.quote_balance -= total_cost + fee
        else:
            try:
                self.exchange.order_market_buy(symbol=self.SYMBOL, quantity=quantity)
            except Exception as exc:
                raise OrderError(f"Buy order failed for {self.SYMBOL}") from exc

        log.info("BUY %.6f %s @ %.8f", quantity, self.BASE_ASSET, self.current_price)
        return True

    def execute_sell(self) -> bool:
        """Execute a market sell. Returns True if the order was placed."""
        if self.base_balance < self.min_quantity:
            log.warning(
                "Insufficient base balance: %.8f < min quantity %.8f",
                self.base_balance,
                self.min_quantity,
            )
            return False

        if self.step_size <= 0:
            log.warning("Invalid step size; skipping sell order")
            return False

        quantity = self._apply_step_size(self.base_balance, self.step_size)

        if quantity <= 0:
            log.warning("Calculated quantity is zero after step size; skipping sell")
            return False

        if quantity < self.min_quantity:
            log.warning(
                "Quantity %.8f below minimum %.8f",
                quantity,
                self.min_quantity,
            )
            return False

        if self.current_price <= 0:
            log.warning("Invalid current price; skipping sell order")
            return False

        if self.SANDBOX:
            total_sale = quantity * self.current_price
            fee = total_sale * 0.001
            self.base_balance -= quantity
            self.quote_balance += total_sale - fee
        else:
            try:
                self.exchange.order_market_sell(symbol=self.SYMBOL, quantity=quantity)
            except Exception as exc:
                raise OrderError(f"Sell order failed for {self.SYMBOL}") from exc

        log.info("SELL %.6f %s @ %.8f", quantity, self.BASE_ASSET, self.current_price)
        return True

    @staticmethod
    def _apply_step_size(quantity: float, step_size: float) -> float:
        """Normalize quantity down to the nearest valid step size increment."""
        try:
            q = Decimal(str(quantity))
            s = Decimal(str(step_size))

            if q.is_nan() or s.is_nan():
                return 0.0
        except InvalidOperation:
            return 0.0

        if q <= 0 or s <= 0:
            return 0.0

        normalized = (q / s).to_integral_value(rounding=ROUND_DOWN) * s
        return float(normalized) if normalized > 0 else 0.0
