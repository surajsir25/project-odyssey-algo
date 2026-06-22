"""Upstox WebSocket market data handler."""

from __future__ import annotations

import json
import logging
from collections.abc import Callable
from typing import Any

from upstox_client import ApiClient, Configuration, MarketDataStreamerV3

from odyssey_algo.candle import extract_candles_from_feed
from odyssey_algo.settings import Settings
from odyssey_algo.storage import CsvCandleStore

FeedCallback = Callable[[str, dict[str, Any]], None]


class UpstoxMarketDataHandler:
    """Connects to Upstox, processes feeds, and persists candle data."""

    def __init__(
        self,
        settings: Settings,
        store: CsvCandleStore | None = None,
        on_feed: FeedCallback | None = None,
    ) -> None:
        self.settings = settings
        self.logger = logging.getLogger("odyssey_algo")
        self.store = store or CsvCandleStore(
            output_dir=settings.output_dir,
            enabled=settings.csv_enabled,
        )
        self.on_feed = on_feed

        configuration = Configuration()
        configuration.access_token = settings.access_token
        self.api_client = ApiClient(configuration)
        self.streamer: MarketDataStreamerV3 | None = None
        self._subscribed_instruments: list[str] = []
        self._stream_mode: str | None = None

    def initialize_streamer(self, instruments: list[str], mode: str | None = None) -> None:
        stream_mode = mode or self.settings.mode
        self._subscribed_instruments = list(instruments)
        self._stream_mode = stream_mode
        self.logger.info(
            "Initializing streamer with %s instruments in '%s' mode",
            len(instruments),
            stream_mode,
        )

        self.streamer = MarketDataStreamerV3(
            api_client=self.api_client,
            instrumentKeys=instruments,
            mode=stream_mode,
        )
        self._setup_event_handlers()
        self.logger.info("Streamer initialized successfully")

    def _setup_event_handlers(self) -> None:
        if self.streamer is None:
            raise RuntimeError("Streamer is not initialized")

        self.streamer.on("open", self._on_open)
        self.streamer.on("message", self._on_message)
        self.streamer.on("close", self._on_close)
        self.streamer.on("error", self._on_error)
        self.streamer.on("reconnecting", self._on_reconnecting)

    def _on_open(self) -> None:
        self.logger.info("WebSocket connection established")
        self._resubscribe_all()

    def _on_message(self, message: str | dict[str, Any]) -> None:
        try:
            data = json.loads(message) if isinstance(message, str) else message
            if data.get("type") == "market_info":
                return

            feeds = data.get("feeds", {})
            for instrument_key, feed_data in feeds.items():
                if self.on_feed is not None:
                    self.on_feed(instrument_key, feed_data)
                    continue

                candles_by_interval = extract_candles_from_feed(instrument_key, feed_data)
                for interval, candle_data in candles_by_interval.items():
                    if self.store.write_candle(instrument_key, interval, candle_data):
                        ohlc = (
                            f"{candle_data.get('open', 'N/A')}/"
                            f"{candle_data.get('high', 'N/A')}/"
                            f"{candle_data.get('low', 'N/A')}/"
                            f"{candle_data.get('close', 'N/A')}"
                        )
                        self.logger.info(
                            "[NEW %s] [%s] OHLC: %s | Vol: %s",
                            interval.upper(),
                            instrument_key,
                            ohlc,
                            candle_data.get("volume", "N/A"),
                        )
        except json.JSONDecodeError:
            self.logger.exception("Failed to decode WebSocket message as JSON")
        except Exception:
            self.logger.exception("Error processing market data message")

    def _on_close(self) -> None:
        self.logger.info("WebSocket connection closed")

    def _on_error(self, error: Any) -> None:
        self.logger.error("WebSocket error: %s", error)

    def _on_reconnecting(self) -> None:
        self.logger.warning("Attempting to reconnect...")

    def _resubscribe_all(self) -> None:
        if not self.streamer or not self._subscribed_instruments:
            return
        mode = self._stream_mode or self.settings.mode
        self.streamer.subscribe(self._subscribed_instruments, mode)
        self.logger.info(
            "Re-subscribed to %s instruments in '%s' mode",
            len(self._subscribed_instruments),
            mode,
        )

    def set_subscriptions(self, instruments: list[str], mode: str | None = None) -> None:
        """Replace the tracked subscription list (used after ATM roll)."""
        self._subscribed_instruments = list(instruments)
        if mode is not None:
            self._stream_mode = mode

    def subscribe_instruments(self, instruments: list[str], mode: str | None = None) -> None:
        if not self.streamer:
            self.logger.error("Streamer not initialized")
            return

        stream_mode = mode or self._stream_mode or self.settings.mode
        self.streamer.subscribe(instruments, stream_mode)
        for key in instruments:
            if key not in self._subscribed_instruments:
                self._subscribed_instruments.append(key)
        self.logger.info("Subscribed to: %s", instruments)

    def unsubscribe_instruments(self, instruments: list[str]) -> None:
        if not self.streamer:
            self.logger.error("Streamer not initialized")
            return

        self.streamer.unsubscribe(instruments)
        self._subscribed_instruments = [
            key for key in self._subscribed_instruments if key not in instruments
        ]
        self.logger.info("Unsubscribed from: %s", instruments)

    def connect(self) -> None:
        if not self.streamer:
            raise RuntimeError("Streamer not initialized")

        self.logger.info("Establishing WebSocket connection...")
        self.streamer.connect()

    def disconnect(self) -> None:
        if not self.streamer:
            return

        self.logger.info("Disconnecting...")
        self.streamer.disconnect()

    def enable_auto_reconnect(
        self,
        enabled: bool | None = None,
        interval: int | None = None,
        retry_count: int | None = None,
    ) -> None:
        if not self.streamer:
            self.logger.error("Streamer not initialized")
            return

        enabled = self.settings.auto_reconnect if enabled is None else enabled
        interval = self.settings.reconnect_interval if interval is None else interval
        retry_count = self.settings.max_retries if retry_count is None else retry_count

        self.streamer.auto_reconnect(enabled, interval, retry_count)
        self.logger.info(
            "Auto-reconnect: enabled=%s, interval=%ss, retries=%s",
            enabled,
            interval,
            retry_count,
        )
