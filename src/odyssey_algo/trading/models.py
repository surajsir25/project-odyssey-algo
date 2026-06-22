"""Domain models for the trading engine."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class TradingMode(str, Enum):
    PAPER = "paper"
    LIVE = "live"


class OrderSide(str, Enum):
    BUY = "BUY"
    SELL = "SELL"


class OrderType(str, Enum):
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    SL = "SL"
    SL_M = "SL-M"


class ProductType(str, Enum):
    INTRADAY = "I"
    DELIVERY = "D"


class OrderStatus(str, Enum):
    PENDING = "pending"
    SUBMITTED = "submitted"
    FILLED = "filled"
    REJECTED = "rejected"
    CANCELLED = "cancelled"


class SignalAction(str, Enum):
    ENTER_LONG = "enter_long"
    ENTER_SHORT = "enter_short"
    EXIT = "exit"
    HOLD = "hold"


class OptionType(str, Enum):
    CE = "CE"
    PE = "PE"


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True)
class OptionContract:
    instrument_key: str
    trading_symbol: str
    underlying: str
    option_type: OptionType
    strike_price: float
    expiry: str
    lot_size: int

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> OptionContract:
        raw_type = str(data.get("instrument_type", "")).upper()
        return cls(
            instrument_key=str(data["instrument_key"]),
            trading_symbol=str(data.get("trading_symbol", "")),
            underlying=str(data.get("underlying_symbol", data.get("name", ""))),
            option_type=OptionType(raw_type),
            strike_price=float(data.get("strike_price", 0)),
            expiry=str(data.get("expiry", "")),
            lot_size=int(data.get("lot_size", 0)),
        )


@dataclass(frozen=True)
class OrderRequest:
    instrument_key: str
    quantity: int
    side: OrderSide
    order_type: OrderType = OrderType.MARKET
    product: ProductType = ProductType.INTRADAY
    price: float = 0.0
    trigger_price: float = 0.0
    tag: str = "odyssey"
    slice: bool = True

    def to_place_order_kwargs(self) -> dict[str, Any]:
        return {
            "instrument_token": self.instrument_key,
            "quantity": self.quantity,
            "transaction_type": self.side.value,
            "order_type": self.order_type.value,
            "product": self.product.value,
            "validity": "DAY",
            "price": self.price,
            "trigger_price": self.trigger_price,
            "disclosed_quantity": 0,
            "is_amo": False,
            "slice": self.slice,
            "tag": self.tag,
        }


@dataclass
class OrderResult:
    order_id: str
    instrument_key: str
    quantity: int
    side: OrderSide
    status: OrderStatus
    fill_price: float | None = None
    message: str = ""
    submitted_at: datetime = field(default_factory=utc_now)
    raw_response: dict[str, Any] | None = None


@dataclass(frozen=True)
class Signal:
    action: SignalAction
    instrument_key: str
    quantity: int
    reason: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class Position:
    instrument_key: str
    quantity: int
    side: OrderSide
    average_price: float
    opened_at: datetime = field(default_factory=utc_now)

    @property
    def signed_quantity(self) -> int:
        return self.quantity if self.side == OrderSide.BUY else -self.quantity


@dataclass
class Quote:
    instrument_key: str
    last_price: float
    volume: int = 0
    oi: int = 0
    net_change: float = 0.0
