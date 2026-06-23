"""Test configuration and fixtures."""

import pytest
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from database.models import Base


@pytest.fixture
async def test_db_session():
    """Create test database session."""
    # Use in-memory SQLite for testing
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
    )
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    async_session = sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    
    async with async_session() as session:
        yield session
    
    await engine.dispose()


@pytest.fixture
def mock_tick_data():
    """Create mock tick data."""
    from datetime import datetime
    from decimal import Decimal
    from broker.websocket_client import TickData
    
    return TickData(
        instrument_key="NSE_INDEX|Nifty 50",
        ltp=Decimal("25100.50"),
        volume=1500,
        timestamp=datetime.utcnow(),
    )
