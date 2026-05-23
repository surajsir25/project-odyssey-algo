#!/bin/bash
# Setup script for Odyssey Algo (Upstox market data streamer)
# Run: bash setup.sh

set -euo pipefail

echo "================================"
echo "Odyssey Algo — Setup"
echo "================================"
echo ""

if [ ! -d "venv" ]; then
    echo "[1/5] Creating virtual environment..."
    python3 -m venv venv
    echo "Virtual environment created"
else
    echo "[1/5] Virtual environment already exists"
fi

echo ""
echo "[2/5] Activating virtual environment..."
# shellcheck disable=SC1091
source venv/bin/activate

echo ""
echo "[3/5] Installing package and dependencies..."
pip install -q -e ".[dev]"

echo ""
echo "[4/5] Configuring environment..."
if [ ! -f ".env" ]; then
    cp .env.example .env
    echo "Created .env from .env.example — add your UPSTOX_ACCESS_TOKEN"
else
    echo ".env already exists"
fi

echo ""
echo "[5/5] Running tests..."
pytest -q

echo ""
echo "================================"
echo "Setup complete"
echo "================================"
echo ""
echo "Next steps:"
echo "1. Edit .env and set UPSTOX_ACCESS_TOKEN"
echo "2. Customize instruments in src/odyssey_algo/instruments.py"
echo "3. Run: odyssey-stream"
echo "   or:  python -m odyssey_algo.cli"
echo ""
