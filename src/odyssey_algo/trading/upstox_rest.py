"""Thin wrapper around Upstox REST SDK clients."""

from __future__ import annotations

import logging
from typing import Any

import upstox_client
from upstox_client import ApiClient, Configuration

logger = logging.getLogger("odyssey_algo")


class UpstoxRestClient:
    """Authenticated Upstox REST client for trading operations."""

    def __init__(self, access_token: str) -> None:
        configuration = Configuration()
        configuration.access_token = access_token
        self.api_client = ApiClient(configuration)
        self.instruments = upstox_client.InstrumentsApi(self.api_client)
        self.quotes_v3 = upstox_client.MarketQuoteV3Api(self.api_client)
        self.quotes = upstox_client.MarketQuoteApi(self.api_client)
        self.orders = upstox_client.OrderApiV3(self.api_client)
        self.portfolio = upstox_client.PortfolioApi(self.api_client)
        self.options = upstox_client.OptionsApi(self.api_client)

    def search_instruments(self, query: str, **kwargs: Any) -> list[dict[str, Any]]:
        response = self.instruments.search_instrument(query, **kwargs)
        return list(response.data or [])

    def get_ltp(self, *instrument_keys: str) -> dict[str, dict[str, Any]]:
        if not instrument_keys:
            return {}
        response = self.quotes_v3.get_ltp(instrument_key=",".join(instrument_keys))
        return _rekey_by_instrument_token(response.data)

    def get_full_quotes(self, *instrument_keys: str) -> dict[str, dict[str, Any]]:
        if not instrument_keys:
            return {}
        response = self.quotes.get_full_market_quote(",".join(instrument_keys), "2.0")
        return _rekey_by_instrument_token(response.data)

    def place_order(self, body: upstox_client.PlaceOrderV3Request, algo_name: str) -> Any:
        return self.orders.place_order(body, algo_name=algo_name)

    def cancel_order(self, order_id: str, algo_name: str) -> Any:
        return self.orders.cancel_order(order_id, algo_name=algo_name)

    def get_positions(self) -> Any:
        return self.portfolio.get_positions()


def _rekey_by_instrument_token(data: dict[str, Any] | None) -> dict[str, dict[str, Any]]:
    if not data:
        return {}

    result: dict[str, dict[str, Any]] = {}
    for entry in data.values():
        if hasattr(entry, "to_dict"):
            entry_dict = entry.to_dict()
        elif isinstance(entry, dict):
            entry_dict = entry
        else:
            continue
        token = entry_dict.get("instrument_token")
        if token:
            result[str(token)] = entry_dict
    return result


def extract_last_price(quote_entry: dict[str, Any] | Any) -> float | None:
    if quote_entry is None:
        return None
    if hasattr(quote_entry, "last_price"):
        return float(quote_entry.last_price)
    if isinstance(quote_entry, dict):
        if "last_price" in quote_entry:
            return float(quote_entry["last_price"])
        ltp = quote_entry.get("ltp")
        if isinstance(ltp, dict) and "last_price" in ltp:
            return float(ltp["last_price"])
    return None
