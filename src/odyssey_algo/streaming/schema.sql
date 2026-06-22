-- TimescaleDB schema for Odyssey Algo OHLCV candles.
-- Applied automatically on first connect, or run manually:
--   psql $ODYSSEY_DATABASE_URL -f src/odyssey_algo/streaming/schema.sql

CREATE EXTENSION IF NOT EXISTS timescaledb;

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
);

SELECT create_hypertable('ohlcv_candles', 'candle_time', if_not_exists => TRUE);

CREATE INDEX IF NOT EXISTS idx_ohlcv_instrument_time
    ON ohlcv_candles (instrument_key, candle_time DESC);
