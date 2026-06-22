"""Tests for NSE market hours helpers."""

from datetime import datetime

from odyssey_algo.trading.market_hours import IST, is_market_open, is_trading_day


def test_weekday_during_session_is_open() -> None:
    # Wednesday 2026-06-17 10:00 IST
    at = datetime(2026, 6, 17, 10, 0, tzinfo=IST)
    assert is_trading_day(at.date())
    assert is_market_open(at)


def test_weekend_is_closed() -> None:
    at = datetime(2026, 6, 20, 10, 0, tzinfo=IST)  # Saturday
    assert not is_trading_day(at.date())
    assert not is_market_open(at)


def test_after_hours_is_closed() -> None:
    at = datetime(2026, 6, 17, 16, 0, tzinfo=IST)
    assert not is_market_open(at)
