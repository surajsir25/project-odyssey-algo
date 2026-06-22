"""Tests for trading domain models."""

from odyssey_algo.trading.models import (
    OptionContract,
    OptionType,
    OrderRequest,
    OrderSide,
    OrderType,
    ProductType,
    Signal,
    SignalAction,
)


def test_option_contract_from_api() -> None:
    contract = OptionContract.from_api(
        {
            "instrument_key": "NSE_FO|12345",
            "trading_symbol": "NIFTY25JUN24000CE",
            "underlying_symbol": "NIFTY",
            "instrument_type": "CE",
            "strike_price": 24000,
            "expiry": "2025-06-26",
            "lot_size": 75,
        }
    )
    assert contract.instrument_key == "NSE_FO|12345"
    assert contract.option_type == OptionType.CE
    assert contract.lot_size == 75


def test_order_request_to_place_order_kwargs() -> None:
    request = OrderRequest(
        instrument_key="NSE_FO|12345",
        quantity=75,
        side=OrderSide.BUY,
        order_type=OrderType.MARKET,
        product=ProductType.INTRADAY,
    )
    kwargs = request.to_place_order_kwargs()
    assert kwargs["instrument_token"] == "NSE_FO|12345"
    assert kwargs["quantity"] == 75
    assert kwargs["transaction_type"] == "BUY"
    assert kwargs["product"] == "I"
    assert kwargs["slice"] is True


def test_signal_metadata_defaults() -> None:
    signal = Signal(
        action=SignalAction.ENTER_LONG,
        instrument_key="NSE_FO|1",
        quantity=75,
        reason="test",
    )
    assert signal.metadata == {}
