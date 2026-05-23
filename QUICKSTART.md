# Quick Start

## 1. Setup

```bash
bash setup.sh
```

## 2. Add your token

Edit `.env`:

```bash
UPSTOX_ACCESS_TOKEN=your_actual_token_here
```

## 3. Run

```bash
source venv/bin/activate
odyssey-stream
```

Data is saved under `data/` as `*_1min.csv` and `*_5min.csv`.

## Customize instruments

Edit `src/odyssey_algo/instruments.py`.

## Debug raw messages

```bash
python scripts/debug_streamer.py
```
