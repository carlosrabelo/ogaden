"""Entry point: one-off data fetch and indicator dump."""

import logging

from ogaden.trader import Trader

log = logging.getLogger(__name__)


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    trader = Trader()
    trader.fetch_data()
    trader.calculate_sma()
    trader.calculate_sma_signal()
    trader.calculate_ema()
    trader.calculate_ema_signal()
    trader.calculate_ema_trend()
    trader.calculate_ema_signal_trend()
    trader.calculate_rsi()
    trader.calculate_rsi_signal()
    log.info("\n%s", trader.data.to_string())


if __name__ == "__main__":
    main()
