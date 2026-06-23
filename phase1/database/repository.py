"""Repository pattern for database access."""

from datetime import datetime, date
from decimal import Decimal
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from database.models import InstrumentMaster, Candle1M, ATMStatus, Tick


class BaseRepository:
    """Base repository with common operations."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize repository.
        
        Args:
            session: AsyncSession for database operations
        """
        self.session = session


class CandleRepository(BaseRepository):
    """Repository for candle operations."""

    async def save(self, candle: Candle1M) -> None:
        """Save candle to database.
        
        Args:
            candle: Candle1M object
        """
        self.session.add(candle)
        await self.session.commit()

    async def get_latest(self, instrument_key: str) -> Optional[Candle1M]:
        """Get latest candle for instrument.
        
        Args:
            instrument_key: Instrument key
            
        Returns:
            Latest Candle1M or None
        """
        query = (
            select(Candle1M)
            .where(Candle1M.instrument_key == instrument_key)
            .order_by(desc(Candle1M.timestamp))
            .limit(1)
        )
        result = await self.session.execute(query)
        return result.scalars().first()

    async def get_recent(
        self, instrument_key: str, limit: int = 100
    ) -> List[Candle1M]:
        """Get recent candles.
        
        Args:
            instrument_key: Instrument key
            limit: Number of candles
            
        Returns:
            List of Candle1M objects
        """
        query = (
            select(Candle1M)
            .where(Candle1M.instrument_key == instrument_key)
            .order_by(desc(Candle1M.timestamp))
            .limit(limit)
        )
        result = await self.session.execute(query)
        return list(reversed(result.scalars().all()))


class InstrumentRepository(BaseRepository):
    """Repository for instrument operations."""

    async def get_by_key(self, key: str) -> Optional[InstrumentMaster]:
        """Get instrument by key.
        
        Args:
            key: Instrument key
            
        Returns:
            InstrumentMaster or None
        """
        query = select(InstrumentMaster).where(InstrumentMaster.instrument_key == key)
        result = await self.session.execute(query)
        return result.scalars().first()

    async def get_by_symbol(self, symbol: str) -> List[InstrumentMaster]:
        """Get instruments by symbol.
        
        Args:
            symbol: Trading symbol
            
        Returns:
            List of InstrumentMaster objects
        """
        query = select(InstrumentMaster).where(InstrumentMaster.symbol == symbol)
        result = await self.session.execute(query)
        return result.scalars().all()

    async def save_many(self, instruments: List[InstrumentMaster]) -> None:
        """Save multiple instruments.
        
        Args:
            instruments: List of InstrumentMaster objects
        """
        for instrument in instruments:
            self.session.add(instrument)
        await self.session.commit()


class ATMStatusRepository(BaseRepository):
    """Repository for ATM status tracking."""

    async def save(self, status: ATMStatus) -> None:
        """Save ATM status.
        
        Args:
            status: ATMStatus object
        """
        self.session.add(status)
        await self.session.commit()

    async def get_latest(self) -> Optional[ATMStatus]:
        """Get latest ATM status.
        
        Returns:
            Latest ATMStatus or None
        """
        query = select(ATMStatus).order_by(desc(ATMStatus.timestamp)).limit(1)
        result = await self.session.execute(query)
        return result.scalars().first()
