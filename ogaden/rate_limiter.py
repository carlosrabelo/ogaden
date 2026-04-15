"""Rate limiter to throttle outbound API calls."""

from __future__ import annotations

import threading
import time


class RateLimiter:
    """Enforces a minimum interval between successive calls (thread-safe).

    Args:
        min_interval: Minimum seconds between calls. Callers that arrive
            sooner than this threshold will block until the interval elapses.

    Example::

        limiter = RateLimiter(min_interval=0.2)

        def fetch_price() -> float:
            limiter.acquire()
            return api.get_ticker(...)
    """

    def __init__(self, min_interval: float = 0.2) -> None:
        self._min_interval = min_interval
        self._last_call: float = 0.0
        self._lock = threading.Lock()

    def acquire(self) -> None:
        """Block until the minimum interval since the last call has elapsed."""
        with self._lock:
            now = time.monotonic()
            wait = self._min_interval - (now - self._last_call)
            if wait > 0:
                time.sleep(wait)
            self._last_call = time.monotonic()
