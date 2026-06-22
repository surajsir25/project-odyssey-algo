"""Orchestrates NIFTY spot + ATM options streaming during market hours."""

from __future__ import annotations

import logging
import signal
import threading
import time
from datetime import datetime, timezone
from typing import Any

from odyssey_algo.handler import UpstoxMarketDataHandler
from odyssey_algo.settings import Settings
from odyssey_algo.storage import CsvCandleStore
from odyssey_algo.streaming.aggregator import MinuteCandleAggregator, OhlcvCandle
from odyssey_algo.streaming.atm import AtmStrikeManager
from odyssey_algo.streaming.settings import StreamingSettings
from odyssey_algo.streaming.store import CompositeCandleStore, PostgresCandleStore
from odyssey_algo.streaming.tick import extract_tick_from_feed
from odyssey_algo.trading.market_hours import (
    is_market_open,
    seconds_until_market_open,
)
from odyssey_algo.trading.nifty_instruments import NiftyOptionsResolver
from odyssey_algo.trading.upstox_rest import UpstoxRestClient

logger = logging.getLogger("odyssey_algo")


def _extract_oi(feed_data: dict[str, Any]) -> int:
    for feed_key in ("fullFeed", "ff"):
        full_feed = feed_data.get(feed_key)
        if not isinstance(full_feed, dict):
            continue
        market_ff = full_feed.get("marketFF")
        if isinstance(market_ff, dict):
            oi = market_ff.get("oi")
            if oi is not None:
                try:
                    return int(float(oi))
                except (TypeError, ValueError):
                    return 0
    return 0


class NiftyStreamingService:
    """Stream NIFTY spot + ATM CE/PE, aggregate ticks to 1-min candles, persist to DB."""

    def __init__(self, settings: StreamingSettings) -> None:
        self.settings = settings
        self._stop_event = threading.Event()
        self._last_spot: float | None = None

        rest_client = UpstoxRestClient(settings.access_token)
        self.resolver = NiftyOptionsResolver(
            rest_client,
            expiry=settings.option_expiry,
        )
        self.atm_manager = AtmStrikeManager(self.resolver)

        stores: list = []
        if settings.db_enabled:
            self.pg_store = PostgresCandleStore(settings.database_url, enabled=True)
            stores.append(self.pg_store)
        else:
            self.pg_store = None

        self.csv_store = CsvCandleStore(
            output_dir=settings.output_dir,
            enabled=settings.csv_enabled,
        )
        if settings.csv_enabled:
            stores.append(self.csv_store)

        self.candle_store = CompositeCandleStore(*stores) if stores else self.csv_store
        self.aggregator = MinuteCandleAggregator()

        handler_settings = Settings(
            access_token=settings.access_token,
            mode=settings.stream_mode,
            auto_reconnect=settings.auto_reconnect,
            reconnect_interval=settings.reconnect_interval,
            max_retries=settings.max_retries,
            output_dir=settings.output_dir,
            csv_enabled=False,
            log_level=settings.log_level,
            log_file=settings.log_file,
        )
        self.handler = UpstoxMarketDataHandler(
            handler_settings,
            store=self.csv_store,
            on_feed=self._on_feed,
        )

    def run(self) -> int:
        self._install_signal_handlers()
        logger.info("NIFTY streaming service starting")

        if self.pg_store is not None:
            self.pg_store.connect()

        try:
            while not self._stop_event.is_set():
                if not is_market_open():
                    wait_sec = seconds_until_market_open()
                    logger.info(
                        "Market closed. Sleeping %ss until next session.",
                        wait_sec,
                    )
                    self._sleep_interruptible(min(wait_sec, 60))
                    continue

                exit_code = self._run_session()
                if exit_code != 0 or self._stop_event.is_set():
                    return exit_code

                if is_market_open():
                    logger.warning("Session ended while market still open; retrying in 5s")
                    self._sleep_interruptible(5)
        finally:
            self._shutdown()

        return 0

    def _run_session(self) -> int:
        pair = self.atm_manager.resolve_pair()
        if pair is None:
            logger.error("Could not resolve ATM CE/PE contracts; retrying in 30s")
            self._sleep_interruptible(30)
            return 0

        instruments = [self.settings.nifty_index_key, pair.ce.instrument_key, pair.pe.instrument_key]
        logger.info(
            "Starting session: spot=%s ATM=%s CE=%s PE=%s",
            self.settings.nifty_index_key,
            pair.strike,
            pair.ce.trading_symbol,
            pair.pe.trading_symbol,
        )

        try:
            self.handler.initialize_streamer(instruments, mode=self.settings.stream_mode)
            self.handler.enable_auto_reconnect()
            self.handler.connect()
        except Exception:
            logger.exception("Failed to start WebSocket session")
            self.handler.disconnect()
            self._sleep_interruptible(10)
            return 0

        try:
            while not self._stop_event.is_set() and is_market_open():
                self._sleep_interruptible(1)
        finally:
            self._flush_all_candles()
            self.handler.disconnect()

        logger.info("Market session ended")
        return 0

    def _on_feed(self, instrument_key: str, feed_data: dict[str, Any]) -> None:
        tick = extract_tick_from_feed(instrument_key, feed_data)
        if tick is None:
            return

        if instrument_key == self.settings.nifty_index_key:
            self._last_spot = tick.price
            if self.settings.atm_roll_enabled and self.atm_manager.should_roll(tick.price):
                self._roll_atm(tick.price)

        oi = _extract_oi(feed_data)
        completed = self.aggregator.on_tick(tick, oi=oi)
        if completed is not None:
            self._persist_candle(completed)

    def _roll_atm(self, spot: float) -> None:
        old_keys = self.atm_manager.instrument_keys()
        pair = self.atm_manager.resolve_pair(spot=spot)
        if pair is None:
            return

        new_keys = [pair.ce.instrument_key, pair.pe.instrument_key]
        if old_keys:
            self.handler.unsubscribe_instruments(old_keys)
        self.handler.subscribe_instruments(new_keys, mode=self.settings.stream_mode)
        self.handler.set_subscriptions(
            [self.settings.nifty_index_key, *new_keys],
            mode=self.settings.stream_mode,
        )
        logger.info("ATM rolled to strike %s at spot %.2f", pair.strike, spot)

    def _persist_candle(self, candle: OhlcvCandle) -> None:
        payload = candle.to_store_dict()
        payload["timestamp"] = datetime.now(timezone.utc).isoformat()
        self.candle_store.write_candle(candle.instrument_key, candle.interval, payload)

    def _flush_all_candles(self) -> None:
        for candle in self.aggregator.flush():
            self._persist_candle(candle)

    def _sleep_interruptible(self, seconds: float) -> None:
        end = time.monotonic() + seconds
        while time.monotonic() < end and not self._stop_event.is_set():
            time.sleep(min(0.5, end - time.monotonic()))

    def _shutdown(self) -> None:
        self._flush_all_candles()
        self.handler.disconnect()
        if self.pg_store is not None:
            self.pg_store.close()
        logger.info("NIFTY streaming service stopped")

    def stop(self) -> None:
        self._stop_event.set()

    def _install_signal_handlers(self) -> None:
        def _handle(signum: int, _frame: object) -> None:
            logger.info("Received signal %s; shutting down", signum)
            self.stop()

        signal.signal(signal.SIGINT, _handle)
        signal.signal(signal.SIGTERM, _handle)
