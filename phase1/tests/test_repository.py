"""Tests for database repository."""

import pytest
from datetime import datetime
from decimal import Decimal

from database.models import Candle1M
from database.repository import CandleRepository


@pytest.mark.asyncio
async def test_save_candle(test_db_session):
    """Test saving candle to database."""
    repo = CandleRepository(test_db_session)
    
    candle = Candle1M(
        timestamp=datetime(2025, 1, 9, 10, 0, 0),
        instrument_key="NSE_EQ|TEST",
        open=Decimal("100.00"),
        high=Decimal("102.00"),
        low=Decimal("99.00"),
        close=Decimal("101.50"),
        volume=Decimal(1000),
    )
    
    await repo.save(candle)
    
    # Verify saved
    latest = await repo.get_latest("NSE_EQ|TEST")
    assert latest is not None
    assert latest.close == Decimal("101.50")


@pytest.mark.asyncio
async def test_get_recent_candles(test_db_session):
    """Test fetching recent candles."""
    repo = CandleRepository(test_db_session)
    
    # Add test candles
    for i in range(5):
        candle = Candle1M(
            timestamp=datetime(2025, 1, 9, 10, i, 0),
            instrument_key="NSE_EQ|TEST",
            open=Decimal("100.00"),
            high=Decimal("102.00"),
            low=Decimal("99.00"),
            close=Decimal("101.50"),
            volume=Decimal(1000),
        )
        await repo.save(candle)
    
    # Fetch recent
    candles = await repo.get_recent("NSE_EQ|TEST", limit=3)
    assert len(candles) == 3
