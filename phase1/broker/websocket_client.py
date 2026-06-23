"""WebSocket client for streaming market data from Upstox."""

import asyncio
import json
from datetime import datetime
from decimal import Decimal
from typing import Optional, Callable, Any
from loguru import logger
from upstox_client import ApiClient, Configuration, MarketDataStreamerV3

from config.settings import settings


class TickData:
    """Structured tick data from WebSocket."""

    def __init__(self, instrument_key: str, ltp: Decimal, volume: int, timestamp: datetime) -> None:
        self.instrument_key = instrument_key
        self.ltp = ltp
        self.volume = volume
        self.timestamp = timestamp

    def __repr__(self) -> str:
        return f"<Tick({self.instrument_key}, {self.ltp}, {self.timestamp})>"


class WebSocketClient:
    """Async WebSocket client for Upstox market data."""

    def __init__(self) -> None:
        """Initialize WebSocket client."""
        config = Configuration()
        config.access_token = settings.upstox.access_token
        self.api_client = ApiClient(config)
        
        self.streamer: Optional[MarketDataStreamerV3] = None
        self.subscribed_instruments: list[str] = []
        self._connected = False
        self._reconnect_count = 0
        self._on_tick_callback: Optional[Callable[[TickData], None]] = None
        logger.info("WebSocket client initialized")

    def on_tick(self, callback: Callable[[TickData], None]) -> None:
        """Register callback for tick data.
        
        Args:
            callback: Async function to call on each tick
        """
        self._on_tick_callback = callback

    async def connect(self, instruments: list[str], mode: str = "full") -> None:
        """Connect to WebSocket and subscribe to instruments.
        
        Args:
            instruments: List of instrument keys to subscribe
            mode: Stream mode (full, ltpc, ltp, snapshot)
            
        Raises:
            RuntimeError: If connection fails
        """
        try:
            self.streamer = MarketDataStreamerV3(
                api_client=self.api_client,
                instrumentKeys=instruments,
                mode=mode,
            )
            
            self._setup_handlers()
            self.subscribed_instruments = list(instruments)
            
            logger.info(f"Connecting to WebSocket with {len(instruments)} instruments in {mode} mode...")
            self.streamer.connect()
            self._connected = True
            self._reconnect_count = 0
            logger.info("WebSocket connected successfully")
            
        except Exception as e:
            logger.error(f"Failed to connect WebSocket: {str(e)}")
            self._connected = False
            raise RuntimeError(f"WebSocket connection failed: {str(e)}")

    def _setup_handlers(self) -> None:
        """Setup event handlers for WebSocket."""
        if self.streamer is None:
            raise RuntimeError("Streamer not initialized")
        
        self.streamer.on("open", self._on_open)
        self.streamer.on("message", self._on_message)
        self.streamer.on("close", self._on_close)
        self.streamer.on("error", self._on_error)
        self.streamer.on("reconnecting", self._on_reconnecting)

    def _on_open(self) -> None:
        """Handle WebSocket open event."""
        logger.info("WebSocket connection opened")
        self._connected = True

    def _on_message(self, message: Any) -> None:
        """Handle incoming message.
        
        Args:
            message: Incoming WebSocket message
        """
        try:
            # Parse message
            if isinstance(message, str):
                data = json.loads(message)
            else:
                data = message
            
            # Skip market_info messages
            if data.get("type") == "market_info":
                return
            
            # Process feeds
            feeds = data.get("feeds", {})
            for instrument_key, feed_data in feeds.items():
                tick = self._parse_tick(instrument_key, feed_data)
                if tick and self._on_tick_callback:
                    self._on_tick_callback(tick)
                    
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse JSON message: {str(e)}")
        except Exception as e:
            logger.exception(f"Error processing message: {str(e)}")

    @staticmethod
    def _parse_tick(instrument_key: str, feed_data: dict) -> Optional[TickData]:
        """Parse tick data from feed.
        
        Args:
            instrument_key: Instrument key
            feed_data: Feed data dictionary
            
        Returns:
            TickData object or None if parsing fails
        """
        try:
            ltp = Decimal(str(feed_data.get("ltp", 0)))
            volume = int(feed_data.get("volume", 0))
            timestamp = datetime.utcnow()
            
            return TickData(instrument_key, ltp, volume, timestamp)
        except (ValueError, TypeError) as e:
            logger.warning(f"Failed to parse tick for {instrument_key}: {str(e)}")
            return None

    def _on_close(self) -> None:
        """Handle WebSocket close event."""
        logger.warning("WebSocket connection closed")
        self._connected = False

    def _on_error(self, error: Any) -> None:
        """Handle WebSocket error.
        
        Args:
            error: Error object
        """
        logger.error(f"WebSocket error: {str(error)}")
        self._connected = False

    def _on_reconnecting(self) -> None:
        """Handle reconnection attempt."""
        self._reconnect_count += 1
        if self._reconnect_count <= settings.websocket.max_reconnect_attempts:
            logger.warning(f"Attempting to reconnect (attempt {self._reconnect_count}/{settings.websocket.max_reconnect_attempts})")
        else:
            logger.error(f"Max reconnection attempts ({settings.websocket.max_reconnect_attempts}) exceeded")

    async def subscribe(self, instruments: list[str], mode: str = "full") -> None:
        """Subscribe to additional instruments.
        
        Args:
            instruments: List of instrument keys
            mode: Stream mode
        """
        if not self.streamer:
            logger.error("Streamer not initialized")
            return
        
        try:
            self.streamer.subscribe(instruments, mode)
            self.subscribed_instruments.extend(instruments)
            logger.info(f"Subscribed to {len(instruments)} new instruments")
        except Exception as e:
            logger.error(f"Failed to subscribe: {str(e)}")

    async def unsubscribe(self, instruments: list[str]) -> None:
        """Unsubscribe from instruments.
        
        Args:
            instruments: List of instrument keys
        """
        if not self.streamer:
            logger.error("Streamer not initialized")
            return
        
        try:
            self.streamer.unsubscribe(instruments)
            for inst in instruments:
                if inst in self.subscribed_instruments:
                    self.subscribed_instruments.remove(inst)
            logger.info(f"Unsubscribed from {len(instruments)} instruments")
        except Exception as e:
            logger.error(f"Failed to unsubscribe: {str(e)}")

    async def disconnect(self) -> None:
        """Disconnect WebSocket."""
        if self.streamer:
            try:
                self.streamer.disconnect()
                self._connected = False
                logger.info("WebSocket disconnected")
            except Exception as e:
                logger.error(f"Error disconnecting: {str(e)}")

    def is_connected(self) -> bool:
        """Check if connected.
        
        Returns:
            True if connected
        """
        return self._connected
