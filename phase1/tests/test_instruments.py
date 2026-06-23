"""Tests for instrument manager."""

import pytest
from datetime import datetime, date
from decimal import Decimal

from broker.instrument_manager import InstrumentManager
from database.models import InstrumentMaster


@pytest.mark.asyncio
async def test_calculate_atm_strike():
    """Test ATM strike calculation."""
    # ATM = round(spot / 50) * 50
    
    # Test case 1: 25123 -> 25100
    assert InstrumentManager.calculate_atm_strike(Decimal("25123")) == Decimal("25100")
    
    # Test case 2: 25100 -> 25100
    assert InstrumentManager.calculate_atm_strike(Decimal("25100")) == Decimal("25100")
    
    # Test case 3: 25149 -> 25150
    assert InstrumentManager.calculate_atm_strike(Decimal("25149")) == Decimal("25150")


@pytest.mark.asyncio
async def test_get_nifty_spot(test_db_session):
    """Test fetching NIFTY spot."""
    manager = InstrumentManager(test_db_session)
    
    # Add test data
    spot = InstrumentMaster(
        instrument_key="NSE_INDEX|Nifty 50",
        symbol="NIFTY",
        expiry=None,
        strike=Decimal("0"),
        option_type=None,
        exchange="NSE",
    )
    test_db_session.add(spot)
    await test_db_session.commit()
    
    # Test fetching
    result = await manager.get_nifty_spot()
    assert result is not None
    assert result.symbol == "NIFTY"


@pytest.mark.asyncio
async def test_load_instrument_master(test_db_session):
    """Test loading instrument master."""
    manager = InstrumentManager(test_db_session)
    
    # Mock instrument data
    instruments = [
        {
            "instrument_key": "NSE_EQ|Nifty25100CE",
            "trading_symbol": "NIFTY",
            "expiry": date(2025, 1, 9),
            "strike": 25100,
            "option_type": "CE",
            "exchange": "NSE",
        },
        {
            "instrument_key": "NSE_EQ|Nifty25100PE",
            "trading_symbol": "NIFTY",
            "expiry": date(2025, 1, 9),
            "strike": 25100,
            "option_type": "PE",
            "exchange": "NSE",
        },
    ]
    
    # Load instruments
    count = await manager.load_instrument_master(instruments)
    assert count == 2
