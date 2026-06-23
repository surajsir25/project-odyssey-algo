"""Tests for candle builder."""

import pytest
from datetime import datetime, timedelta
from decimal import Decimal

from market_data.candle_builder import CandleBuilder
from broker.websocket_client import TickData


@pytest.mark.asyncio
async def test_candle_builder_initialization(test_db_session):
    """Test candle builder initialization."""
    builder = CandleBuilder(test_db_session)
    
    assert builder.incomplete_candles == {}
    assert builder.candle_count == 0


@pytest.mark.asyncio
async def test_create_candle_from_ticks(test_db_session):
    """Test creating candle from ticks."""
    builder = CandleBuilder(test_db_session)
    base_time = datetime(2025, 1, 9, 10, 0, 0)
    
    # Create ticks within same minute
    tick1 = TickData("NSE_EQ|TEST", Decimal("100.00"), 100, base_time)
    tick2 = TickData("NSE_EQ|TEST", Decimal("102.00"), 150, base_time + timedelta(seconds=10))
    tick3 = TickData("NSE_EQ|TEST", Decimal("99.00"), 120, base_time + timedelta(seconds=30))
    tick4 = TickData("NSE_EQ|TEST", Decimal("101.50"), 180, base_time + timedelta(seconds=50))
    
    # Process ticks
    assert builder.on_tick(tick1) is None  # Creates candle
    assert builder.on_tick(tick2) is None  # Updates candle
    assert builder.on_tick(tick3) is None  # Updates candle
    assert builder.on_tick(tick4) is None  # Updates candle
    
    # Verify candle data
    candle = builder.incomplete_candles["NSE_EQ|TEST"]
    assert candle["open"] == Decimal("100.00")
    assert candle["high"] == Decimal("102.00")
    assert candle["low"] == Decimal("99.00")
    assert candle["close"] == Decimal("101.50")
    assert candle["volume"] == Decimal(550)


@pytest.mark.asyncio
async def test_candle_minute_boundary(test_db_session):
    """Test candle completion on minute boundary."""
    builder = CandleBuilder(test_db_session)
    base_time = datetime(2025, 1, 9, 10, 0, 0)
    
    tick1 = TickData("NSE_EQ|TEST", Decimal("100.00"), 100, base_time)
    tick2 = TickData("NSE_EQ|TEST", Decimal("101.00"), 150, base_time + timedelta(minutes=1))
    
    # First tick creates candle
    assert builder.on_tick(tick1) is None
    
    # Second tick after minute boundary completes previous candle
    completed = builder.on_tick(tick2)
    assert completed is not None
    assert completed["open"] == Decimal("100.00")
    assert completed["close"] == Decimal("100.00")
