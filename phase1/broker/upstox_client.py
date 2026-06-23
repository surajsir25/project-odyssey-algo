"""Upstox REST API client wrapper."""

from typing import Any, Optional, dict, list
from decimal import Decimal
from loguru import logger
from upstox_client import ApiClient, Configuration, InstrumentsApi

from config.settings import settings


class UpstoxRestClient:
    """Authenticated REST client for Upstox API."""

    def __init__(self) -> None:
        """Initialize Upstox REST client with API credentials."""
        config = Configuration()
        config.access_token = settings.upstox.access_token
        self.api_client = ApiClient(config)
        self.instruments_api = InstrumentsApi(self.api_client)
        logger.info("Upstox REST client initialized")

    async def get_instrument_master(self) -> list[dict]:
        """Fetch instrument master from Upstox API.
        
        Returns:
            List of instrument dictionaries
            
        Raises:
            Exception: If API call fails
        """
        try:
            response = self.instruments_api.search_instrument()
            logger.info(f"Downloaded instrument master with {len(response.data)} instruments")
            return self._parse_instruments(response.data)
        except Exception as e:
            logger.error(f"Failed to fetch instrument master: {str(e)}")
            raise

    def _parse_instruments(self, api_response: Any) -> list[dict]:
        """Parse API response into instrument dictionaries.
        
        Args:
            api_response: Raw API response
            
        Returns:
            List of parsed instrument dicts
        """
        instruments = []
        
        if not hasattr(api_response, '__iter__'):
            return instruments
        
        for item in api_response:
            try:
                instrument = {
                    "instrument_key": getattr(item, "instrument_key", None),
                    "trading_symbol": getattr(item, "trading_symbol", None),
                    "exchange": getattr(item, "exchange", None),
                    "expiry": getattr(item, "expiry", None),
                    "strike": getattr(item, "strike", None),
                    "option_type": getattr(item, "option_type", None),
                }
                if instrument.get("instrument_key"):
                    instruments.append(instrument)
            except Exception as e:
                logger.warning(f"Failed to parse instrument: {str(e)}")
                continue
        
        return instruments

    async def search_instruments(self, query: str) -> list[dict]:
        """Search for instruments by name/symbol.
        
        Args:
            query: Search query
            
        Returns:
            List of matching instruments
        """
        try:
            response = self.instruments_api.search_instrument(query)
            return self._parse_instruments(response.data)
        except Exception as e:
            logger.error(f"Failed to search instruments: {str(e)}")
            raise
