"""Tick processor for handling incoming tick data."""

from datetime import datetime
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from database.models import Tick
from broker.websocket_client import TickData


class TickProcessor:
    """Process and store tick data."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize tick processor.
        
        Args:
            session: AsyncSession for database operations
        """
        self.session = session
        self.tick_count = 0

    async def process_tick(self, tick: TickData) -> None:
        """Process incoming tick and store in database.
        
        Args:
            tick: TickData object
        """
        try:
            # Create database record
            db_tick = Tick(
                timestamp=tick.timestamp,
                instrument_key=tick.instrument_key,
                ltp=tick.ltp,
                volume=Decimal(tick.volume),
            )
            
            self.session.add(db_tick)
            await self.session.commit()
            
            self.tick_count += 1
            
            # Log every 100 ticks
            if self.tick_count % 100 == 0:
                logger.info(
                    f"Processed {self.tick_count} ticks | Latest: {tick.instrument_key} @ {tick.ltp}"
                )
                
        except Exception as e:
            logger.error(f"Failed to process tick: {str(e)}")
            await self.session.rollback()

    async def get_latest_ticks(
        self, instrument_key: str, limit: int = 100
    ) -> list[Tick]:
        """Get latest ticks for an instrument.
        
        Args:
            instrument_key: Instrument key
            limit: Number of ticks to retrieve
            
        Returns:
            List of Tick objects
        """
        from sqlalchemy import select, desc
        
        query = (
            select(Tick)
            .where(Tick.instrument_key == instrument_key)
            .order_by(desc(Tick.timestamp))
            .limit(limit)
        )
        result = await self.session.execute(query)
        return list(reversed(result.scalars().all()))
