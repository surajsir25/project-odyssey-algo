"""Market data helpers for the trading engine."""

from __future__ import annotations

import logging

from odyssey_algo.trading.models import Quote
from odyssey_algo.trading.upstox_rest import UpstoxRestClient, extract_last_price

logger = logging.getLogger("odyssey_algo")


class MarketDataService:
    """Fetch and normalize live quotes."""

    def __init__(self, client: UpstoxRestClient) -> None:
        self.client = client

    def get_quote(self, instrument_key: str) -> Quote | None:
        quotes = self.get_quotes(instrument_key)
        return quotes.get(instrument_key)

    def get_quotes(self, *instrument_keys: str) -> dict[str, Quote]:
        if not instrument_keys:
            return {}

        raw = self.client.get_ltp(*instrument_keys)
        result: dict[str, Quote] = {}
        for key in instrument_keys:
            entry = raw.get(key)
            if entry is None:
                continue
            last_price = extract_last_price(entry)
            if last_price is None:
                continue
            result[key] = Quote(
                instrument_key=key,
                last_price=last_price,
                volume=int(entry.get("volume", 0) or 0),
                oi=int(entry.get("oi", 0) or 0),
                net_change=float(entry.get("net_change", 0) or 0),
            )
        return result

    def get_spot(self, index_key: str) -> float | None:
        quote = self.get_quote(index_key)
        return quote.last_price if quote else None
