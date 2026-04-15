"""Exchange protocol — decouples broker logic from the Binance SDK.

Defining an explicit interface here makes it straightforward to add support
for other exchanges (Bybit, Kraken, Coinbase, …) by writing an adapter that
satisfies this Protocol without changing any trading logic.

The Binance ``Client`` satisfies this protocol implicitly at runtime; mypy
verifies structural compatibility at type-check time.
"""

from __future__ import annotations

from typing import Any, Protocol


class ExchangeProtocol(Protocol):
    """Minimal surface of an exchange client used by :class:`~ogaden.broker.Broker`.

    To add support for a new exchange, create a class that implements every
    method below and pass it to ``Broker.__init__`` instead of the Binance
    ``Client``.
    """

    def get_account(self) -> dict[str, Any]:
        """Return account information including asset balances."""
        ...

    def get_symbol_ticker(self, *, symbol: str) -> dict[str, Any]:
        """Return the latest price ticker for *symbol*."""
        ...

    def get_symbol_info(self, symbol: str) -> dict[str, Any]:
        """Return exchange metadata (filters, precision) for *symbol*."""
        ...

    def get_klines(
        self,
        *,
        symbol: str,
        interval: str,
        limit: int,
    ) -> list[list[Any]]:
        """Return OHLCV kline/candlestick data for *symbol*."""
        ...

    def order_market_buy(
        self, *, symbol: str, quantity: float
    ) -> dict[str, Any]:
        """Place a market buy order for *quantity* units of *symbol*."""
        ...

    def order_market_sell(
        self, *, symbol: str, quantity: float
    ) -> dict[str, Any]:
        """Place a market sell order for *quantity* units of *symbol*."""
        ...
