"""Entry point: infinite trading loop with graceful shutdown."""

import logging
import signal
import sys

from ogaden.errors import OgadenError
from ogaden.trader import Trader

log = logging.getLogger(__name__)

# Global shutdown flag
_shutdown_requested = False
_trader: Trader | None = None


def _shutdown(signum: int, _frame: object) -> None:
    global _shutdown_requested, _trader
    log.info("Received signal %s — shutting down", signal.Signals(signum).name)
    _shutdown_requested = True
    if _trader is not None:
        _trader.stop()


def main() -> None:
    global _shutdown_requested, _trader

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    signal.signal(signal.SIGTERM, _shutdown)
    signal.signal(signal.SIGINT, _shutdown)

    try:
        _trader = Trader()
        _trader.setup()
        _trader.start()
    except OgadenError:
        log.exception("Failed to initialize trader")
        sys.exit(1)

    try:
        while not _shutdown_requested:
            _trader.execute()
    except KeyboardInterrupt:
        log.info("Received keyboard interrupt")
        _shutdown_requested = True

    if _trader is not None:
        _trader.stop()
    _trader = None
    log.info("Engine stopped")


if __name__ == "__main__":
    main()
