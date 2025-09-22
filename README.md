# Ogaden

Ogaden is a small trading bot that talks with Binance spot markets, keeps a short dashboard, and stores state in Memcached. The project also ships with a ready dashboard and docker setup so you can look at the signals without leaving the browser.

## Architecture

- **Engine (`src/engine.py`)** spins a `Trader` loop, pulls candles, computes indicators, chooses BUY/SELL/HOLD, and syncs balances.
- **Trader/Broker** layer handles the actual business rules, including EMA/RSI signals, profit-loss guards, and order sizing with Binance filters.
- **Dashboard (`src/dashboard.py`)** uses Flask + Socket.IO to stream the latest metrics out of Memcached.
- **Memcached** keeps the last snapshot so dashboard and other services can read it without talking to Binance again.

```
Binance API  <--->  engine (Trader/Broker)
                           |
                           v
                      Memcached
                           |
                           v
                  dashboard (Flask)
```

## Prerequisites

- Python 3.12 (or compatible) if you plan to run outside Docker.
- Docker and Docker Compose (for full stack).
- Binance API key and secret with spot trading access.

## Environment configuration

Create a `.env` file in the project root. These variables are read by the loader:

```
API_KEY=your_key_here
API_SECRET=your_secret_here
SANDBOX=true
TIMEZONE=America/Cuiaba
BASE_ASSET=BTC
QUOTE_ASSET=USDT
INTERVAL=15m
LIMIT=500
FAST_EMA=7
SLOW_EMA=14
TREND_EMA=50
RSI_PERIOD=14
RSI_BUY_THRESHOLD=40
RSI_SELL_THRESHOLD=60
PROFIT_THRESHOLD=0.0
LOSS_THRESHOLD=0.0
TRAILING_THRESHOLD=0.0
MEMCACHED_HOST=localhost
MEMCACHED_PORT=11211
BASE_BALANCE=0.0
QUOTE_BALANCE=10.0
HTTP_PORT=3502
```

Adjust thresholds and assets to match your strategy. Setting `SANDBOX=true` makes the engine simulate fills without hitting the live order book.

## Local workflow (without Docker)

```
make venv   # create or update .venv with both engine and dashboard deps
make run    # run the infinite trading loop (Ctrl+C to stop)
python src/ogaden.py  # one-off data fetch and indicator dump
```

The `run` target depends on `.venv/bin/python`, so it will bootstrap your virtualenv automatically if needed. Use `make clean` to drop Python bytecode.

## Full stack with Docker Compose

```
make start   # build images and start engine, dashboard, memcached
make stop    # stop everything, remove orphans and volumes
make restart # convenient combo of stop + start
```

Once the stack is up, open `http://localhost:3502` to see the live dashboard. It refreshes every 10 seconds with the newest snapshot from Memcached.

## Dashboard preview

The dashboard lists:

- Update time, symbol, and interval
- Position state and the three signals (EMA, RSI, EMA trend)
- Base/quote balances together with expected and trailing balances
- Current/purchase price and profit delta

## Development tips

- Keep an eye on logs: the engine prints buy/sell/hold decisions and rejection reasons (too small quantity, invalid price, etc.).
- When you touch the logic that depends on Binance filters, make sure `MIN_NOTIONAL`, `MIN_QUANTITY`, and `STEP_SIZE` are available before firing orders.
- This bot runs with a 60-second sleep between loops by default; tweak it in `Trader.execute` if you need a different cadence.

## Safety note

Trading with real funds is risky. Test with `SANDBOX=true`, tiny amounts, or a dedicated sub-account before going live. Nothing here is financial advice.
