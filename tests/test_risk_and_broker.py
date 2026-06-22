"""Tests for paper broker and risk manager."""

from odyssey_algo.trading.models import (
    OrderRequest,
    OrderSide,
    OrderStatus,
    OrderType,
    ProductType,
)
from odyssey_algo.trading.orders.broker import PaperBroker
from odyssey_algo.trading.risk.manager import RiskManager


def _buy_request(instrument: str, qty: int = 75) -> OrderRequest:
    return OrderRequest(
        instrument_key=instrument,
        quantity=qty,
        side=OrderSide.BUY,
        order_type=OrderType.MARKET,
        product=ProductType.INTRADAY,
    )


def test_paper_broker_fills_at_ltp() -> None:
    broker = PaperBroker()
    result = broker.place_order(_buy_request("NSE_FO|1"), fill_price=120.5)
    assert result.status == OrderStatus.FILLED
    assert result.fill_price == 120.5
    positions = broker.get_positions()
    assert len(positions) == 1
    assert positions[0].instrument_key == "NSE_FO|1"


def test_paper_broker_rejects_without_ltp() -> None:
    broker = PaperBroker()
    result = broker.place_order(_buy_request("NSE_FO|1"), fill_price=None)
    assert result.status == OrderStatus.REJECTED


def test_risk_blocks_when_kill_switch_active() -> None:
    broker = PaperBroker()
    risk = RiskManager(
        broker=broker,
        max_open_positions=2,
        max_daily_loss_inr=5000,
        max_order_lots=1,
        kill_switch=True,
    )
    check = risk.check_order(_buy_request("NSE_FO|1"), estimated_price=100.0)
    assert not check.allowed
    assert "Kill switch" in check.reason


def test_risk_blocks_max_positions() -> None:
    broker = PaperBroker()
    broker.place_order(_buy_request("NSE_FO|1"), fill_price=100.0)
    broker.place_order(_buy_request("NSE_FO|2"), fill_price=100.0)

    risk = RiskManager(
        broker=broker,
        max_open_positions=2,
        max_daily_loss_inr=5000,
        max_order_lots=1,
    )
    check = risk.check_order(_buy_request("NSE_FO|3"), estimated_price=100.0)
    assert not check.allowed


def test_risk_allows_valid_order() -> None:
    broker = PaperBroker()
    risk = RiskManager(
        broker=broker,
        max_open_positions=2,
        max_daily_loss_inr=5000,
        max_order_lots=1,
    )
    check = risk.check_order(_buy_request("NSE_FO|1"), estimated_price=100.0)
    assert check.allowed
