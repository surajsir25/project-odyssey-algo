"""Parse real-time ticks from Upstox WebSocket feed payloads."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

FULL_FEED_KEYS = ("fullFeed", "ff")
FF_SECTION_KEYS = ("indexFF", "marketFF", "equityFF")


@dataclass(frozen=True)
class Tick:
    instrument_key: str
    price: float
    quantity: int
    timestamp_ms: int


def _parse_ltpc(instrument_key: str, ltpc: dict[str, Any]) -> Tick | None:
    ltp = ltpc.get("ltp")
    if ltp is None:
        return None
    try:
        price = float(ltp)
    except (TypeError, ValueError):
        return None
    if price <= 0:
        return None

    ltt = ltpc.get("ltt", 0)
    ltq = ltpc.get("ltq", 0)
    try:
        timestamp_ms = int(ltt)
        quantity = int(ltq)
    except (TypeError, ValueError):
        timestamp_ms = 0
        quantity = 0

    return Tick(
        instrument_key=instrument_key,
        price=price,
        quantity=max(quantity, 0),
        timestamp_ms=timestamp_ms,
    )


def extract_tick_from_feed(instrument_key: str, feed_data: dict[str, Any]) -> Tick | None:
    """Extract the latest trade tick from an Upstox feed message."""
    for feed_key in FULL_FEED_KEYS:
        full_feed = feed_data.get(feed_key)
        if not isinstance(full_feed, dict):
            continue
        for section_key in FF_SECTION_KEYS:
            section = full_feed.get(section_key)
            if not isinstance(section, dict):
                continue
            ltpc = section.get("ltpc")
            if isinstance(ltpc, dict):
                tick = _parse_ltpc(instrument_key, ltpc)
                if tick is not None:
                    return tick

    ltpc = feed_data.get("ltpc")
    if isinstance(ltpc, dict):
        return _parse_ltpc(instrument_key, ltpc)

    return None
