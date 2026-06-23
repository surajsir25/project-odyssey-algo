"""Pydantic response models."""

from pydantic import BaseModel
from typing import Optional


class HealthResponse(BaseModel):
    """Health check response."""
    status: str


class ATMResponse(BaseModel):
    """ATM information response."""
    spot: float
    strike: float
    ce: str
    pe: str


class CandleResponse(BaseModel):
    """Candle data response."""
    instrument_key: str
    timestamp: str
    open: float
    high: float
    low: float
    close: float
    volume: float
