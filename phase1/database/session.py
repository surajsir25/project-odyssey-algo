"""Database connection and session management."""

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from typing import AsyncGenerator

from config.settings import settings


# Create async engine
engine = create_async_engine(
    settings.database.async_database_url,
    echo=settings.database.echo,
    pool_size=20,
    max_overflow=40,
    pool_pre_ping=True,  # Verify connections before using
)

# Session factory
async_session_factory = sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Dependency injection for async session."""
    async with async_session_factory() as session:
        try:
            yield session
        finally:
            await session.close()


async def init_db() -> None:
    """Initialize database tables and TimescaleDB hypertable."""
    from .models import Base
    
    async with engine.begin() as conn:
        # Create all tables
        await conn.run_sync(Base.metadata.create_all)
        
        # Enable TimescaleDB extension and convert candles_1m to hypertable
        await conn.execute("CREATE EXTENSION IF NOT EXISTS timescaledb;")
        
        # Check if hypertable exists before creating
        result = await conn.execute(
            "SELECT EXISTS (SELECT 1 FROM timescaledb_information.hypertables WHERE hypertable_name='candles_1m');"
        )
        is_hypertable = result.scalar()
        
        if not is_hypertable:
            await conn.execute(
                "SELECT create_hypertable('candles_1m', 'timestamp', if_not_exists => TRUE);"
            )


async def close_db() -> None:
    """Close database connections."""
    await engine.dispose()
