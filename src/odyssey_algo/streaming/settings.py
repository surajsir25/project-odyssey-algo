"""Streaming-specific settings."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

from odyssey_algo.settings import VALID_LOG_LEVELS, VALID_MODES, _env_bool

load_dotenv()


@dataclass(frozen=True)
class StreamingSettings:
    access_token: str
    nifty_index_key: str
    option_expiry: str
    stream_mode: str
    auto_reconnect: bool
    reconnect_interval: int
    max_retries: int
    database_url: str
    db_enabled: bool
    csv_enabled: bool
    output_dir: Path
    atm_roll_enabled: bool
    log_level: str
    log_file: Path | None

    @classmethod
    def from_env(cls) -> StreamingSettings:
        mode = os.getenv("UPSTOX_STREAM_MODE", "full").strip().lower()
        if mode not in VALID_MODES:
            raise ValueError(
                f"Invalid UPSTOX_STREAM_MODE '{mode}'. "
                f"Expected one of: {', '.join(sorted(VALID_MODES))}"
            )

        expiry = os.getenv("ODYSSEY_OPTION_EXPIRY", "current_week").strip().lower()
        log_level = os.getenv("ODYSSEY_LOG_LEVEL", "INFO").strip().upper()
        if log_level not in VALID_LOG_LEVELS:
            raise ValueError(f"Invalid ODYSSEY_LOG_LEVEL '{log_level}'")

        log_file_raw = os.getenv("ODYSSEY_LOG_FILE", "logs/odyssey_stream.log").strip()
        log_file = Path(log_file_raw) if log_file_raw else None

        return cls(
            access_token=os.getenv("UPSTOX_ACCESS_TOKEN", "").strip(),
            nifty_index_key=os.getenv(
                "ODYSSEY_NIFTY_INDEX_KEY", "NSE_INDEX|Nifty 50"
            ).strip(),
            option_expiry=expiry,
            stream_mode=mode,
            auto_reconnect=_env_bool("UPSTOX_AUTO_RECONNECT", True),
            reconnect_interval=int(os.getenv("UPSTOX_RECONNECT_INTERVAL", "5")),
            max_retries=int(os.getenv("UPSTOX_MAX_RETRIES", "10")),
            database_url=os.getenv("ODYSSEY_DATABASE_URL", "").strip(),
            db_enabled=_env_bool("ODYSSEY_DB_ENABLED", True),
            csv_enabled=_env_bool("ODYSSEY_CSV_ENABLED", False),
            output_dir=Path(os.getenv("ODYSSEY_OUTPUT_DIR", "data")),
            atm_roll_enabled=_env_bool("ODYSSEY_ATM_ROLL_ENABLED", True),
            log_level=log_level,
            log_file=log_file,
        )

    def validate(self) -> None:
        if not self.access_token or self.access_token == "your_upstox_access_token_here":
            raise ValueError(
                "UPSTOX_ACCESS_TOKEN is not set. Copy .env.example to .env and add your token."
            )
        if self.db_enabled and not self.database_url:
            raise ValueError(
                "ODYSSEY_DB_ENABLED is true but ODYSSEY_DATABASE_URL is not set."
            )
        if self.reconnect_interval < 1:
            raise ValueError("UPSTOX_RECONNECT_INTERVAL must be >= 1")
        if self.max_retries < 0:
            raise ValueError("UPSTOX_MAX_RETRIES must be >= 0")
