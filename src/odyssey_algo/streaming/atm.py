"""ATM strike detection and NIFTY option contract management."""

from __future__ import annotations

import logging
from dataclasses import dataclass

from odyssey_algo.trading.models import OptionContract, OptionType
from odyssey_algo.trading.nifty_instruments import NiftyOptionsResolver

logger = logging.getLogger("odyssey_algo")

NIFTY_STRIKE_STEP = 50


def round_to_atm_strike(spot: float) -> int:
    """Round NIFTY spot to the nearest 50-point strike."""
    return int(round(spot / NIFTY_STRIKE_STEP) * NIFTY_STRIKE_STEP)


@dataclass(frozen=True)
class AtmPair:
    strike: int
    ce: OptionContract
    pe: OptionContract


class AtmStrikeManager:
    """Track ATM strike from spot and resolve CE/PE contracts for the nearest weekly expiry."""

    def __init__(self, resolver: NiftyOptionsResolver) -> None:
        self.resolver = resolver
        self.current_strike: int | None = None
        self.current_pair: AtmPair | None = None

    def strike_from_spot(self, spot: float) -> int:
        return round_to_atm_strike(spot)

    def resolve_pair(self, spot: float | None = None) -> AtmPair | None:
        """Resolve ATM CE/PE via Upstox Instruments API (uses live spot when spot is None)."""
        if spot is not None:
            self.current_strike = self.strike_from_spot(spot)

        self.resolver._contract_cache.clear()
        ce = self.resolver.get_atm_contract(OptionType.CE)
        pe = self.resolver.get_atm_contract(OptionType.PE)
        if ce is None or pe is None:
            logger.warning("Failed to resolve ATM CE/PE pair")
            return None

        strike = int(ce.strike_price)
        self.current_strike = strike
        self.current_pair = AtmPair(strike=strike, ce=ce, pe=pe)
        logger.info(
            "ATM pair resolved: strike=%s CE=%s PE=%s expiry=%s",
            strike,
            ce.trading_symbol,
            pe.trading_symbol,
            ce.expiry,
        )
        return self.current_pair

    def should_roll(self, spot: float) -> bool:
        """Return True when spot has crossed into a new ATM strike bucket."""
        new_strike = self.strike_from_spot(spot)
        return self.current_strike is not None and new_strike != self.current_strike

    def instrument_keys(self) -> list[str]:
        if self.current_pair is None:
            return []
        return [self.current_pair.ce.instrument_key, self.current_pair.pe.instrument_key]
