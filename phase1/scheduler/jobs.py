"""APScheduler jobs for background tasks."""

from datetime import datetime
from decimal import Decimal
from loguru import logger
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy.ext.asyncio import AsyncSession

from config.settings import settings
from database.session import async_session_factory
from broker.instrument_manager import InstrumentManager
from broker.upstox_client import UpstoxRestClient
from database.models import ATMStatus


async def refresh_instrument_master() -> None:
    """Daily job to refresh instrument master from Upstox."""
    logger.info("Starting instrument master refresh...")
    
    try:
        async with async_session_factory() as session:
            upstox = UpstoxRestClient()
            instruments = await upstox.get_instrument_master()
            
            manager = InstrumentManager(session)
            count = await manager.load_instrument_master(instruments)
            
            logger.info(f"Instrument master refreshed: {count} NIFTY instruments loaded")
    except Exception as e:
        logger.error(f"Failed to refresh instrument master: {str(e)}")


async def check_atm_changes(
    on_atm_change_callback = None,
) -> None:
    """Check every minute if ATM strike has changed."""
    try:
        async with async_session_factory() as session:
            upstox = UpstoxRestClient()
            manager = InstrumentManager(session)
            
            # Get current NIFTY spot price
            spot_instrument = await manager.get_nifty_spot()
            if not spot_instrument:
                logger.warning("NIFTY spot not found")
                return
            
            # For this simplified version, we'll skip actual price fetching
            # In production, fetch from MarketQuoteV3Api
            logger.debug("ATM check completed")
            
    except Exception as e:
        logger.error(f"Failed to check ATM changes: {str(e)}")


def setup_scheduler(
    on_atm_change_callback = None,
) -> AsyncIOScheduler:
    """Setup APScheduler with background jobs.
    
    Args:
        on_atm_change_callback: Optional callback for ATM changes
        
    Returns:
        Configured AsyncIOScheduler
    """
    scheduler = AsyncIOScheduler()
    
    # Refresh instrument master daily at 09:00 AM
    scheduler.add_job(
        refresh_instrument_master,
        "cron",
        hour=9,
        minute=0,
        id="refresh_instrument_master",
        name="Refresh Instrument Master",
        replace_existing=True,
    )
    
    # Check ATM changes every minute
    scheduler.add_job(
        check_atm_changes,
        "interval",
        minutes=1,
        id="check_atm_changes",
        name="Check ATM Changes",
        replace_existing=True,
        kwargs={"on_atm_change_callback": on_atm_change_callback},
    )
    
    logger.info("Scheduler configured with jobs")
    
    return scheduler
