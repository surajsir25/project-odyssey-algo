"""Command-line entry point for the Phase 1 trading engine."""

from __future__ import annotations

import signal
import sys

from odyssey_algo.logging_setup import setup_logging
from odyssey_algo.trading.engine import TradingEngine
from odyssey_algo.trading.settings import TradingSettings


def _install_signal_handlers(engine: TradingEngine) -> None:
    def _shutdown(signum: int, _frame: object) -> None:
        print(f"\nReceived signal {signum}. Shutting down...")
        engine.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, _shutdown)
    signal.signal(signal.SIGTERM, _shutdown)


def main() -> int:
    try:
        settings = TradingSettings.from_env()
        settings.validate()
    except ValueError as exc:
        print(f"[Error] {exc}")
        return 1

    setup_logging(settings.log_level, settings.log_file)
    engine = TradingEngine.from_settings(settings)
    _install_signal_handlers(engine)

    print("\n" + "=" * 60)
    print("Odyssey Algo — Phase 1 NIFTY Options Trading Engine")
    print("=" * 60)
    print(f"Mode:       {settings.trading_mode.value}")
    print(f"Strategy:   {settings.strategy_name}")
    print(f"Underlying: {settings.underlying}")
    print(f"Expiry:     {settings.option_expiry}")
    print(f"Algo name:  {settings.algo_name}")
    print(f"Poll:       every {settings.poll_interval_sec}s")
    print("=" * 60)
    if settings.trading_mode.value == "live":
        print("\n⚠️  LIVE TRADING MODE — real orders will be placed.\n")
    else:
        print("\nPaper trading mode — no real orders.\n")

    try:
        engine.run()
        return 0
    except KeyboardInterrupt:
        engine.stop()
        return 0
    except Exception as exc:
        print(f"[Fatal Error] {exc}")
        engine.stop()
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
