# Odyssey Algo — Upstox Market Data Streamer

Production-oriented Python package that streams real-time market data from Upstox, extracts 1-minute and 5-minute OHLC candles, and persists them to CSV.

## Project structure

```
project-odyssey-algo/
├── .env.example          # Environment variable template
├── pyproject.toml        # Package metadata and tooling
├── requirements.txt
├── setup.sh
├── src/odyssey_algo/     # Application package
│   ├── cli.py            # Entry point
│   ├── settings.py       # Env-based configuration
│   ├── instruments.py    # Subscribed instruments
│   ├── handler.py        # WebSocket stream handler
│   ├── candle.py         # OHLC extraction
│   ├── storage.py        # Append-only CSV storage
│   └── logging_setup.py
├── scripts/
│   └── debug_streamer.py # Inspect raw WebSocket payloads
├── examples/
│   └── basic_usage.py
└── tests/
```

## Quick start

### 1. Setup

```bash
bash setup.sh
```

Or manually:

```bash
python3 -m venv venv
source venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
```

### 2. Configure credentials

Edit `.env` (never commit this file):

```bash
UPSTOX_ACCESS_TOKEN=your_token_here
```

Get a token from the [Upstox Developer Console](https://dashboard.upstox.com).

### 3. Customize instruments

Edit `src/odyssey_algo/instruments.py` to add or remove indexes and stocks.

### 4. Run the streamer

```bash
odyssey-stream
# or
python -m odyssey_algo.cli
```

Press `Ctrl+C` to stop gracefully.

## Configuration

All settings are loaded from environment variables (see `.env.example`):

| Variable | Default | Description |
|----------|---------|-------------|
| `UPSTOX_ACCESS_TOKEN` | — | **Required.** API access token |
| `UPSTOX_STREAM_MODE` | `full` | `full`, `ltpc`, `full_d30`, `option_greeks` |
| `UPSTOX_AUTO_RECONNECT` | `true` | Enable WebSocket auto-reconnect |
| `UPSTOX_RECONNECT_INTERVAL` | `5` | Seconds between reconnect attempts |
| `UPSTOX_MAX_RETRIES` | `10` | Max reconnect attempts |
| `ODYSSEY_OUTPUT_DIR` | `data` | CSV output directory |
| `ODYSSEY_CSV_ENABLED` | `true` | Persist candles to CSV |
| `ODYSSEY_LOG_LEVEL` | `INFO` | Logging level |
| `ODYSSEY_LOG_FILE` | `logs/upstox_streamer.log` | Log file path |

## Data output

Candles are written to `{ODYSSEY_OUTPUT_DIR}/` as append-only CSV files:

```
data/
├── NSE_INDEX_Nifty 50_1min.csv
├── NSE_INDEX_Nifty 50_5min.csv
├── NSE_EQ_INE020B01018_1min.csv
└── ...
```

Each row includes: `timestamp`, `candle_timestamp`, `instrument`, OHLC, `volume`, `oi`.

Restarting the streamer does **not** truncate existing files; duplicate candles are skipped using the last `candle_timestamp`.

## Development

```bash
source venv/bin/activate
pytest
ruff check src tests
python scripts/debug_streamer.py
```

## Troubleshooting

- **Token error** — Set `UPSTOX_ACCESS_TOKEN` in `.env`.
- **No data** — Markets must be open (9:15 AM–3:30 PM IST, Mon–Fri).
- **Connection failed** — Verify token validity and network access.

## License

MIT
