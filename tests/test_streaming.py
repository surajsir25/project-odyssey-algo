"""Tests for tick parsing and 1-minute candle aggregation."""

from datetime import datetime
from zoneinfo import ZoneInfo

from odyssey_algo.streaming.aggregator import MinuteCandleAggregator
from odyssey_algo.streaming.atm import round_to_atm_strike
from odyssey_algo.streaming.tick import Tick, extract_tick_from_feed

IST = ZoneInfo("Asia/Kolkata")


def test_round_to_atm_strike() -> None:
    assert round_to_atm_strike(23456.0) == 23450
    assert round_to_atm_strike(23474.0) == 23450
    assert round_to_atm_strike(23476.0) == 23500


def test_extract_tick_from_index_feed() -> None:
    feed = {
        "fullFeed": {
            "indexFF": {
                "ltpc": {
                    "ltp": 23456.5,
                    "ltt": 1710000060000,
                    "ltq": 0,
                }
            }
        }
    }
    tick = extract_tick_from_feed("NSE_INDEX|Nifty 50", feed)
    assert tick is not None
    assert tick.price == 23456.5
    assert tick.instrument_key == "NSE_INDEX|Nifty 50"


def test_extract_tick_from_option_feed() -> None:
    feed = {
        "ff": {
            "marketFF": {
                "ltpc": {
                    "ltp": 125.5,
                    "ltt": 1710000120000,
                    "ltq": 150,
                },
                "oi": 1200000,
            }
        }
    }
    tick = extract_tick_from_feed("NSE_FO|12345", feed)
    assert tick is not None
    assert tick.price == 125.5
    assert tick.quantity == 150


def test_minute_aggregator_builds_candle_on_bucket_roll() -> None:
    aggregator = MinuteCandleAggregator(tz=IST)
    base_ms = int(datetime(2026, 6, 17, 10, 15, 30, tzinfo=IST).timestamp() * 1000)

    tick1 = Tick("NSE_INDEX|Nifty 50", 100.0, 0, base_ms)
    tick2 = Tick("NSE_INDEX|Nifty 50", 101.0, 0, base_ms + 10_000)
    tick3 = Tick("NSE_INDEX|Nifty 50", 99.5, 0, base_ms + 20_000)

    assert aggregator.on_tick(tick1) is None
    assert aggregator.on_tick(tick2) is None
    assert aggregator.on_tick(tick3) is None

    next_minute_ms = int(datetime(2026, 6, 17, 10, 16, 5, tzinfo=IST).timestamp() * 1000)
    tick4 = Tick("NSE_INDEX|Nifty 50", 102.0, 0, next_minute_ms)
    completed = aggregator.on_tick(tick4)

    assert completed is not None
    assert completed.open == 100.0
    assert completed.high == 101.0
    assert completed.low == 99.5
    assert completed.close == 99.5
    assert completed.interval == "1min"


def test_extract_candles_from_option_feed() -> None:
    from odyssey_algo.candle import extract_candles_from_feed

    feed = {
        "fullFeed": {
            "marketFF": {
                "marketOHLC": {
                    "ohlc": [
                        {
                            "interval": "I1",
                            "ts": 1710000000,
                            "open": 120.0,
                            "high": 125.0,
                            "low": 118.0,
                            "close": 123.0,
                            "volume": 5000,
                            "oi": 100000,
                        }
                    ]
                }
            }
        }
    }
    candles = extract_candles_from_feed("NSE_FO|99999", feed)
    assert "1min" in candles
    assert candles["1min"]["close"] == 123.0
