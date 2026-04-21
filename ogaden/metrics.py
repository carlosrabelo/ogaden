"""Runtime metrics collected across trading cycles."""

from dataclasses import dataclass, field


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
    price_history: list[list[object]] = field(default_factory=list)

    def record_price(self, timestamp: str, price: float) -> None:
        """Append a price point for chart display (capped at 40 entries)."""
        self.price_history.append([timestamp, round(price, 2)])
        if len(self.price_history) > 40:
            self.price_history = self.price_history[-40:]

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
