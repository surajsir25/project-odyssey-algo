"""Order execution backends."""

from __future__ import annotations

import logging
import uuid
from abc import ABC, abstractmethod
from typing import Any

import upstox_client

from odyssey_algo.trading.models import (
    OrderRequest,
    OrderResult,
    OrderSide,
    OrderStatus,
    Position,
    utc_now,
)
from odyssey_algo.trading.upstox_rest import UpstoxRestClient

logger = logging.getLogger("odyssey_algo")


class OrderBroker(ABC):
    @abstractmethod
    def place_order(self, request: OrderRequest, fill_price: float | None = None) -> OrderResult:
        raise NotImplementedError

    @abstractmethod
    def get_positions(self) -> list[Position]:
        raise NotImplementedError

    @abstractmethod
    def reset_day(self) -> None:
        raise NotImplementedError


class PaperBroker(OrderBroker):
    """Simulates order fills at the provided LTP."""

    def __init__(self) -> None:
        self._positions: dict[str, Position] = {}
        self._orders: list[OrderResult] = []

    def place_order(self, request: OrderRequest, fill_price: float | None = None) -> OrderResult:
        if fill_price is None or fill_price <= 0:
            result = OrderResult(
                order_id=f"paper-{uuid.uuid4().hex[:12]}",
                instrument_key=request.instrument_key,
                quantity=request.quantity,
                side=request.side,
                status=OrderStatus.REJECTED,
                message="Paper fill requires a valid LTP",
            )
            self._orders.append(result)
            return result

        order_id = f"paper-{uuid.uuid4().hex[:12]}"
        result = OrderResult(
            order_id=order_id,
            instrument_key=request.instrument_key,
            quantity=request.quantity,
            side=request.side,
            status=OrderStatus.FILLED,
            fill_price=fill_price,
            message="Paper fill at LTP",
            submitted_at=utc_now(),
        )
        self._apply_fill(request, fill_price)
        self._orders.append(result)
        logger.info(
            "Paper fill: %s %s x%d @ %.2f",
            request.side.value,
            request.instrument_key,
            request.quantity,
            fill_price,
        )
        return result

    def _apply_fill(self, request: OrderRequest, fill_price: float) -> None:
        key = request.instrument_key
        existing = self._positions.get(key)
        signed_qty = request.quantity if request.side == OrderSide.BUY else -request.quantity

        if existing is None:
            if signed_qty == 0:
                return
            self._positions[key] = Position(
                instrument_key=key,
                quantity=abs(signed_qty),
                side=OrderSide.BUY if signed_qty > 0 else OrderSide.SELL,
                average_price=fill_price,
            )
            return

        existing_signed = existing.signed_quantity
        new_signed = existing_signed + signed_qty

        if new_signed == 0:
            del self._positions[key]
            return

        if (existing_signed > 0 and signed_qty > 0) or (existing_signed < 0 and signed_qty < 0):
            total_qty = abs(existing_signed) + abs(signed_qty)
            weighted = (
                existing.average_price * abs(existing_signed) + fill_price * abs(signed_qty)
            ) / total_qty
            self._positions[key] = Position(
                instrument_key=key,
                quantity=total_qty,
                side=OrderSide.BUY if new_signed > 0 else OrderSide.SELL,
                average_price=weighted,
                opened_at=existing.opened_at,
            )
            return

        self._positions[key] = Position(
            instrument_key=key,
            quantity=abs(new_signed),
            side=OrderSide.BUY if new_signed > 0 else OrderSide.SELL,
            average_price=fill_price,
            opened_at=utc_now(),
        )

    def get_positions(self) -> list[Position]:
        return list(self._positions.values())

    def reset_day(self) -> None:
        self._positions.clear()
        self._orders.clear()


class LiveBroker(OrderBroker):
    """Places real orders via Upstox OrderApiV3."""

    def __init__(self, client: UpstoxRestClient, algo_name: str) -> None:
        self.client = client
        self.algo_name = algo_name

    def place_order(self, request: OrderRequest, fill_price: float | None = None) -> OrderResult:
        body = upstox_client.PlaceOrderV3Request(**request.to_place_order_kwargs())
        try:
            response = self.client.place_order(body, algo_name=self.algo_name)
            order_id = _extract_order_id(response)
            return OrderResult(
                order_id=order_id or "unknown",
                instrument_key=request.instrument_key,
                quantity=request.quantity,
                side=request.side,
                status=OrderStatus.SUBMITTED,
                message="Order submitted to Upstox",
                raw_response=_response_to_dict(response),
            )
        except Exception as exc:
            logger.exception("Live order failed for %s", request.instrument_key)
            return OrderResult(
                order_id="",
                instrument_key=request.instrument_key,
                quantity=request.quantity,
                side=request.side,
                status=OrderStatus.REJECTED,
                message=str(exc),
            )

    def get_positions(self) -> list[Position]:
        try:
            response = self.client.get_positions()
            data = getattr(response, "data", None) or []
            positions: list[Position] = []
            for entry in data:
                entry_dict = entry.to_dict() if hasattr(entry, "to_dict") else entry
                qty = int(entry_dict.get("quantity", 0) or 0)
                if qty == 0:
                    continue
                positions.append(
                    Position(
                        instrument_key=str(entry_dict.get("instrument_token", "")),
                        quantity=abs(qty),
                        side=OrderSide.BUY if qty > 0 else OrderSide.SELL,
                        average_price=float(entry_dict.get("average_price", 0) or 0),
                    )
                )
            return positions
        except Exception:
            logger.exception("Failed to fetch live positions")
            return []

    def reset_day(self) -> None:
        return


def _extract_order_id(response: Any) -> str | None:
    if response is None:
        return None
    if hasattr(response, "data") and response.data is not None:
        data = response.data
        if hasattr(data, "order_id"):
            return str(data.order_id)
        if isinstance(data, dict):
            return str(data.get("order_id", "")) or None
    if hasattr(response, "order_id"):
        return str(response.order_id)
    return None


def _response_to_dict(response: Any) -> dict[str, Any] | None:
    if response is None:
        return None
    if hasattr(response, "to_dict"):
        return response.to_dict()
    if isinstance(response, dict):
        return response
    return {"raw": str(response)}
