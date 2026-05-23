#!/usr/bin/env python3
"""Debug Upstox WebSocket payloads (prints first few messages)."""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

# Allow running without editable install
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from upstox_client import ApiClient, Configuration, MarketDataStreamerV3

from odyssey_algo.instruments import get_all_instruments
from odyssey_algo.settings import Settings


def main() -> int:
    try:
        settings = Settings.from_env()
        settings.validate()
    except ValueError as exc:
        print(f"[Error] {exc}")
        return 1

    instruments = get_all_instruments()[:1]
    if not instruments:
        print("[Error] No instruments configured")
        return 1

    print("\n" + "=" * 70)
    print("UPSTOX STREAMER — DEBUG MODE")
    print("=" * 70)
    print(f"Token: {settings.access_token[:20]}...")
    print(f"Mode: {settings.mode}")
    print(f"Instruments: {instruments}")
    print("=" * 70 + "\n")

    configuration = Configuration()
    configuration.access_token = settings.access_token
    api_client = ApiClient(configuration)

    streamer = MarketDataStreamerV3(
        api_client=api_client,
        instrumentKeys=instruments,
        mode=settings.mode,
    )

    message_count = [0]

    def on_open() -> None:
        print("\nWebSocket OPEN\n")

    def on_message(message: object) -> None:
        message_count[0] += 1
        print("\n" + "=" * 70)
        print(f"MESSAGE #{message_count[0]}")
        print("=" * 70)
        print(f"Type: {type(message)}")
        payload = json.dumps(message, indent=2, default=str)
        print(f"{payload[:2000]}{'...' if len(payload) > 2000 else ''}")
        print("=" * 70 + "\n")

        if message_count[0] >= 3:
            print("Received 3 messages. Stopping debug.")
            streamer.disconnect()

    def on_error(error: object) -> None:
        print(f"\nERROR: {error}\n")
        streamer.disconnect()

    def on_close() -> None:
        print("\nWebSocket CLOSED\n")

    def on_reconnecting() -> None:
        print("\nRECONNECTING\n")

    streamer.on("open", on_open)
    streamer.on("message", on_message)
    streamer.on("error", on_error)
    streamer.on("close", on_close)
    streamer.on("reconnecting", on_reconnecting)

    try:
        print("Connecting...")
        streamer.connect()

        for _ in range(30):
            time.sleep(1)
            if message_count[0] >= 3:
                break

        streamer.disconnect()
    except KeyboardInterrupt:
        print("\nStopped by user")
        streamer.disconnect()
    except Exception as exc:
        print(f"\n[Error] {exc}")
        streamer.disconnect()
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
