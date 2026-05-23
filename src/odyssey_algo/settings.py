"""Application settings loaded from environment variables."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

VALID_MODES = frozenset({"full", "ltpc", "full_d30", "option_greeks"})
VALID_LOG_LEVELS = frozenset({"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"})


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    access_token: str
    mode: str
    auto_reconnect: bool
    reconnect_interval: int
    max_retries: int
    output_dir: Path
    csv_enabled: bool
    log_level: str
    log_file: Path | None

    @classmethod
    def from_env(cls) -> Settings:
        access_token = os.getenv("UPSTOX_ACCESS_TOKEN", "").strip()
        mode = os.getenv("UPSTOX_STREAM_MODE", "full").strip().lower()
        if mode not in VALID_MODES:
            raise ValueError(
                f"Invalid UPSTOX_STREAM_MODE '{mode}'. "
                f"Expected one of: {', '.join(sorted(VALID_MODES))}"
            )

        log_level = os.getenv("ODYSSEY_LOG_LEVEL", "INFO").strip().upper()
        if log_level not in VALID_LOG_LEVELS:
            raise ValueError(
                f"Invalid ODYSSEY_LOG_LEVEL '{log_level}'. "
                f"Expected one of: {', '.join(sorted(VALID_LOG_LEVELS))}"
            )

        log_file_raw = os.getenv("ODYSSEY_LOG_FILE", "logs/upstox_streamer.log").strip()
        log_file = Path(log_file_raw) if log_file_raw else None

        return cls(
            access_token=access_token,
            mode=mode,
            auto_reconnect=_env_bool("UPSTOX_AUTO_RECONNECT", True),
            reconnect_interval=int(os.getenv("UPSTOX_RECONNECT_INTERVAL", "5")),
            max_retries=int(os.getenv("UPSTOX_MAX_RETRIES", "10")),
            output_dir=Path(os.getenv("ODYSSEY_OUTPUT_DIR", "data")),
            csv_enabled=_env_bool("ODYSSEY_CSV_ENABLED", True),
            log_level=log_level,
            log_file=log_file,
        )

    def validate(self) -> None:
        if not self.access_token or self.access_token == "your_upstox_access_token_here":
            raise ValueError(
                "UPSTOX_ACCESS_TOKEN is not set. Copy .env.example to .env and add your token."
            )
        if self.reconnect_interval < 1:
            raise ValueError("UPSTOX_RECONNECT_INTERVAL must be >= 1")
        if self.max_retries < 0:
            raise ValueError("UPSTOX_MAX_RETRIES must be >= 0")
