"""CLI entry point for NIFTY spot + ATM options candle streaming."""

from __future__ import annotations

import sys

from odyssey_algo.logging_setup import setup_logging
from odyssey_algo.streaming.service import NiftyStreamingService
from odyssey_algo.streaming.settings import StreamingSettings


def main() -> int:
    try:
        settings = StreamingSettings.from_env()
        settings.validate()
    except ValueError as exc:
        print(f"[Error] {exc}")
        return 1

    setup_logging(settings.log_level, settings.log_file)

    print("\n" + "=" * 60)
    print("Odyssey Algo — NIFTY Spot + ATM Options Streamer")
    print("=" * 60)
    print(f"Spot:       {settings.nifty_index_key}")
    print(f"Expiry:     {settings.option_expiry}")
    print(f"Mode:       {settings.stream_mode}")
    print(f"Database:   {'enabled' if settings.db_enabled else 'disabled'}")
    print(f"CSV backup: {'enabled' if settings.csv_enabled else 'disabled'}")
    print(f"ATM roll:   {'enabled' if settings.atm_roll_enabled else 'disabled'}")
    print("=" * 60 + "\n")

    service = NiftyStreamingService(settings)
    try:
        return service.run()
    except KeyboardInterrupt:
        service.stop()
        return 0
    except Exception as exc:
        print(f"[Fatal Error] {exc}")
        service.stop()
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
