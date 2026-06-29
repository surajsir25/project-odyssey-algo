"""Strategy framework for Phase 1."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from odyssey_algo.trading.models import (
    OptionType,
    OrderRequest,
    OrderSide,
    Signal,
    SignalAction,
)
from odyssey_algo.trading.nifty_instruments import NiftyOptionsResolver
from odyssey_algo.trading.settings import TradingSettings


@dataclass
class StrategyContext:
    settings: TradingSettings
    resolver: NiftyOptionsResolver
    spot_price: float | None = None
    session_open_spot: float | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class BaseStrategy(ABC):
    name: str = "base"

    def __init__(self, settings: TradingSettings) -> None:
        self.settings = settings

    @abstractmethod
    def on_tick(self, context: StrategyContext) -> list[Signal]:
        raise NotImplementedError

    def signal_to_order(self, signal: Signal) -> OrderRequest | None:
        if signal.action == SignalAction.HOLD:
            return None

        side = OrderSide.BUY
        if signal.action == SignalAction.ENTER_SHORT:
            side = OrderSide.SELL

        return OrderRequest(
            instrument_key=signal.instrument_key,
            quantity=signal.quantity,
            side=side,
            product=self.settings.product,
            tag=f"odyssey-{self.name}",
        )


class ATMOptionStrategy(BaseStrategy):
    """
    ATM options strategy: enter ATM CE/PE based on intraday breakouts.

    Tracks intraday high and low levels. Generates entry signals for ATM CE
    on breakout above previous high, ATM PE on breakout below previous low.
    Resets levels on session change.
    """

    name = "atm_options"

    def on_tick(self, context: StrategyContext) -> list[Signal]:
        spot = context.spot_price
        if spot is None:
            return []

        # Initialize session tracking
        if context.session_open_spot is None:
            context.session_open_spot = spot
            context.metadata["intraday_high"] = spot
            context.metadata["intraday_low"] = spot
            context.metadata["last_ce_signal"] = None
            context.metadata["last_pe_signal"] = None
            return []

        # Track intraday extremes
        intraday_high = context.metadata.get("intraday_high", spot)
        intraday_low = context.metadata.get("intraday_low", spot)
        last_ce_signal = context.metadata.get("last_ce_signal")
        last_pe_signal = context.metadata.get("last_pe_signal")

        signals: list[Signal] = []

        # CE signal on breakout above high (if not already triggered)
        if spot > intraday_high and last_ce_signal != intraday_high:
            contract = context.resolver.resolve_for_signal(OptionType.CE)
            if contract is not None:
                intraday_high = spot
                context.metadata["intraday_high"] = intraday_high
                signals.append(
                    Signal(
                        action=SignalAction.ENTER_LONG,
                        instrument_key=contract.instrument_key,
                        quantity=contract.lot_size * self.settings.max_order_lots,
                        reason=f"ATM CE: breakout above {intraday_high:.2f} (current {spot:.2f})",
                        metadata={
                            "spot": spot,
                            "intraday_high": intraday_high,
                            "intraday_low": intraday_low,
                            "strike": contract.strike_price,
                            "option_type": contract.option_type.value,
                        },
                    )
                )
                context.metadata["last_ce_signal"] = intraday_high
        elif spot > intraday_high:
            intraday_high = spot
            context.metadata["intraday_high"] = intraday_high

        # PE signal on breakout below low (if not already triggered)
        if spot < intraday_low and last_pe_signal != intraday_low:
            contract = context.resolver.resolve_for_signal(OptionType.PE)
            if contract is not None:
                intraday_low = spot
                context.metadata["intraday_low"] = intraday_low
                signals.append(
                    Signal(
                        action=SignalAction.ENTER_LONG,
                        instrument_key=contract.instrument_key,
                        quantity=contract.lot_size * self.settings.max_order_lots,
                        reason=f"ATM PE: breakout below {intraday_low:.2f} (current {spot:.2f})",
                        metadata={
                            "spot": spot,
                            "intraday_high": intraday_high,
                            "intraday_low": intraday_low,
                            "strike": contract.strike_price,
                            "option_type": contract.option_type.value,
                        },
                    )
                )
                context.metadata["last_pe_signal"] = intraday_low
        elif spot < intraday_low:
            intraday_low = spot
            context.metadata["intraday_low"] = intraday_low

        return signals


class NiftyMomentumStrategy(BaseStrategy):
    """
    Reference strategy: enter ATM CE on upward momentum, ATM PE on downward.

    Compares current NIFTY spot to the session open. Threshold is configurable
    via ODYSSEY_MOMENTUM_THRESHOLD_POINTS (default 50 points).
    """

    name = "nifty_momentum"

    def on_tick(self, context: StrategyContext) -> list[Signal]:
        spot = context.spot_price
        if spot is None:
            return []

        if context.session_open_spot is None:
            context.session_open_spot = spot
            return []

        move = spot - context.session_open_spot
        threshold = self.settings.momentum_threshold_points

        if abs(move) < threshold:
            return []

        if move >= threshold:
            contract = context.resolver.resolve_for_signal(OptionType.CE)
            if contract is None:
                return []
            return [
                Signal(
                    action=SignalAction.ENTER_LONG,
                    instrument_key=contract.instrument_key,
                    quantity=contract.lot_size * self.settings.max_order_lots,
                    reason=f"NIFTY up {move:.1f} pts from open (threshold {threshold})",
                    metadata={
                        "spot": spot,
                        "session_open": context.session_open_spot,
                        "strike": contract.strike_price,
                        "option_type": contract.option_type.value,
                    },
                )
            ]

        contract = context.resolver.resolve_for_signal(OptionType.PE)
        if contract is None:
            return []
        return [
            Signal(
                action=SignalAction.ENTER_LONG,
                instrument_key=contract.instrument_key,
                quantity=contract.lot_size * self.settings.max_order_lots,
                reason=f"NIFTY down {abs(move):.1f} pts from open (threshold {threshold})",
                metadata={
                    "spot": spot,
                    "session_open": context.session_open_spot,
                    "strike": contract.strike_price,
                    "option_type": contract.option_type.value,
                },
            )
        ]


def build_strategy(settings: TradingSettings) -> BaseStrategy:
    if settings.strategy_name == "nifty_momentum":
        return NiftyMomentumStrategy(settings)
    if settings.strategy_name == "atm_options":
        return ATMOptionStrategy(settings)
    raise ValueError(f"Unknown strategy: {settings.strategy_name}")
