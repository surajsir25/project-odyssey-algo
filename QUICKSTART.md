# Quick Start

## 1. Setup

```bash
bash setup.sh
```

Requires Python 3.12+.

## 2. Add your token

Edit `.env`:

```bash
UPSTOX_ACCESS_TOKEN=your_actual_token_here
```

## 3. Run paper trading (Phase 1)

```bash
source venv/bin/activate
odyssey-trade
```

Paper mode is the default — no real orders. Trade events are logged to `data/trade_journal.jsonl`.

## 4. Run market data streamer (optional)

```bash
odyssey-stream
```

Data is saved under `data/` as `*_1min.csv` and `*_5min.csv`.

## Going live

Set `ODYSSEY_TRADING_MODE=live` and register `ODYSSEY_ALGO_NAME` with Upstox before placing real orders.

See [PHASE1.md](PHASE1.md) for architecture details.
