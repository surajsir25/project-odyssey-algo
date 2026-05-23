"""Persist market data to CSV files."""

from __future__ import annotations

import csv
import logging
from pathlib import Path


def _normalize_timestamp(value: str | int | None) -> str | int | None:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return value


CSV_FIELDNAMES = [
    "timestamp",
    "candle_timestamp",
    "instrument",
    "open",
    "high",
    "low",
    "close",
    "volume",
    "oi",
]


class CsvCandleStore:
    """Append-only CSV storage with restart-safe deduplication."""

    def __init__(self, output_dir: Path, enabled: bool = True) -> None:
        self.output_dir = output_dir
        self.enabled = enabled
        self.logger = logging.getLogger("odyssey_algo")
        self._file_paths: dict[tuple[str, str], Path] = {}
        self._last_candle_timestamp: dict[tuple[str, str], str | int | None] = {}

        if self.enabled:
            self.output_dir.mkdir(parents=True, exist_ok=True)
            self._hydrate_last_timestamps()

    def csv_path(self, instrument_key: str, interval: str) -> Path:
        safe_name = instrument_key.replace("|", "_")
        return self.output_dir / f"{safe_name}_{interval}.csv"

    def _ensure_csv(self, instrument_key: str, interval: str) -> Path | None:
        if not self.enabled:
            return None

        key = (instrument_key, interval)
        if key in self._file_paths:
            return self._file_paths[key]

        path = self.csv_path(instrument_key, interval)
        self._file_paths[key] = path

        if not path.exists() or path.stat().st_size == 0:
            with path.open("w", newline="", encoding="utf-8") as handle:
                csv.DictWriter(handle, fieldnames=CSV_FIELDNAMES).writeheader()
            self.logger.info("Created CSV file: %s", path)
        else:
            self.logger.info("Using existing CSV file: %s", path)

        return path

    def _hydrate_last_timestamps(self) -> None:
        if not self.output_dir.exists():
            return

        for path in self.output_dir.glob("*_*.csv"):
            last_row = self._read_last_row(path)
            if not last_row:
                continue

            instrument_key = last_row.get("instrument")
            candle_timestamp = last_row.get("candle_timestamp")
            if not instrument_key or candle_timestamp in (None, ""):
                continue

            interval = self._interval_from_path(path)
            if interval is None:
                continue

            self._last_candle_timestamp[(instrument_key, interval)] = _normalize_timestamp(
                candle_timestamp
            )

    @staticmethod
    def _interval_from_path(path: Path) -> str | None:
        if path.stem.endswith("_1min"):
            return "1min"
        if path.stem.endswith("_5min"):
            return "5min"
        return None

    @staticmethod
    def _read_last_row(path: Path) -> dict[str, str] | None:
        last_row: dict[str, str] | None = None
        with path.open(newline="", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            for row in reader:
                last_row = row
        return last_row

    def write_candle(self, instrument_key: str, interval: str, candle: dict) -> bool:
        """Write a candle if it is new. Returns True when persisted."""
        if not self.enabled:
            return False

        key = (instrument_key, interval)
        current_timestamp = _normalize_timestamp(candle.get("candle_timestamp"))
        last_timestamp = self._last_candle_timestamp.get(key)

        if current_timestamp == last_timestamp:
            return False

        path = self._ensure_csv(instrument_key, interval)
        if path is None:
            return False

        with path.open("a", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=CSV_FIELDNAMES)
            writer.writerow({field: candle.get(field) for field in CSV_FIELDNAMES})

        self._last_candle_timestamp[key] = current_timestamp
        return True
