"""Example: stream market data using the odyssey_algo package."""

from __future__ import annotations

import time

from odyssey_algo.handler import UpstoxMarketDataHandler
from odyssey_algo.instruments import get_all_instruments
from odyssey_algo.logging_setup import setup_logging
from odyssey_algo.settings import Settings


def main() -> None:
    settings = Settings.from_env()
    settings.validate()
    setup_logging(settings.log_level, settings.log_file)

    handler = UpstoxMarketDataHandler(settings)
    handler.initialize_streamer(get_all_instruments())
    handler.enable_auto_reconnect()

    try:
        handler.connect()
        print("Streaming... Press Ctrl+C to stop.")
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopped.")
    finally:
        handler.disconnect()


if __name__ == "__main__":
    main()
