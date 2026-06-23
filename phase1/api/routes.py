"""FastAPI application and routes."""

from fastapi import FastAPI, HTTPException, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime
from decimal import Decimal
from loguru import logger

from config.settings import settings
from database import get_session, init_db
from database.repository import CandleRepository, ATMStatusRepository
from broker.instrument_manager import InstrumentManager
from app.models import HealthResponse, ATMResponse, CandleResponse


# Create FastAPI app
app = FastAPI(
    title=settings.app_name,
    version=settings.version,
    debug=settings.debug,
)


@app.on_event("startup")
async def startup_event() -> None:
    """Initialize database on startup."""
    logger.info(f"Starting {settings.app_name}")
    await init_db()
    logger.info("Database initialized")


@app.on_event("shutdown")
async def shutdown_event() -> None:
    """Cleanup on shutdown."""
    from database import close_db
    await close_db()
    logger.info("Application shutdown")


@app.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Health check endpoint.
    
    Returns:
        Health status
    """
    return HealthResponse(status="UP")


@app.get("/atm", response_model=ATMResponse)
async def get_atm(session: AsyncSession = Depends(get_session)) -> ATMResponse:
    """Get current ATM information.
    
    Returns:
        Current ATM spot, strike, CE and PE instruments
    """
    try:
        # Get latest ATM status from database
        repo = ATMStatusRepository(session)
        status = await repo.get_latest()
        
        if not status:
            raise HTTPException(status_code=404, detail="ATM status not available")
        
        return ATMResponse(
            spot=float(status.spot_price),
            strike=float(status.atm_strike),
            ce=status.ce_instrument_key,
            pe=status.pe_instrument_key,
        )
    except Exception as e:
        logger.error(f"Error fetching ATM: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/candles/latest")
async def get_latest_candles(
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Get latest candles for all subscribed instruments.
    
    Returns:
        Latest candles for NIFTY spot, CE, and PE
    """
    try:
        repo = CandleRepository(session)
        atm_repo = ATMStatusRepository(session)
        
        # Get current ATM status
        atm_status = await atm_repo.get_latest()
        if not atm_status:
            raise HTTPException(status_code=404, detail="ATM status not available")
        
        # Get latest candles for all three instruments
        instruments = [
            ("NIFTY_SPOT", "NSE_INDEX|Nifty 50"),
            ("CE", atm_status.ce_instrument_key),
            ("PE", atm_status.pe_instrument_key),
        ]
        
        candles = {}
        for candle_type, instrument_key in instruments:
            latest = await repo.get_latest(instrument_key)
            if latest:
                candles[candle_type] = {
                    "instrument_key": latest.instrument_key,
                    "timestamp": latest.timestamp.isoformat(),
                    "open": float(latest.open),
                    "high": float(latest.high),
                    "low": float(latest.low),
                    "close": float(latest.close),
                    "volume": float(latest.volume),
                }
        
        return candles
        
    except Exception as e:
        logger.error(f"Error fetching candles: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/instruments/{symbol}")
async def get_instruments(
    symbol: str,
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Get all instruments for a symbol.
    
    Args:
        symbol: Trading symbol
        
    Returns:
        List of instruments
    """
    try:
        manager = InstrumentManager(session)
        instruments = await manager.get_instruments_by_symbol(symbol)
        
        return {
            "symbol": symbol,
            "count": len(instruments),
            "instruments": [
                {
                    "key": inst.instrument_key,
                    "symbol": inst.symbol,
                    "strike": float(inst.strike) if inst.strike else None,
                    "option_type": inst.option_type,
                    "expiry": inst.expiry.isoformat() if inst.expiry else None,
                }
                for inst in instruments
            ],
        }
    except Exception as e:
        logger.error(f"Error fetching instruments: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
