"""Order routing with risk checks and journaling."""

from __future__ import annotations

import logging

from odyssey_algo.trading.journal import TradeJournal
from odyssey_algo.trading.market_data import MarketDataService
from odyssey_algo.trading.models import OrderRequest, OrderResult, OrderStatus, Signal
from odyssey_algo.trading.orders.broker import OrderBroker
from odyssey_algo.trading.risk.manager import RiskManager

logger = logging.getLogger("odyssey_algo")


class OrderManager:
    """Translate approved signals into broker orders."""

    def __init__(
        self,
        broker: OrderBroker,
        risk: RiskManager,
        market_data: MarketDataService,
        journal: TradeJournal,
    ) -> None:
        self.broker = broker
        self.risk = risk
        self.market_data = market_data
        self.journal = journal

    def execute_signal(self, signal: Signal, request: OrderRequest) -> OrderResult | None:
        quote = self.market_data.get_quote(request.instrument_key)
        estimated_price = quote.last_price if quote else 0.0

        check = self.risk.check_order(request, estimated_price)
        if not check.allowed:
            logger.warning("Risk blocked order: %s", check.reason)
            self.journal.record(
                "order_blocked",
                {"signal": signal, "request": request, "reason": check.reason},
            )
            return None

        fill_price = estimated_price if estimated_price > 0 else None
        result = self.broker.place_order(request, fill_price=fill_price)
        self.journal.record(
            "order_result",
            {"signal": signal, "request": request, "result": result},
        )

        if result.status in {OrderStatus.FILLED, OrderStatus.SUBMITTED}:
            self.risk.record_order(result, estimated_price)

        return result

    def positions_summary(self) -> list[dict[str, object]]:
        positions = self.broker.get_positions()
        summary: list[dict[str, object]] = []
        for pos in positions:
            quote = self.market_data.get_quote(pos.instrument_key)
            ltp = quote.last_price if quote else None
            summary.append(
                {
                    "instrument": pos.instrument_key,
                    "side": pos.side.value,
                    "quantity": pos.quantity,
                    "avg_price": pos.average_price,
                    "ltp": ltp,
                }
            )
        return summary
