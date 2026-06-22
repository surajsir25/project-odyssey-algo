"""PostgreSQL / TimescaleDB candle persistence."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Protocol

logger = logging.getLogger("odyssey_algo")

UPSERT_CANDLE_SQL = """
INSERT INTO ohlcv_candles (
    instrument_key, interval, candle_time, open, high, low, close, volume, oi
) VALUES (
    %(instrument_key)s, %(interval)s, %(candle_time)s,
    %(open)s, %(high)s, %(low)s, %(close)s, %(volume)s, %(oi)s
)
ON CONFLICT (instrument_key, interval, candle_time) DO UPDATE SET
    open = EXCLUDED.open,
    high = EXCLUDED.high,
    low = EXCLUDED.low,
    close = EXCLUDED.close,
    volume = EXCLUDED.volume,
    oi = EXCLUDED.oi
"""


class CandleStore(Protocol):
    def write_candle(self, instrument_key: str, interval: str, candle: dict) -> bool: ...


class PostgresCandleStore:
    """Persist OHLCV candles to PostgreSQL / TimescaleDB with idempotent upserts."""

    def __init__(self, database_url: str, enabled: bool = True) -> None:
        self.database_url = database_url
        self.enabled = enabled
        self._conn = None
        self._last_candle_timestamp: dict[tuple[str, str], int | str | None] = {}

    def connect(self) -> None:
        if not self.enabled:
            return
        import psycopg

        self._conn = psycopg.connect(self.database_url, autocommit=True)
        self._ensure_schema()
        self._hydrate_last_timestamps()
        logger.info("Connected to PostgreSQL candle store")

    def close(self) -> None:
        if self._conn is not None:
            self._conn.close()
            self._conn = None

    def _ensure_schema(self) -> None:
        assert self._conn is not None
        with self._conn.cursor() as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS ohlcv_candles (
                    instrument_key TEXT NOT NULL,
                    interval TEXT NOT NULL,
                    candle_time TIMESTAMPTZ NOT NULL,
                    open DOUBLE PRECISION NOT NULL,
                    high DOUBLE PRECISION NOT NULL,
                    low DOUBLE PRECISION NOT NULL,
                    close DOUBLE PRECISION NOT NULL,
                    volume BIGINT NOT NULL DEFAULT 0,
                    oi BIGINT NOT NULL DEFAULT 0,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    PRIMARY KEY (instrument_key, interval, candle_time)
                )
                """
            )
            cur.execute(
                """
                DO $$
                BEGIN
                    IF EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'timescaledb') THEN
                        PERFORM create_hypertable(
                            'ohlcv_candles', 'candle_time', if_not_exists => TRUE
                        );
                    END IF;
                EXCEPTION
                    WHEN OTHERS THEN NULL;
                END $$;
                """
            )

    def _hydrate_last_timestamps(self) -> None:
        if self._conn is None:
            return
        with self._conn.cursor() as cur:
            cur.execute(
                """
                SELECT instrument_key, interval, EXTRACT(EPOCH FROM candle_time)::bigint
                FROM ohlcv_candles
                ORDER BY candle_time DESC
                LIMIT 500
                """
            )
            for instrument_key, interval, epoch in cur.fetchall():
                key = (str(instrument_key), str(interval))
                if key not in self._last_candle_timestamp:
                    self._last_candle_timestamp[key] = int(epoch)

    @staticmethod
    def _normalize_candle_time(candle: dict[str, Any]) -> datetime:
        candle_time = candle.get("candle_time")
        if isinstance(candle_time, datetime):
            if candle_time.tzinfo is None:
                return candle_time.replace(tzinfo=timezone.utc)
            return candle_time.astimezone(timezone.utc)

        raw_ts = candle.get("candle_timestamp")
        if raw_ts is None:
            return datetime.now(timezone.utc)
        return datetime.fromtimestamp(int(raw_ts), tz=timezone.utc)

    def write_candle(self, instrument_key: str, interval: str, candle: dict) -> bool:
        if not self.enabled or self._conn is None:
            return False

        current_timestamp = candle.get("candle_timestamp")
        key = (instrument_key, interval)
        if current_timestamp == self._last_candle_timestamp.get(key):
            return False

        params = {
            "instrument_key": instrument_key,
            "interval": interval,
            "candle_time": self._normalize_candle_time(candle),
            "open": float(candle.get("open", 0)),
            "high": float(candle.get("high", 0)),
            "low": float(candle.get("low", 0)),
            "close": float(candle.get("close", 0)),
            "volume": int(candle.get("volume", 0)),
            "oi": int(candle.get("oi", 0)),
        }

        with self._conn.cursor() as cur:
            cur.execute(UPSERT_CANDLE_SQL, params)

        self._last_candle_timestamp[key] = current_timestamp
        logger.info(
            "[DB %s] %s O=%s H=%s L=%s C=%s V=%s",
            interval.upper(),
            instrument_key,
            params["open"],
            params["high"],
            params["low"],
            params["close"],
            params["volume"],
        )
        return True


class CompositeCandleStore:
    """Write candles to multiple backends (PostgreSQL + optional CSV)."""

    def __init__(self, *stores: CandleStore) -> None:
        self.stores = stores

    def write_candle(self, instrument_key: str, interval: str, candle: dict) -> bool:
        wrote = False
        for store in self.stores:
            if store.write_candle(instrument_key, interval, candle):
                wrote = True
        return wrote
