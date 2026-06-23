# Phase 1 - Trading System

Production-grade algorithmic trading system for NIFTY options on Upstox, built with Python 3.12.

## Features

✅ **Real-time Market Data**
- WebSocket connection to Upstox MarketDataStreamerV3
- Automatic reconnection with exponential backoff
- Tick-by-tick data processing

✅ **Instrument Management**
- Daily instrument master download from Upstox
- ATM strike calculation (50-point intervals)
- Dynamic ATM CE/PE selection

✅ **Data Processing**
- Real-time tick processing and storage
- 1-minute OHLCV candle generation
- TimescaleDB time-series optimization

✅ **REST API**
- Health check endpoint
- Current ATM information
- Latest candle data query
- Instrument lookup

✅ **Scheduling**
- Daily instrument master refresh (09:00 AM)
- Every-minute ATM change detection
- APScheduler integration

✅ **Production Ready**
- Full async/await support
- Dependency injection pattern
- Repository pattern for data access
- Structured logging with Loguru
- Docker containerization

## Tech Stack

- **Python 3.12** - Core language
- **FastAPI** - REST API framework
- **SQLAlchemy** - ORM
- **PostgreSQL + TimescaleDB** - Time-series database
- **WebSockets** - Real-time data
- **APScheduler** - Background jobs
- **Pydantic** - Data validation
- **Loguru** - Structured logging
- **Docker** - Containerization

## Project Structure

```
phase1/
├── app/                    # Application models
│   └── models.py          # Pydantic response models
├── broker/                 # Upstox integration
│   ├── instrument_manager.py
│   ├── upstox_client.py
│   └── websocket_client.py
├── config/                 # Configuration
│   └── settings.py        # Pydantic settings
├── database/               # Database layer
│   ├── models.py          # SQLAlchemy models
│   ├── session.py         # Connection management
│   └── repository.py      # Repository pattern
├── market_data/            # Market data processing
│   ├── tick_processor.py
│   └── candle_builder.py
├── api/                    # REST API
│   └── routes.py          # FastAPI routes
├── scheduler/              # Background jobs
│   └── jobs.py            # APScheduler jobs
├── tests/                  # Unit tests
├── logs/                   # Log files
├── main.py                 # Application entry point
├── Dockerfile              # Docker image definition
├── docker-compose.yml      # Docker Compose configuration
└── requirements.txt        # Python dependencies
```

## Getting Started

### 1. Prerequisites

- Docker & Docker Compose
- Python 3.12 (for local development)
- Upstox API credentials

### 2. Configuration

```bash
# Copy environment template
cp .env.example .env

# Edit .env with your credentials
nano .env
```

Required environment variables:
```
UPSTOX_API_KEY=your_api_key
UPSTOX_ACCESS_TOKEN=your_access_token
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
POSTGRES_DB=odyssey_trading
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
```

### 3. Start with Docker Compose

```bash
# Build and start services
docker compose up -d

# View logs
docker compose logs -f app

# Stop services
docker compose down
```

### 4. Local Development

```bash
# Create virtual environment
python3.12 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run tests
pytest

# Start application
python main.py
```

## API Endpoints

### Health Check
```bash
GET /health
```
Response: `{"status": "UP"}`

### Current ATM
```bash
GET /atm
```
Response:
```json
{
  "spot": 25123.50,
  "strike": 25100,
  "ce": "NIFTY25100CE",
  "pe": "NIFTY25100PE"
}
```

### Latest Candles
```bash
GET /candles/latest
```
Response:
```json
{
  "NIFTY_SPOT": {
    "instrument_key": "NSE_INDEX|Nifty 50",
    "timestamp": "2025-01-09T10:30:00",
    "open": 25100.0,
    "high": 25150.0,
    "low": 25050.0,
    "close": 25120.0,
    "volume": 150000.0
  },
  "CE": {...},
  "PE": {...}
}
```

### Get Instruments
```bash
GET /instruments/{symbol}
```
Example: `GET /instruments/NIFTY`

## Database

### Tables

**instrument_master** - Instrument metadata from Upstox
```sql
SELECT * FROM instrument_master WHERE symbol = 'NIFTY';
```

**ticks** - Raw tick data
```sql
SELECT * FROM ticks WHERE instrument_key = '...' ORDER BY timestamp DESC LIMIT 100;
```

**candles_1m** - 1-minute OHLCV candles (TimescaleDB hypertable)
```sql
SELECT * FROM candles_1m WHERE instrument_key = '...' AND timestamp > NOW() - INTERVAL '1 day';
```

### Connect to Database

```bash
# From host
psql -h localhost -U postgres -d odyssey_trading

# From Docker container
docker exec -it odyssey_postgres psql -U postgres -d odyssey_trading
```

## Logging

Logs are written to:
- **Console**: Formatted output to stdout
- **File**: `logs/trading_system.log` (rotated at 500 MB)

Log format: `<timestamp> | <level> | <module>:<function>:<line> - <message>`

Configure logging in `config/settings.py`:
```python
LoggingSettings(
    level="INFO",
    rotation="500 MB",
    retention="7 days",
)
```

## Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=.

# Run specific test file
pytest tests/test_candles.py

# Run specific test
pytest tests/test_candles.py::test_candle_builder_initialization
```

## Architecture Highlights

### Async/Await
All I/O operations use async/await for non-blocking execution:
- WebSocket connections
- Database queries
- HTTP requests

### Dependency Injection
FastAPI dependencies for clean, testable code:
```python
@app.get("/health")
async def health_check(session: AsyncSession = Depends(get_session)):
    # session automatically injected and cleaned up
    pass
```

### Repository Pattern
Data access abstraction for easy testing and swapping:
```python
repo = CandleRepository(session)
latest = await repo.get_latest("NSE_EQ|TEST")
```

### Event Callbacks
WebSocket uses event-driven callbacks:
```python
websocket_client.on_tick(on_tick_callback)
```

## Error Handling

### WebSocket Reconnection
- Automatic reconnection on connection loss
- Exponential backoff (configurable)
- Max retry attempts: 10
- Logs reconnection attempts

### Database Errors
- Connection pooling with health checks
- Automatic rollback on failures
- Detailed error logging

### API Errors
- Structured error responses
- HTTP status codes
- Detailed error messages in logs

## Performance Considerations

### TimescaleDB
- Hypertable on `candles_1m` for time-series optimization
- Compression for old data
- Automatic chunking by time

### Connection Pooling
- 20 base connections, up to 60 max
- Connection health checks before use
- Configurable in `database/session.py`

### Caching
- Incomplete candles held in-memory
- ATM status cached in database
- Instrument master refreshed daily

## Monitoring & Debugging

### Health Checks
- FastAPI health endpoint (`/health`)
- Docker health check (30s interval)
- Database connection verification

### Logging
- Application start/stop
- WebSocket connect/disconnect/reconnect
- Tick processing (every 100 ticks)
- Candle generation
- Database operations
- Error stack traces

### Example Queries

```bash
# Check system status
curl http://localhost:8000/health

# Get current ATM
curl http://localhost:8000/atm

# Check logs
docker logs odyssey_trading_app
docker logs odyssey_postgres
```

## Troubleshooting

### WebSocket Connection Failed
1. Verify `UPSTOX_ACCESS_TOKEN` in `.env`
2. Check internet connectivity
3. Ensure token hasn't expired
4. Review logs: `docker logs odyssey_trading_app`

### Database Connection Failed
1. Verify PostgreSQL is running: `docker ps`
2. Check environment variables
3. Verify credentials match in docker-compose.yml
4. Review logs: `docker logs odyssey_postgres`

### No Candles Being Generated
1. Verify ticks are being received (check logs)
2. Check tick timestamps are correct
3. Verify candle builder is running
4. Query ticks table: `SELECT COUNT(*) FROM ticks;`

## Future Enhancements (Phase 2+)

- Trade execution engine
- Risk management system
- Position tracking
- Trade journal (JSONL)
- Strategy framework
- Backtesting capabilities
- Web dashboard
- Alert system

## Support

For issues or questions:
1. Check logs: `docker logs odyssey_trading_app`
2. Review error messages in detail
3. Check database state
4. Verify configuration

## License

Proprietary - Odyssey Trading System
