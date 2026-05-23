"""Tests for CSV candle storage."""

from pathlib import Path

from odyssey_algo.storage import CsvCandleStore


def _sample_candle(instrument: str, ts: int) -> dict:
    return {
        "timestamp": "2026-01-01T00:00:00+00:00",
        "candle_timestamp": ts,
        "instrument": instrument,
        "open": 1.0,
        "high": 2.0,
        "low": 0.5,
        "close": 1.5,
        "volume": 100,
        "oi": 0,
    }


def test_write_candle_creates_file(tmp_output_dir: Path) -> None:
    store = CsvCandleStore(tmp_output_dir)
    instrument = "NSE_INDEX|Nifty 50"

    assert store.write_candle(instrument, "5min", _sample_candle(instrument, 100))
    path = store.csv_path(instrument, "5min")
    assert path.exists()
    assert path.read_text(encoding="utf-8").count("\n") == 2  # header + row


def test_write_candle_deduplicates(tmp_output_dir: Path) -> None:
    store = CsvCandleStore(tmp_output_dir)
    instrument = "NSE_EQ|INE020B01018"
    candle = _sample_candle(instrument, 200)

    assert store.write_candle(instrument, "1min", candle) is True
    assert store.write_candle(instrument, "1min", candle) is False

    path = store.csv_path(instrument, "1min")
    assert path.read_text(encoding="utf-8").count("\n") == 2


def test_hydrate_last_timestamp_on_restart(tmp_output_dir: Path) -> None:
    instrument = "NSE_INDEX|Nifty Bank"
    store = CsvCandleStore(tmp_output_dir)
    store.write_candle(instrument, "5min", _sample_candle(instrument, 300))

    restarted = CsvCandleStore(tmp_output_dir)
    assert restarted.write_candle(instrument, "5min", _sample_candle(instrument, 300)) is False
    assert restarted.write_candle(instrument, "5min", _sample_candle(instrument, 301)) is True
