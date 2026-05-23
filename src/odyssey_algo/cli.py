"""Command-line entry point for the market data streamer."""

from __future__ import annotations

import signal
import sys
import time

from odyssey_algo.handler import UpstoxMarketDataHandler
from odyssey_algo.instruments import get_all_instruments
from odyssey_algo.logging_setup import setup_logging
from odyssey_algo.settings import Settings


def _install_signal_handlers(handler: UpstoxMarketDataHandler) -> None:
    def _shutdown(signum: int, _frame: object) -> None:
        print(f"\nReceived signal {signum}. Shutting down...")
        handler.disconnect()
        sys.exit(0)

    signal.signal(signal.SIGINT, _shutdown)
    signal.signal(signal.SIGTERM, _shutdown)


def main() -> int:
    try:
        settings = Settings.from_env()
        settings.validate()
    except ValueError as exc:
        print(f"[Error] {exc}")
        return 1

    setup_logging(settings.log_level, settings.log_file)
    instruments = get_all_instruments()
    if not instruments:
        print("[Error] No instruments configured in odyssey_algo/instruments.py")
        return 1

    print("\n" + "=" * 60)
    print("Odyssey Algo — Upstox Market Data Streamer")
    print("=" * 60)
    print(f"Mode: {settings.mode}")
    print(f"Instruments: {len(instruments)}")
    print(f"Output dir: {settings.output_dir}")
    print("=" * 60 + "\n")

    handler = UpstoxMarketDataHandler(settings)
    _install_signal_handlers(handler)

    try:
        handler.initialize_streamer(instruments)
        handler.enable_auto_reconnect()
        handler.connect()

        print("\nStreaming started. Press Ctrl+C to stop.\n")
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping streamer...")
        handler.disconnect()
        return 0
    except Exception as exc:
        print(f"[Fatal Error] {exc}")
        handler.disconnect()
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
