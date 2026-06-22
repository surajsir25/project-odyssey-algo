# Odyssey Algo — NIFTY Options Algorithmic Trading

Production-oriented Python 3.12 system for NIFTY options trading on Upstox. Phase 1 delivers a paper/live trading engine with risk controls, instrument resolution, and a reference momentum strategy — built on top of the existing market data streamer.

## Project structure

```
project-odyssey-algo/
├── .env.example
├── pyproject.toml
├── PHASE1.md              # Phase 1 architecture and scope
├── src/odyssey_algo/
│   ├── cli.py             # Market data streamer (odyssey-stream)
│   ├── handler.py         # WebSocket stream handler
│   ├── candle.py          # OHLC extraction
│   ├── storage.py         # CSV persistence
│   └── trading/           # Phase 1 trading engine
│       ├── cli.py         # Trading entry point (odyssey-trade)
│       ├── engine.py      # Orchestrator
│       ├── models.py      # Domain types
│       ├── settings.py    # Trading config
│       ├── upstox_rest.py # REST API wrapper
│       ├── nifty_instruments.py
│       ├── market_data.py
│       ├── market_hours.py
│       ├── journal.py     # JSONL audit log
│       ├── orders/        # Paper + live brokers
│       ├── risk/          # Pre-trade risk checks
│       └── strategy/      # Strategy framework
├── scripts/
└── tests/
```

## Quick start

### 1. Setup

```bash
bash setup.sh
```

Requires **Python 3.12+**.

### 2. Configure credentials

```bash
cp .env.example .env
# Edit .env — set UPSTOX_ACCESS_TOKEN
```

Get a token from the [Upstox Developer Console](https://dashboard.upstox.com).

### 3. Run the trading engine (paper mode)

```bash
odyssey-trade
# or
python -m odyssey_algo.trading.cli
```

Paper mode is the default — orders are simulated at LTP with no real capital at risk.

### 4. Run the market data streamer (optional)

```bash
odyssey-stream
```

## Phase 1 trading engine

| Component | Description |
|-----------|-------------|
| **Paper broker** | Simulates fills at last traded price |
| **Live broker** | Places real orders via Upstox OrderApiV3 with algo name header |
| **NIFTY options resolver** | Finds ATM CE/PE via Instruments API |
| **Risk manager** | Position limits, daily loss cap, kill switch |
| **Trade journal** | Append-only JSONL audit log in `data/trade_journal.jsonl` |
| **Nifty momentum strategy** | Reference strategy: ATM CE on +50pt move, ATM PE on -50pt move |

See [PHASE1.md](PHASE1.md) for full architecture details.

## Configuration

### Trading (Phase 1)

| Variable | Default | Description |
|----------|---------|-------------|
| `ODYSSEY_TRADING_MODE` | `paper` | `paper` or `live` |
| `ODYSSEY_ALGO_NAME` | `odyssey-nifty-v1` | Upstox algo registration name (required for live) |
| `ODYSSEY_UNDERLYING` | `NIFTY` | Underlying symbol |
| `ODYSSEY_OPTION_EXPIRY` | `current_week` | `current_week`, `current_month`, or `yyyy-MM-dd` |
| `ODYSSEY_STRATEGY` | `nifty_momentum` | Active strategy |
| `ODYSSEY_PRODUCT` | `I` | `I` (intraday) or `D` (delivery) |
| `ODYSSEY_POLL_INTERVAL_SEC` | `30` | Quote polling interval |
| `ODYSSEY_MAX_OPEN_POSITIONS` | `2` | Max concurrent positions |
| `ODYSSEY_MAX_DAILY_LOSS_INR` | `5000` | Daily loss circuit breaker |
| `ODYSSEY_MAX_ORDER_LOTS` | `1` | Max lots per order |
| `ODYSSEY_MOMENTUM_THRESHOLD_POINTS` | `50` | NIFTY move threshold for signals |
| `ODYSSEY_KILL_SWITCH` | `false` | Emergency stop — blocks all orders |

### Market data streamer

| Variable | Default | Description |
|----------|---------|-------------|
| `UPSTOX_ACCESS_TOKEN` | — | **Required.** API access token |
| `UPSTOX_STREAM_MODE` | `full` | `full`, `ltpc`, `full_d30`, `option_greeks` |
| `ODYSSEY_OUTPUT_DIR` | `data` | CSV and journal output directory |
| `ODYSSEY_LOG_LEVEL` | `INFO` | Logging level |

## Development

```bash
source venv/bin/activate
pytest
ruff check src tests
```

## Going live

1. Register your algo name with Upstox (`ODYSSEY_ALGO_NAME`)
2. Set `ODYSSEY_TRADING_MODE=live` in `.env`
3. Start with `ODYSSEY_MAX_ORDER_LOTS=1` and tight risk limits
4. Monitor `data/trade_journal.jsonl` and logs

## License

MIT
