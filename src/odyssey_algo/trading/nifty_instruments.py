"""NIFTY options instrument resolution via Upstox Instruments API."""

from __future__ import annotations

import logging
from typing import Any

from odyssey_algo.trading.models import OptionContract, OptionType
from odyssey_algo.trading.upstox_rest import UpstoxRestClient, extract_last_price

logger = logging.getLogger("odyssey_algo")

NIFTY_LOT_SIZE = 75


class NiftyOptionsResolver:
    """Resolve ATM and offset NIFTY option contracts."""

    def __init__(
        self,
        client: UpstoxRestClient,
        underlying: str = "NIFTY",
        expiry: str = "current_week",
    ) -> None:
        self.client = client
        self.underlying = underlying
        self.expiry = expiry
        self._contract_cache: dict[tuple[str, int], OptionContract] = {}

    def get_spot_price(self, index_key: str) -> float | None:
        quotes = self.client.get_ltp(index_key)
        entry = quotes.get(index_key)
        if entry is None:
            return None
        return extract_last_price(entry)

    def get_atm_contract(
        self,
        option_type: OptionType,
        atm_offset: int = 0,
    ) -> OptionContract | None:
        cache_key = (option_type.value, atm_offset)
        if cache_key in self._contract_cache:
            return self._contract_cache[cache_key]

        instruments = self.client.search_instruments(
            self.underlying,
            exchanges="NSE",
            segments="FO",
            instrument_types=option_type.value,
            expiry=self.expiry,
            atm_offset=atm_offset,
            records=5,
        )
        contract = _pick_exact_underlying(instruments, self.underlying)
        if contract is None:
            logger.warning(
                "No %s contract found for %s expiry=%s offset=%s",
                option_type.value,
                self.underlying,
                self.expiry,
                atm_offset,
            )
            return None

        self._contract_cache[cache_key] = contract
        return contract

    def get_atm_pair(self) -> tuple[OptionContract | None, OptionContract | None]:
        return self.get_atm_contract(OptionType.CE), self.get_atm_contract(OptionType.PE)

    def resolve_for_signal(self, option_type: OptionType) -> OptionContract | None:
        return self.get_atm_contract(option_type, atm_offset=0)


def _pick_exact_underlying(
    instruments: list[dict[str, Any]],
    underlying: str,
) -> OptionContract | None:
    matches = [
        inst
        for inst in instruments
        if str(inst.get("underlying_symbol", "")).upper() == underlying.upper()
    ]
    if not matches:
        return None

    chosen = matches[0]
    contract = OptionContract.from_api(chosen)
    if contract.lot_size <= 0:
        contract = OptionContract(
            instrument_key=contract.instrument_key,
            trading_symbol=contract.trading_symbol,
            underlying=contract.underlying,
            option_type=contract.option_type,
            strike_price=contract.strike_price,
            expiry=contract.expiry,
            lot_size=NIFTY_LOT_SIZE,
        )
    return contract
