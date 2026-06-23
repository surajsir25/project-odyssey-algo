# Phase 1 - Quick Start Guide

## Prerequisites

✅ Docker & Docker Compose installed
✅ Upstox API credentials (get from https://dashboard.upstox.com)

## 1. Setup

```bash
cd phase1

# Copy environment template and configure
cp .env.example .env

# Edit .env and add your Upstox credentials
nano .env  # or use your editor
```

Required values in `.env`:
```
UPSTOX_API_KEY=your_api_key
UPSTOX_ACCESS_TOKEN=your_access_token
```

## 2. Start the System

```bash
# Make startup script executable
chmod +x start.sh

# Start all services
./start.sh
```

Or manually:
```bash
docker compose up -d
```

## 3. Verify It's Running

```bash
# Check services status
docker compose ps

# Health check
curl http://localhost:8000/health
# Expected: {"status":"UP"}

# Get ATM information
curl http://localhost:8000/atm
# Expected: {"spot": 25123.50, "strike": 25100, "ce": "...", "pe": "..."}

# View logs
docker compose logs -f app
```

## 4. API Endpoints

Access API documentation at: **http://localhost:8000/docs**

Key endpoints:
- `GET /health` - System health check
- `GET /atm` - Current ATM information
- `GET /candles/latest` - Latest 1-minute candles
- `GET /instruments/{symbol}` - Get all instruments for symbol

## 5. Database Access

```bash
# Connect to PostgreSQL
docker exec -it odyssey_postgres psql -U postgres -d odyssey_trading

# Example queries:
# Get NIFTY instruments:
SELECT * FROM instrument_master WHERE symbol = 'NIFTY' LIMIT 5;

# Get latest candles:
SELECT * FROM candles_1m ORDER BY timestamp DESC LIMIT 10;

# Count ticks:
SELECT COUNT(*) FROM ticks;
```

## 6. Monitoring

```bash
# Stream application logs
docker compose logs -f app

# Stream database logs  
docker compose logs -f postgres

# Check system resources
docker stats
```

## 7. Stop the System

```bash
# Stop all services
./stop.sh

# Or manually:
docker compose down
```

## Troubleshooting

### WebSocket not connecting?
1. Verify token in `.env`: `echo $UPSTOX_ACCESS_TOKEN`
2. Check app logs: `docker compose logs app`
3. Ensure network connectivity

### Database connection error?
1. Verify PostgreSQL is running: `docker compose ps postgres`
2. Check credentials in `.env`
3. Review postgres logs: `docker compose logs postgres`

### Port 8000 already in use?
```bash
# Find what's using port 8000
lsof -i :8000

# Or change port in docker-compose.yml:
# ports:
#   - "8001:8000"  # Use 8001 instead
```

### Need to rebuild?
```bash
# Clean rebuild
docker compose down -v
docker compose build --no-cache
docker compose up -d
```

## Next Steps

✅ System is ready for:
- Real-time tick streaming
- 1-minute candle generation
- ATM strike monitoring
- Data persistence in TimescaleDB

📊 Data is being stored in PostgreSQL/TimescaleDB:
- Raw ticks in `ticks` table
- 1-minute candles in `candles_1m` (optimized hypertable)
- Instrument metadata in `instrument_master`

🚀 Ready for Phase 2:
- Trade execution
- Risk management
- Strategy implementation
- Trade journal

---

For detailed documentation, see `README.md`
