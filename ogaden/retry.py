"""Retry decorator with exponential backoff for API calls."""

from __future__ import annotations

import logging
import time
from collections.abc import Callable
from functools import wraps
from typing import ParamSpec, TypeVar

log = logging.getLogger(__name__)

P = ParamSpec("P")
R = TypeVar("R")


def with_retry(
    max_attempts: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 30.0,
    exceptions: tuple[type[Exception], ...] = (Exception,),
) -> Callable[[Callable[P, R]], Callable[P, R]]:
    """Retry a function with exponential backoff on specified exceptions.

    Args:
        max_attempts: Maximum total attempts before re-raising the last error.
        base_delay: Initial delay in seconds between retries.
        max_delay: Upper cap on delay in seconds.
        exceptions: Exception types that trigger a retry; others propagate immediately.

    Example::

        @with_retry(max_attempts=3, base_delay=2.0, exceptions=(FetchError,))
        def fetch_price(symbol: str) -> float:
            ...
    """

    def decorator(func: Callable[P, R]) -> Callable[P, R]:
        @wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            delay = base_delay
            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as exc:
                    if attempt == max_attempts:
                        raise
                    log.warning(
                        "%s attempt %d/%d failed: %s — retrying in %.1fs",
                        func.__qualname__,
                        attempt,
                        max_attempts,
                        exc,
                        delay,
                    )
                    time.sleep(delay)
                    delay = min(delay * 2.0, max_delay)
            raise RuntimeError("unreachable")  # pragma: no cover

        return wrapper

    return decorator
