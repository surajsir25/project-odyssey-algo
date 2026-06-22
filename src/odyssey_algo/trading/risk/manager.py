"""Pre-trade and intraday risk controls."""

from __future__ import annotations

import logging
from dataclasses import dataclass

from odyssey_algo.trading.models import OrderRequest, OrderResult, OrderStatus
from odyssey_algo.trading.orders.broker import OrderBroker

logger = logging.getLogger("odyssey_algo")


@dataclass(frozen=True)
class RiskCheckResult:
    allowed: bool
    reason: str = ""


class RiskManager:
    """Enforce position limits, daily loss cap, and kill switch."""

    def __init__(
        self,
        broker: OrderBroker,
        max_open_positions: int,
        max_daily_loss_inr: float,
        max_order_lots: int,
        lot_size: int = 75,
        kill_switch: bool = False,
    ) -> None:
        self.broker = broker
        self.max_open_positions = max_open_positions
        self.max_daily_loss_inr = max_daily_loss_inr
        self.max_order_lots = max_order_lots
        self.lot_size = lot_size
        self.kill_switch = kill_switch
        self.realized_pnl_inr = 0.0
        self.orders_today = 0

    def check_order(self, request: OrderRequest, estimated_price: float) -> RiskCheckResult:
        if self.kill_switch:
            return RiskCheckResult(False, "Kill switch is active")

        lots = request.quantity // self.lot_size
        if lots > self.max_order_lots:
            return RiskCheckResult(
                False,
                f"Order size {lots} lots exceeds max {self.max_order_lots}",
            )

        open_positions = self.broker.get_positions()
        open_keys = {p.instrument_key for p in open_positions}
        is_new_position = request.instrument_key not in open_keys

        if is_new_position and len(open_keys) >= self.max_open_positions:
            return RiskCheckResult(
                False,
                f"Max open positions ({self.max_open_positions}) reached",
            )

        if self.realized_pnl_inr <= -self.max_daily_loss_inr:
            return RiskCheckResult(
                False,
                f"Daily loss limit breached ({self.max_daily_loss_inr} INR)",
            )

        notional = estimated_price * request.quantity
        if estimated_price <= 0:
            return RiskCheckResult(False, "Cannot estimate order notional without LTP")

        logger.debug("Risk OK: notional=%.2f INR for %s", notional, request.instrument_key)
        return RiskCheckResult(True)

    def record_order(self, result: OrderResult, estimated_price: float) -> None:
        self.orders_today += 1
        if result.status == OrderStatus.FILLED and result.fill_price is not None:
            # Phase 1 tracks realized PnL only on explicit exits (simplified).
            logger.info(
                "Order recorded: %s status=%s price=%.2f",
                result.order_id,
                result.status.value,
                result.fill_price,
            )
        elif estimated_price > 0:
            logger.info("Order recorded: %s status=%s", result.order_id, result.status.value)

    def update_realized_pnl(self, pnl_delta: float) -> None:
        self.realized_pnl_inr += pnl_delta
        if self.realized_pnl_inr <= -self.max_daily_loss_inr:
            logger.error(
                "Daily loss limit reached: %.2f INR (limit %.2f)",
                self.realized_pnl_inr,
                self.max_daily_loss_inr,
            )

    def activate_kill_switch(self, reason: str) -> None:
        self.kill_switch = True
        logger.critical("Kill switch activated: %s", reason)

    def reset_day(self) -> None:
        self.realized_pnl_inr = 0.0
        self.orders_today = 0
        self.kill_switch = False
        self.broker.reset_day()
