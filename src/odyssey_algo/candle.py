"""Extract OHLC candle data from Upstox feed payloads."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

SUPPORTED_INTERVALS = frozenset({"1min", "5min"})
INTERVAL_ALIASES = {
    "i1": "1min",
    "1min": "1min",
    "i5": "5min",
    "5min": "5min",
}


def normalize_interval(raw_interval: str | None) -> str | None:
    if not raw_interval:
        return None
    return INTERVAL_ALIASES.get(raw_interval.lower())


def _parse_candle(instrument_key: str, candle: dict[str, Any]) -> dict[str, Any] | None:
    interval = normalize_interval(candle.get("interval"))
    if interval not in SUPPORTED_INTERVALS:
        return None

    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "candle_timestamp": candle.get("ts"),
        "instrument": instrument_key,
        "open": candle.get("open"),
        "high": candle.get("high"),
        "low": candle.get("low"),
        "close": candle.get("close"),
        "volume": candle.get("volume", 0),
        "oi": candle.get("oi", 0),
        "_interval": interval,
    }


def _extract_from_ff(
    full_feed_key: str,
    feed_data: dict[str, Any],
    instrument_key: str,
) -> dict[str, dict]:
    candles_by_interval: dict[str, dict] = {}
    full_feed = feed_data.get("fullFeed", {})
    ff_section = full_feed.get(full_feed_key, {})
    if not ff_section:
        return candles_by_interval

    ohlc_data = ff_section.get("marketOHLC", {}).get("ohlc", [])
    for candle in ohlc_data:
        parsed = _parse_candle(instrument_key, candle)
        if parsed is None:
            continue
        interval = parsed.pop("_interval")
        candles_by_interval[interval] = parsed

    return candles_by_interval


def extract_candles_from_feed(instrument_key: str, feed_data: dict[str, Any]) -> dict[str, dict]:
    """Extract 1-min and 5-min candles from index or equity full feeds."""
    candles: dict[str, dict] = {}
    for ff_key in ("indexFF", "equityFF"):
        candles.update(_extract_from_ff(ff_key, feed_data, instrument_key))
    return candles
