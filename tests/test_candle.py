"""Tests for candle extraction."""

from odyssey_algo.candle import extract_candles_from_feed, normalize_interval


def test_normalize_interval_aliases() -> None:
    assert normalize_interval("I1") == "1min"
    assert normalize_interval("i5") == "5min"
    assert normalize_interval("unknown") is None


def test_extract_candles_from_index_feed(sample_index_feed: dict) -> None:
    instrument = "NSE_INDEX|Nifty 50"
    candles = extract_candles_from_feed(instrument, sample_index_feed)

    assert set(candles.keys()) == {"1min", "5min"}
    assert candles["1min"]["instrument"] == instrument
    assert candles["1min"]["candle_timestamp"] == 1710000000
    assert candles["5min"]["close"] == 101.0
    assert "timestamp" in candles["1min"]


def test_extract_ignores_unknown_intervals() -> None:
    feed = {
        "fullFeed": {
            "equityFF": {
                "marketOHLC": {
                    "ohlc": [
                        {
                            "interval": "I30",
                            "ts": 1,
                            "open": 1,
                            "high": 1,
                            "low": 1,
                            "close": 1,
                        }
                    ]
                }
            }
        }
    }
    assert extract_candles_from_feed("NSE_EQ|INE020B01018", feed) == {}
