# Ogaden

Advanced cryptocurrency trading bot for Binance spot markets with multiple indicators, strategy modes, and comprehensive backtesting capabilities.

## Highlights

- **Multiple Technical Indicators**: EMA crossover, RSI, Volume analysis, MACD, Bollinger Bands, Stochastic Oscillator
- **Three Strategy Modes**: Conservative, Balanced, and Aggressive with different risk profiles
- **Dynamic Risk Management**: ATR-based stop loss and take profit with 2:1 reward ratio
- **Volume Confirmation**: Volume SMA, Volume Ratio, OBV, and VPT for enhanced signal validation
- **Comprehensive Backtesting**: Test strategies with detailed metrics including win rate, Sharpe ratio, and max drawdown
- **Real-time Dashboard**: Live monitoring with strategy comparison and backtesting interface
- **Sandbox Simulation**: Test strategies safely with simulated fills and 0.1% fee simulation
- **Professional Architecture**: Modular design with separate components for broker, strategy, and execution

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

Install entry points to `~/.local/bin`:

```bash
make install
```

### Docker

```bash
make start
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

### Enhanced example

```bash
python examples/enhanced_example.py
```

Demonstrates all enhanced features including multiple indicators, strategy modes, and backtesting.

### Web Dashboard

```bash
make run-dashboard
```

Starts the dashboard on port **3501** with:
- **Real-time Trading Data**: Position, signals, balances, P&L
- **Live Price Chart**: Chart.js com atualizações em tempo real
- **Clean Interface**: Interface simples e focada
- **Essential Metrics**: Apenas as informações importantes

### Trading Engine

```bash
make run-engine
```

Starts the trading engine (processo separado):
- **Infinite Loop**: Ciclo contínuo de trading
- **Strategy Execution**: Executa as estratégias configuradas
- **State Management**: Compartilha estado via Memcached
- **Graceful Shutdown**: Desligamento controlado

### Docker Stack

```bash
make docker-start    # Build and start all containers
make docker-stop     # Stop everything and remove orphans
make docker-restart  # docker-stop + docker-start
```

O Docker stack inclui:
- **Engine Container**: Processo de trading
- **Dashboard Container**: Dashboard principal com backtesting
- **Simple Dashboard Container**: Dashboard minimalista
- **Metrics Dashboard Container**: Dashboard de métricas avançadas
- **Memcached**: Compartilhamento de estado entre processos

Porta padrão:
- **Dashboard**: `http://localhost:3501`

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Ogaden Trading Bot                       │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────┐    ┌──────────────────┐    ┌─────────┐  │
│  │  Trading    │    │                  │    │         │  │
│  │  Engine     │◄──►│    Memcached     │◄──►│ Dashboard│  │
│  │  (Python)   │    │   (State Mgmt)   │    │   (Web) │  │
│  └─────────────┘    └──────────────────┘    └─────────┘  │
│       │                     │                     │        │
│       └─────────────────────┼─────────────────────┘        │
│                             │                              │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 2 Processos Separados:

1. **Engine** (`make run-engine`): Processo de trading infinito
2. **Dashboard** (`make run-dashboard`): Interface web com visualização em tempo real

### Comunicação:
- **Memcached**: Compartilhamento de estado entre engine e dashboard
- **WebSocket**: Atualizações em tempo real no dashboard

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
- **Requirement**: 3/3 signals must align
- **Volume**: Required for confirmation
- **RSI Thresholds**: 35 (buy) / 65 (sell)
- **Risk Profile**: Low risk, fewer trades

#### Balanced Mode
- **Requirement**: 2/3 signals needed
- **Volume**: Optional confirmation
- **RSI Thresholds**: 40 (buy) / 60 (sell)
- **Risk Profile**: Moderate risk/reward

#### Aggressive Mode
- **Requirement**: Only 1 signal needed
- **Volume**: Optional confirmation
- **RSI Thresholds**: 45 (buy) / 55 (sell)
- **Risk Profile**: Higher risk, more frequent trades

### Risk Management

- **Dynamic Stop Loss**: ATR-based with 2.0 multiplier
- **Take Profit**: 2:1 reward ratio based on ATR
- **Position Sizing**: Respects Binance filters (MIN_NOTIONAL, STEP_SIZE, MIN_QUANTITY)
- **Volume Confirmation**: Optional volume spike validation

## Configuration

Create a `.env` file at the project root:

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

Set `SANDBOX=true` to simulate fills without touching the live order book. All thresholds use the quote asset unit.

## Backtesting

The bot includes a comprehensive backtesting engine that evaluates strategy performance on historical data:

### Metrics Calculated

- **Win Rate**: Percentage of profitable trades
- **Average Profit**: Mean return per trade
- **Total P&L**: Cumulative profit/loss in currency
- **Max Drawdown**: Maximum peak-to-trough decline
- **Sharpe Ratio**: Risk-adjusted return measure
- **Trade Count**: Number of executed trades

### Running Backtests

Via the web dashboard:
1. Click strategy buttons to test individual modes
2. Use "Compare All" to see side-by-side results
3. View detailed metrics and strategy recommendations

Via command line:
```bash
python enhanced_example.py
```

## Project Layout

```
ogaden/          # Python package: engine, analysis, core trading logic, dashboard
│   ├── broker.py     # Order execution and indicator calculation
│   ├── strategy.py   # Trading logic and strategy modes
│   ├── trader.py     # Main trading orchestration
│   ├── backtest.py   # Backtesting engine and analysis
│   ├── dashboard.py  # Web interface and API
│   └── core/         # Core components (errors, loader)
docker/          # Dockerfiles for engine and dashboard containers
make/            # Build and install scripts
tests/           # Test suite
```

## Development

```bash
make setup      # Create .venv and install dependencies (first time only)
make test       # Run all tests
make quality    # Format, lint, and type-check
make install    # Install entry points to ~/.local/bin
```

## License

This project is licensed under the MIT License — see [LICENSE](LICENSE) for details.
