"""Tests for the NIFTY momentum reference strategy."""

from pathlib import Path

from odyssey_algo.trading.models import ProductType, SignalAction, TradingMode
from odyssey_algo.trading.nifty_instruments import NiftyOptionsResolver
from odyssey_algo.trading.settings import TradingSettings
from odyssey_algo.trading.strategy.base import NiftyMomentumStrategy, StrategyContext


class _FakeClient:
    def search_instruments(self, query: str, **kwargs):
        option_type = kwargs.get("instrument_types", "CE")
        return [
            {
                "instrument_key": f"NSE_FO|{option_type}",
                "trading_symbol": f"NIFTY{option_type}",
                "underlying_symbol": "NIFTY",
                "instrument_type": option_type,
                "strike_price": 24000,
                "expiry": "2026-06-26",
                "lot_size": 75,
            }
        ]

    def get_ltp(self, *instrument_keys: str):
        return {}


def _settings() -> TradingSettings:
    return TradingSettings(
        access_token="test-token",
        trading_mode=TradingMode.PAPER,
        algo_name="test-algo",
        underlying="NIFTY",
        nifty_index_key="NSE_INDEX|Nifty 50",
        option_expiry="current_week",
        strategy_name="nifty_momentum",
        product=ProductType.INTRADAY,
        poll_interval_sec=30,
        max_open_positions=2,
        max_daily_loss_inr=5000,
        max_order_lots=1,
        momentum_threshold_points=50,
        output_dir=Path("data"),
        journal_enabled=False,
        log_level="INFO",
        log_file=None,
        kill_switch=False,
    )


def test_strategy_sets_session_open_on_first_tick() -> None:
    settings = _settings()
    strategy = NiftyMomentumStrategy(settings)
    resolver = NiftyOptionsResolver(_FakeClient())  # type: ignore[arg-type]
    context = StrategyContext(settings=settings, resolver=resolver, spot_price=24000.0)

    signals = strategy.on_tick(context)
    assert signals == []
    assert context.session_open_spot == 24000.0


def test_strategy_emits_ce_signal_on_upward_move() -> None:
    settings = _settings()
    strategy = NiftyMomentumStrategy(settings)
    resolver = NiftyOptionsResolver(_FakeClient())  # type: ignore[arg-type]
    context = StrategyContext(
        settings=settings,
        resolver=resolver,
        spot_price=24000.0,
        session_open_spot=23900.0,
    )

    signals = strategy.on_tick(context)
    assert len(signals) == 1
    assert signals[0].action == SignalAction.ENTER_LONG
    assert signals[0].instrument_key == "NSE_FO|CE"
    assert "up" in signals[0].reason.lower()


def test_strategy_emits_pe_signal_on_downward_move() -> None:
    settings = _settings()
    strategy = NiftyMomentumStrategy(settings)
    resolver = NiftyOptionsResolver(_FakeClient())  # type: ignore[arg-type]
    context = StrategyContext(
        settings=settings,
        resolver=resolver,
        spot_price=23900.0,
        session_open_spot=24000.0,
    )

    signals = strategy.on_tick(context)
    assert len(signals) == 1
    assert signals[0].instrument_key == "NSE_FO|PE"
