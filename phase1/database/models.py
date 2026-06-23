"""SQLAlchemy database models."""

from datetime import datetime
from decimal import Decimal
from sqlalchemy import (
    Column,
    BigInteger,
    String,
    Numeric,
    DateTime,
    Date,
    Index,
    UniqueConstraint,
)
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class InstrumentMaster(Base):
    """Instrument master data from Upstox."""

    __tablename__ = "instrument_master"

    instrument_key = Column(String(255), primary_key=True)
    symbol = Column(String(255), nullable=False)
    expiry = Column(Date, nullable=False)
    strike = Column(Numeric(10, 2), nullable=False)
    option_type = Column(String(10), nullable=True)  # CE, PE
    exchange = Column(String(50), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index("ix_instrument_symbol_expiry", "symbol", "expiry"),
        Index("ix_instrument_strike", "strike"),
    )

    def __repr__(self) -> str:
        return f"<InstrumentMaster(key={self.instrument_key}, symbol={self.symbol}, strike={self.strike})>"


class Tick(Base):
    """Raw tick data from WebSocket."""

    __tablename__ = "ticks"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, nullable=False, index=True)
    instrument_key = Column(String(255), nullable=False, index=True)
    ltp = Column(Numeric(10, 2), nullable=False)
    volume = Column(Numeric(15, 0), nullable=False, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("ix_tick_timestamp_instrument", "timestamp", "instrument_key"),
    )

    def __repr__(self) -> str:
        return f"<Tick(timestamp={self.timestamp}, instrument={self.instrument_key}, ltp={self.ltp})>"


class Candle1M(Base):
    """1-minute OHLCV candles."""

    __tablename__ = "candles_1m"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, nullable=False, index=True)
    instrument_key = Column(String(255), nullable=False, index=True)
    open = Column(Numeric(10, 2), nullable=False)
    high = Column(Numeric(10, 2), nullable=False)
    low = Column(Numeric(10, 2), nullable=False)
    close = Column(Numeric(10, 2), nullable=False)
    volume = Column(Numeric(15, 0), nullable=False, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("timestamp", "instrument_key", name="uq_candle_timestamp_instrument"),
        Index("ix_candle_timestamp_instrument", "timestamp", "instrument_key"),
    )

    def __repr__(self) -> str:
        return f"<Candle1M(timestamp={self.timestamp}, instrument={self.instrument_key}, close={self.close})>"


class ATMStatus(Base):
    """Track current ATM status for monitoring."""

    __tablename__ = "atm_status"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, nullable=False, index=True)
    spot_price = Column(Numeric(10, 2), nullable=False)
    atm_strike = Column(Numeric(10, 2), nullable=False)
    ce_instrument_key = Column(String(255), nullable=False)
    pe_instrument_key = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("ix_atm_timestamp", "timestamp"),
    )

    def __repr__(self) -> str:
        return f"<ATMStatus(timestamp={self.timestamp}, spot={self.spot_price}, atm={self.atm_strike})>"
