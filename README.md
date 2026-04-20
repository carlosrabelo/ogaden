# Ogaden

Advanced cryptocurrency trading bot for Binance spot markets with multiple indicators, strategy modes, and built-in safety mechanisms.

## Highlights

- EMA crossover, RSI, MACD, Bollinger Bands, Stochastic Oscillator, and volume analysis as coordinated signal sources
- Three strategy modes (conservative, balanced, aggressive) with enforced risk profiles
- ATR-based dynamic stop loss and take profit with 2:1 reward ratio
- Circuit breaker halts trading automatically when drawdown or consecutive loss thresholds are exceeded
- Price-based trailing stop that rises with price and never falls
- Volume SMA, Volume Ratio, OBV, and VPT for enhanced signal validation
- Real-time dashboard via WebSocket with live price chart and trade metrics
- Sandbox simulation with simulated fills and 0.1% fee emulation

## Prerequisites

- **Python 3.12+** — required to run locally; [download](https://www.python.org/downloads/)
- **Docker and Docker Compose** — required for the full stack
- **Binance API key and secret** — spot trading access required

## Installation

### Local

```bash
git clone https://github.com/username/ogaden.git
cd ogaden
make setup
```

### Docker

```bash
make docker-start
```

Builds the engine and dashboard images and starts the full stack with Memcached.

## Usage

### Trading loop

```bash
make run-engine
```

Starts the infinite trading loop locally. The engine fetches candles every 60 seconds, computes indicators, and executes BUY/SELL orders when conditions align.

### One-off analysis

```bash
ogaden-analysis
```

Fetches current candle data and dumps all indicator values without placing any orders.

### Web Dashboard

```bash
make run-dashboard
```

Starts the dashboard on port **3501** with:
- **Real-time Trading Data**: Position, signals, balances, P&L
- **Live Price Chart**: Chart.js with real-time updates
- **Essential Metrics**: Circuit breaker status, drawdown, consecutive losses, trade history

### Docker Stack

```bash
make docker-start    # Build and start all containers
make docker-stop     # Stop everything and remove orphans
make docker-restart  # docker-stop + docker-start
```

The Docker stack includes:
- **Engine Container**: Trading process
- **Dashboard Container**: Web interface with chart and real-time metrics
- **Memcached**: State sharing between processes

Default port:
- **Dashboard**: `http://localhost:3501`

## Architecture

```
+-------------------------------------------------------------+
|                    Ogaden Trading Bot                       |
+-------------------------------------------------------------+
|                                                             |
|  +-------------+    +------------------+    +---------+    |
|  |  Trading    |    |                  |    |         |    |
|  |  Engine     |<-->|    Memcached     |<-->| Dashboard|   |
|  |  (Python)   |    |   (State Mgmt)   |    |   (Web) |   |
|  +-------------+    +------------------+    +---------+    |
|                                                             |
+-------------------------------------------------------------+
```

### 2 Independent Processes

1. **Engine** (`make run-engine`): Infinite trading loop
2. **Dashboard** (`make run-dashboard`): Web interface with real-time visualization

### Communication

- **Memcached**: State sharing between engine and dashboard
- **WebSocket**: Real-time updates in the dashboard

> Trading with real funds carries risk. Test with `SANDBOX=true` and small amounts before going live.

## Trading Strategy

### Technical Indicators

The bot uses a comprehensive set of technical indicators:

1. **Trend Indicators**
   - EMA Crossover (Fast/Slow)
   - EMA Trend Confirmation
   - MACD (Moving Average Convergence Divergence)

2. **Momentum Indicators**
   - RSI (Relative Strength Index)
   - Stochastic Oscillator

3. **Volatility Indicators**
   - Bollinger Bands (with squeeze detection)
   - ATR (Average True Range)

4. **Volume Indicators**
   - Volume SMA
   - Volume Ratio
   - OBV (On-Balance Volume)
   - VPT (Volume Price Trend)

### Strategy Modes

#### Conservative Mode
- **Requirement**: 2 confirmations needed
- **Volume**: Required for confirmation
- **RSI Thresholds**: 35 (buy) / 65 (sell)
- **Risk Profile**: Low risk, fewer trades

#### Balanced Mode
- **Requirement**: 1 confirmation needed
- **Volume**: Optional confirmation
- **RSI Thresholds**: 40 (buy) / 60 (sell)
- **Risk Profile**: Moderate risk/reward

#### Aggressive Mode
- **Requirement**: 1 primary + 1 confirmation signal (RSI or MACD required)
- **Cooldown**: 2 cycles after loss
- **Position size**: 25% of balance (hard cap at 30%)
- **Volume**: Optional confirmation
- **RSI Thresholds**: 45 (buy) / 55 (sell)
- **Risk Profile**: Higher frequency, minimum safety enforced

### Risk Management

- **Dynamic Stop Loss**: ATR-based with configurable multiplier (default 2.0)
- **Take Profit**: 2:1 reward ratio based on ATR
- **Price-Based Trailing Stop**: `TRAILING_STOP_PCT` sets distance below price peak; stop rises with price and never falls
- **Circuit Breaker**: Halts buying when rolling drawdown (last 20 trades) exceeds `MAX_DRAWDOWN_PCT` or consecutive losses exceed `MAX_CONSECUTIVE_LOSSES`; persisted across restarts — requires manual reset in `data/state.json`
- **Cooldown After Loss**: Configurable pause cycles before next buy after a losing trade
- **Min Trade Margin**: Skips trades where expected move (ATR-based) is below fee threshold
- **Position Sizing**: Respects Binance filters (MIN_NOTIONAL, STEP_SIZE, MIN_QUANTITY)

## Configuration

Create a `.env` file at the project root:

```
# Live credentials (required when SANDBOX=false)
API_KEY=your_key_here
API_SECRET=your_secret_here

# SANDBOX=true by default — set to false only for live trading
SANDBOX=true

BASE_ASSET=BTC
QUOTE_ASSET=USDT
INTERVAL=15m
LIMIT=500
TIMEZONE=America/Cuiaba

# Strategy mode: conservative | balanced | aggressive
STRATEGY_MODE=balanced

# Circuit breaker (set to 0 to disable)
MAX_DRAWDOWN_PCT=15.0
MAX_CONSECUTIVE_LOSSES=5

# Price-based trailing stop (0 = disabled)
TRAILING_STOP_PCT=0.0

MEMCACHED_HOST=localhost
MEMCACHED_PORT=11211

# Sandbox-only initial balances
BASE_BALANCE=0.0
QUOTE_BALANCE=10.0
```

See `.env.example` for the full parameter reference including all risk management overrides.

## Project Layout

```
ogaden/
├── trader.py       # Trading orchestration and cycle loop
├── strategy.py     # Strategy modes and indicator-based decisions
├── broker.py       # Order execution and Binance integration
├── indicators.py   # Technical indicator calculations
├── exchange.py     # Exchange protocol abstraction
├── loader.py       # Configuration from environment variables
├── persistence.py  # Atomic state save/restore (data/state.json)
├── dashboard.py    # Flask + WebSocket dashboard server
├── engine.py       # Entry point for the trading loop
├── errors.py       # Custom exception types
├── retry.py        # Exponential backoff decorator
└── rate_limiter.py # API call throttling
docker/             # Dockerfiles for engine and dashboard
tests/              # Test suite (~2.6k lines)
```

## Development

```bash
make setup      # Create .venv and install dependencies (first time only)
make test       # Run all tests
make quality    # Format, lint, and type-check
```

## License

This project is licensed under the MIT License — see [LICENSE](LICENSE) for details.
