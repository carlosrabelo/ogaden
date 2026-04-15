"""Health check for the engine container.

Returns 0 (healthy) when:
  1. The Loader initializes successfully (config is valid).
  2. Memcached is reachable (engine depends on it).
  3. A Trader can be instantiated (exchange client works).

This is more meaningful than just checking the Loader alone,
as it verifies the full dependency chain.
"""

import sys

from ogaden.loader import Loader
from ogaden.trader import Trader

try:
    loader = Loader()
    # Test memcached connectivity
    trader = Trader()
    trader.memcache.get("health_check")  # Will raise if memcached is down
    print("Engine health check passed")
    sys.exit(0)
except Exception as exc:
    print(f"Engine health check FAILED: {exc}", file=sys.stderr)
    sys.exit(1)
