"""Candle builder for converting ticks into OHLCV candles."""

from datetime import datetime, timedelta
from decimal import Decimal
from typing import Optional, Dict
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from database.models import Tick, Candle1M
from broker.websocket_client import TickData


class CandleBuilder:
    """Build 1-minute candles from ticks."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize candle builder.
        
        Args:
            session: AsyncSession for database operations
        """
        self.session = session
        
        # In-memory buffer for incomplete candles
        # Key: instrument_key, Value: {timestamp, open, high, low, last_close, volume}
        self.incomplete_candles: Dict[str, dict] = {}
        
        self.candle_count = 0

    def on_tick(self, tick: TickData) -> Optional[Dict]:
        """Process tick and potentially generate candle.
        
        Args:
            tick: TickData object
            
        Returns:
            Completed candle dict if one was just completed, else None
        """
        # Get candle timestamp (round down to minute)
        candle_time = self._round_to_minute(tick.timestamp)
        
        if tick.instrument_key not in self.incomplete_candles:
            # New candle
            self.incomplete_candles[tick.instrument_key] = {
                "timestamp": candle_time,
                "open": tick.ltp,
                "high": tick.ltp,
                "low": tick.ltp,
                "close": tick.ltp,
                "volume": Decimal(tick.volume),
            }
        else:
            candle = self.incomplete_candles[tick.instrument_key]
            
            # Check if we've moved to next minute
            if tick.timestamp >= candle["timestamp"] + timedelta(minutes=1):
                # Completed candle - save it
                completed = self.incomplete_candles.pop(tick.instrument_key)
                
                # Start new candle
                self.incomplete_candles[tick.instrument_key] = {
                    "timestamp": candle_time,
                    "open": tick.ltp,
                    "high": tick.ltp,
                    "low": tick.ltp,
                    "close": tick.ltp,
                    "volume": Decimal(tick.volume),
                }
                
                return completed
            else:
                # Update current candle
                candle["high"] = max(candle["high"], tick.ltp)
                candle["low"] = min(candle["low"], tick.ltp)
                candle["close"] = tick.ltp
                candle["volume"] += Decimal(tick.volume)
        
        return None

    async def save_candle(self, candle: dict, instrument_key: str) -> None:
        """Save completed candle to database.
        
        Args:
            candle: Candle dictionary
            instrument_key: Instrument key
        """
        try:
            db_candle = Candle1M(
                timestamp=candle["timestamp"],
                instrument_key=instrument_key,
                open=candle["open"],
                high=candle["high"],
                low=candle["low"],
                close=candle["close"],
                volume=candle["volume"],
            )
            
            self.session.add(db_candle)
            await self.session.commit()
            
            self.candle_count += 1
            
            logger.info(
                f"[CANDLE 1M] {instrument_key} @ {candle['timestamp']} | "
                f"OHLC: {candle['open']}/{candle['high']}/{candle['low']}/{candle['close']} | "
                f"Vol: {candle['volume']}"
            )
            
        except Exception as e:
            logger.error(f"Failed to save candle: {str(e)}")
            await self.session.rollback()

    async def get_latest_candle(self, instrument_key: str) -> Optional[Candle1M]:
        """Get latest candle for instrument.
        
        Args:
            instrument_key: Instrument key
            
        Returns:
            Latest Candle1M or None
        """
        from sqlalchemy import select, desc
        
        query = (
            select(Candle1M)
            .where(Candle1M.instrument_key == instrument_key)
            .order_by(desc(Candle1M.timestamp))
            .limit(1)
        )
        result = await self.session.execute(query)
        return result.scalars().first()

    async def get_candles(
        self, instrument_key: str, limit: int = 100
    ) -> list[Candle1M]:
        """Get recent candles for instrument.
        
        Args:
            instrument_key: Instrument key
            limit: Number of candles to retrieve
            
        Returns:
            List of Candle1M objects
        """
        from sqlalchemy import select, desc
        
        query = (
            select(Candle1M)
            .where(Candle1M.instrument_key == instrument_key)
            .order_by(desc(Candle1M.timestamp))
            .limit(limit)
        )
        result = await self.session.execute(query)
        return list(reversed(result.scalars().all()))

    @staticmethod
    def _round_to_minute(dt: datetime) -> datetime:
        """Round datetime down to minute.
        
        Args:
            dt: Datetime to round
            
        Returns:
            Rounded datetime
        """
        return dt.replace(second=0, microsecond=0)
