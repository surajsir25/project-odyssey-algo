"""Build 1-minute OHLCV candles from tick streams."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from odyssey_algo.streaming.tick import Tick

IST = ZoneInfo("Asia/Kolkata")


@dataclass
class OhlcvCandle:
    instrument_key: str
    interval: str
    candle_time: datetime
    open: float
    high: float
    low: float
    close: float
    volume: int = 0
    oi: int = 0

    def to_store_dict(self) -> dict:
        return {
            "instrument": self.instrument_key,
            "interval": self.interval,
            "candle_timestamp": int(self.candle_time.timestamp()),
            "candle_time": self.candle_time,
            "open": self.open,
            "high": self.high,
            "low": self.low,
            "close": self.close,
            "volume": self.volume,
            "oi": self.oi,
        }


def _tick_time(tick: Tick, tz: ZoneInfo = IST) -> datetime:
    if tick.timestamp_ms > 0:
        seconds = tick.timestamp_ms / 1000 if tick.timestamp_ms > 10_000_000_000 else tick.timestamp_ms
        return datetime.fromtimestamp(seconds, tz=timezone.utc).astimezone(tz)
    return datetime.now(tz)


def _minute_bucket(at: datetime) -> datetime:
    return at.replace(second=0, microsecond=0)


class MinuteCandleAggregator:
    """Aggregate ticks into rolling 1-minute OHLCV candles."""

    def __init__(self, tz: ZoneInfo = IST) -> None:
        self.tz = tz
        self._active: dict[str, OhlcvCandle] = {}

    def on_tick(self, tick: Tick, oi: int = 0) -> OhlcvCandle | None:
        """Ingest a tick. Returns a completed candle when the minute bucket rolls over."""
        tick_at = _tick_time(tick, self.tz)
        bucket = _minute_bucket(tick_at)
        key = tick.instrument_key
        current = self._active.get(key)

        if current is None:
            self._active[key] = OhlcvCandle(
                instrument_key=key,
                interval="1min",
                candle_time=bucket,
                open=tick.price,
                high=tick.price,
                low=tick.price,
                close=tick.price,
                volume=tick.quantity,
                oi=oi,
            )
            return None

        if bucket == current.candle_time:
            current.high = max(current.high, tick.price)
            current.low = min(current.low, tick.price)
            current.close = tick.price
            current.volume += tick.quantity
            if oi > 0:
                current.oi = oi
            return None

        completed = current
        self._active[key] = OhlcvCandle(
            instrument_key=key,
            interval="1min",
            candle_time=bucket,
            open=tick.price,
            high=tick.price,
            low=tick.price,
            close=tick.price,
            volume=tick.quantity,
            oi=oi,
        )
        return completed

    def flush(self, instrument_key: str | None = None) -> list[OhlcvCandle]:
        """Return and clear active in-progress candles (e.g. at session end)."""
        if instrument_key is not None:
            candle = self._active.pop(instrument_key, None)
            return [candle] if candle else []

        candles = list(self._active.values())
        self._active.clear()
        return candles
