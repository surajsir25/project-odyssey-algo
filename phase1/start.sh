#!/bin/bash

# Startup script for Phase 1 Trading System

set -e

echo "=========================================="
echo "Odyssey Trading System - Phase 1"
echo "=========================================="
echo ""

# Check if .env exists
if [ ! -f .env ]; then
    echo "[ERROR] .env file not found!"
    echo "Please create .env from .env.example"
    echo "  cp .env.example .env"
    exit 1
fi

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "[ERROR] Docker is not running!"
    echo "Please start Docker and try again."
    exit 1
fi

echo "[1/4] Verifying .env configuration..."
source .env

if [ -z "$UPSTOX_ACCESS_TOKEN" ]; then
    echo "[ERROR] UPSTOX_ACCESS_TOKEN not set in .env"
    exit 1
fi

echo "✓ UPSTOX_ACCESS_TOKEN configured"
echo "✓ PostgreSQL Host: ${POSTGRES_HOST:-postgres}"
echo "✓ PostgreSQL DB: ${POSTGRES_DB:-odyssey_trading}"
echo ""

echo "[2/4] Pulling Docker images..."
docker compose pull

echo ""
echo "[3/4] Building Docker images..."
docker compose build

echo ""
echo "[4/4] Starting services..."
docker compose up -d

echo ""
echo "=========================================="
echo "✓ Services started!"
echo "=========================================="
echo ""
echo "API Server:     http://localhost:8000"
echo "Health Check:   http://localhost:8000/health"
echo "API Docs:       http://localhost:8000/docs"
echo ""
echo "Logs:"
echo "  docker compose logs -f app"
echo ""
echo "To stop:"
echo "  docker compose down"
echo ""
