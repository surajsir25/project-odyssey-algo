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
    raise ValueError(f"Unknown strategy: {settings.strategy_name}")
