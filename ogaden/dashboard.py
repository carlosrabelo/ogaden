"""Entry point: Flask + Socket.IO dashboard server."""

import logging
import os
import threading
import time

from dotenv import load_dotenv
from flask import Flask, render_template
from flask_socketio import SocketIO
from pymemcache.client import base

log = logging.getLogger(__name__)

MEMCACHE_KEYS = [
    "update_time",
    "symbol",
    "interval",
    "position",
    "action",
    "strategy",
    "signal",
    "base_balance",
    "quote_balance",
    "base_quote_balance",
    "expected_balance",
    "trailing_balance",
    "current_price",
    "purchase_price",
    "difference_price",
    "difference_price_p",
    "cycle",
    # Risk management config
    "position_size_pct",
    "atr_stop_mult",
    "trend_filter_ema",
    "cooldown_remaining",
    "min_trade_margin_pct",
    "stop_loss",
    "take_profit",
    "trend_ema_value",
    "price_heartbeat",
    "price_history",
    "cycle_sleep",
]

# Default poll interval: 2 seconds (5x faster than previous 10s).
# Override via DASHBOARD_POLL_INTERVAL env var.
_DEFAULT_POLL_INTERVAL = 2

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

# Connection tracking — only poll Memcached when clients are connected.
_connection_lock = threading.Lock()
_connected_count = 0

# Last broadcast payload — re-sent immediately to newly connected clients.
_last_broadcast: dict = {}


def _increment_connections() -> int:
    global _connected_count
    with _connection_lock:
        _connected_count += 1
        return _connected_count


def _decrement_connections() -> int:
    global _connected_count
    with _connection_lock:
        _connected_count -= 1
        return _connected_count


def _has_clients() -> bool:
    with _connection_lock:
        return _connected_count > 0


@app.route("/")
def dashboard() -> str:
    return render_template("dashboard.html")


@app.route("/health")
def health() -> dict[str, str]:
    return {"status": "healthy", "service": "ogaden-dashboard"}


@socketio.on("connect")
def _on_connect() -> None:
    count = _increment_connections()
    log.info("Client connected (total: %d)", count)
    if _last_broadcast:
        socketio.emit("update", _last_broadcast, namespace="/")


@socketio.on("disconnect")
def _on_disconnect() -> None:
    count = _decrement_connections()
    log.info("Client disconnected (total: %d)", count)


def _poll_memcache(client: base.Client, interval: float) -> None:
    """Poll Memcached and broadcast only when meaningful data changes.

    Polls at *interval* seconds to detect changes quickly, but only emits a
    Socket.IO event when price_heartbeat or action has changed — avoiding
    redundant updates between trading cycles.
    """
    global _last_broadcast
    consecutive_errors = 0
    last_heartbeat: str | None = None
    last_action: str | None = None
    current_interval = interval  # fallback until engine reports cycle_sleep

    while True:
        if not _has_clients():
            time.sleep(1)  # Check again soon without polling Memcached
            continue

        try:
            raw = client.get_many(MEMCACHE_KEYS)
            data = {
                k: v.decode() if isinstance(v, bytes) else v for k, v in raw.items()
            }
            if data:
                # Auto-tune poll interval: cycle_sleep / 4 so we catch changes
                # within a quarter of the engine's sleep window.
                if cs := data.get("cycle_sleep"):
                    current_interval = max(5.0, float(cs) / 4)

                heartbeat = data.get("price_heartbeat")
                action = data.get("action")
                if heartbeat != last_heartbeat or action != last_action:
                    last_heartbeat = heartbeat
                    last_action = action
                    _last_broadcast = data
                    keys = {k for k in data if k != "signal"}
                    log.debug("Broadcasting update (interval=%.0fs): %s", current_interval, keys)
                    socketio.emit("update", data, namespace="/")
            consecutive_errors = 0
        except Exception:
            consecutive_errors += 1
            if consecutive_errors <= 3:
                log.warning("Memcache poll failed (attempt %d)", consecutive_errors)
            elif consecutive_errors == 4:
                log.error(
                    "Memcache unreachable for %d attempts — still polling",
                    consecutive_errors,
                )

        time.sleep(current_interval)


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    load_dotenv()

    host = os.getenv("MEMCACHED_HOST", "localhost")
    port = int(os.getenv("MEMCACHED_PORT", "11211"))
    http_port = int(os.getenv("HTTP_PORT", "3501"))
    poll_interval = float(
        os.getenv("DASHBOARD_POLL_INTERVAL", str(_DEFAULT_POLL_INTERVAL))
    )

    client = base.Client(server=(host, port), key_prefix="ogaden")
    log.info("Memcached: %s:%d", host, port)
    log.info("Poll interval: %.1fs", poll_interval)
    log.info("Dashboard: http://localhost:%d", http_port)

    threading.Thread(
        target=_poll_memcache, args=(client, poll_interval), daemon=True
    ).start()

    socketio.run(
        app, host="0.0.0.0", port=http_port, debug=False, allow_unsafe_werkzeug=True
    )


if __name__ == "__main__":
    main()
