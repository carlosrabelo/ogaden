#!/usr/bin/env ./.venv/bin/python

from flask import Flask, render_template
from flask_socketio import SocketIO
from pymemcache.client import base
from dotenv import load_dotenv
import os
import time
import threading

load_dotenv()

memcached_host = os.getenv("MEMCACHED_HOST", "localhost")
memcached_port = int(os.getenv("MEMCACHED_PORT", 11211))

print(memcached_host, memcached_port)

memcache_client = base.Client(server=(memcached_host, memcached_port), key_prefix="ogaden")

app = Flask(__name__)

socketio = SocketIO(app)


@app.route("/")
def dashboard():
    return render_template("dashboard.html")


def update_dashboard():
    while True:
        data = memcache_client.get_many([
            "update_time",
            "symbol",
            "interval",
            "position",
            "signal",
            "base_balance",
            "quote_balance",
            "base_quote_balance",
            "expected_balance",
            "trailing_balance",
            "current_price",
            "purchase_price",
            "difference_price",
        ])

        dashboard_data = {key: (value.decode() if isinstance(value, bytes) else value) for key, value in data.items()}

        socketio.emit("update", dashboard_data)

        time.sleep(10)


threading.Thread(target=update_dashboard, daemon=True).start()

if __name__ == "__main__":
    port = int(os.getenv("HTTP_PORT", 3502))
    socketio.run(app, host="0.0.0.0", port=port, debug=False, allow_unsafe_werkzeug=True)
