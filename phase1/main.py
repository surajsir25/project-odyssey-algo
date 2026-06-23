"""Main entry point for trading system."""

import asyncio
import signal
import sys
from contextlib import asynccontextmanager

from loguru import logger
import uvicorn

from config.settings import settings
from api.routes import app
from database import init_db, close_db
from scheduler.jobs import setup_scheduler
from broker.websocket_client import WebSocketClient
from broker.instrument_manager import InstrumentManager
from market_data.tick_processor import TickProcessor
from market_data.candle_builder import CandleBuilder
from database.session import async_session_factory
from database.models import ATMStatus
from database.repository import ATMStatusRepository


# Setup logging
logger.remove()  # Remove default handler
logger.add(
    f"{settings.logging.log_dir}/{settings.logging.log_file}",
    format=settings.logging.format,
    level=settings.logging.level,
    rotation=settings.logging.rotation,
    retention=settings.logging.retention,
)
logger.add(
    sys.stdout,
    format=settings.logging.format,
    level=settings.logging.level,
)

logger.info(f"Starting {settings.app_name} v{settings.version}")


# Global instances
websocket_client: WebSocketClient | None = None
scheduler = None


async def on_tick(tick_data) -> None:
    """Handle incoming tick."""
    async with async_session_factory() as session:
        # Process tick
        tick_processor = TickProcessor(session)
        await tick_processor.process_tick(tick_data)
        
        # Build candle
        candle_builder = CandleBuilder(session)
        completed_candle = candle_builder.on_tick(tick_data)
        
        if completed_candle:
            await candle_builder.save_candle(
                completed_candle,
                tick_data.instrument_key
            )


async def start_websocket() -> None:
    """Start WebSocket connection for market data."""
    global websocket_client
    
    try:
        async with async_session_factory() as session:
            manager = InstrumentManager(session)
            
            # Get NIFTY spot and ATM instruments
            spot = await manager.get_nifty_spot()
            if not spot:
                logger.error("NIFTY spot instrument not found")
                return
            
            # For initial demo, subscribe to NIFTY spot only
            # In production, get ATM CE/PE dynamically
            instruments = [spot.instrument_key]
            
            logger.info(f"Subscribing to instruments: {instruments}")
            
            # Create and configure WebSocket client
            websocket_client = WebSocketClient()
            websocket_client.on_tick(on_tick)
            
            # Connect
            await websocket_client.connect(instruments, mode=settings.market.stream_mode)
            
            logger.info("WebSocket client started successfully")
            
    except Exception as e:
        logger.error(f"Failed to start WebSocket: {str(e)}")


async def main() -> None:
    """Main application entry point."""
    global scheduler
    
    # Initialize database
    await init_db()
    logger.info("Database initialized")
    
    # Setup scheduler
    scheduler = setup_scheduler()
    scheduler.start()
    logger.info("Scheduler started")
    
    # Start WebSocket
    websocket_task = asyncio.create_task(start_websocket())
    
    # Start FastAPI server
    config = uvicorn.Config(
        app,
        host="0.0.0.0",
        port=8000,
        log_level=settings.logging.level.lower(),
    )
    server = uvicorn.Server(config)
    
    # Handle graceful shutdown
    def handle_signal(sig, frame):
        logger.info(f"Received signal {sig}, shutting down...")
        asyncio.create_task(shutdown())
    
    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)
    
    try:
        await server.serve()
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received")
        await shutdown()


async def shutdown() -> None:
    """Graceful shutdown."""
    logger.info("Shutting down...")
    
    if websocket_client:
        await websocket_client.disconnect()
    
    if scheduler and scheduler.running:
        scheduler.shutdown()
    
    await close_db()
    
    logger.info("Shutdown complete")
    sys.exit(0)


if __name__ == "__main__":
    asyncio.run(main())
