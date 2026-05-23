"""Shared pytest fixtures."""

from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture
def sample_index_feed() -> dict:
    return {
        "fullFeed": {
            "indexFF": {
                "marketOHLC": {
                    "ohlc": [
                        {
                            "interval": "I1",
                            "ts": 1710000000,
                            "open": 100.0,
                            "high": 101.0,
                            "low": 99.0,
                            "close": 100.5,
                            "volume": 1000,
                            "oi": 0,
                        },
                        {
                            "interval": "I5",
                            "ts": 1710000300,
                            "open": 100.0,
                            "high": 102.0,
                            "low": 98.0,
                            "close": 101.0,
                            "volume": 5000,
                            "oi": 0,
                        },
                    ]
                }
            }
        }
    }


@pytest.fixture
def tmp_output_dir(tmp_path: Path) -> Path:
    return tmp_path / "data"
