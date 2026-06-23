"""Trading-specific settings loaded from environment variables."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

from odyssey_algo.settings import VALID_LOG_LEVELS, _env_bool
from odyssey_algo.trading.models import ProductType, TradingMode

load_dotenv()

VALID_EXPIRY_PRESETS = frozenset({"current_week", "current_month"})
VALID_STRATEGIES = frozenset({"nifty_momentum", "atm_options"})


@dataclass(frozen=True)
class TradingSettings:
    access_token: str
    trading_mode: TradingMode
    algo_name: str
    underlying: str
    nifty_index_key: str
    option_expiry: str
    strategy_name: str
    product: ProductType
    poll_interval_sec: int
    max_open_positions: int
    max_daily_loss_inr: float
    max_order_lots: int
    momentum_threshold_points: float
    output_dir: Path
    journal_enabled: bool
    log_level: str
    log_file: Path | None
    kill_switch: bool

    @classmethod
    def from_env(cls) -> TradingSettings:
        mode_raw = os.getenv("ODYSSEY_TRADING_MODE", "paper").strip().lower()
        if mode_raw not in {m.value for m in TradingMode}:
            raise ValueError(
                f"Invalid ODYSSEY_TRADING_MODE '{mode_raw}'. Expected: paper, live"
            )

        product_raw = os.getenv("ODYSSEY_PRODUCT", "I").strip().upper()
        if product_raw not in {p.value for p in ProductType}:
            raise ValueError(f"Invalid ODYSSEY_PRODUCT '{product_raw}'. Expected: I, D")

        strategy = os.getenv("ODYSSEY_STRATEGY", "nifty_momentum").strip().lower()
        if strategy not in VALID_STRATEGIES:
            raise ValueError(
                f"Invalid ODYSSEY_STRATEGY '{strategy}'. "
                f"Expected one of: {', '.join(sorted(VALID_STRATEGIES))}"
            )

        expiry = os.getenv("ODYSSEY_OPTION_EXPIRY", "current_week").strip().lower()
        if expiry not in VALID_EXPIRY_PRESETS and len(expiry) != 10:
            raise ValueError(
                "ODYSSEY_OPTION_EXPIRY must be 'current_week', 'current_month', "
                "or a date 'yyyy-MM-dd'"
            )

        log_level = os.getenv("ODYSSEY_LOG_LEVEL", "INFO").strip().upper()
        if log_level not in VALID_LOG_LEVELS:
            raise ValueError(f"Invalid ODYSSEY_LOG_LEVEL '{log_level}'")

        log_file_raw = os.getenv("ODYSSEY_LOG_FILE", "logs/odyssey_trade.log").strip()
        log_file = Path(log_file_raw) if log_file_raw else None

        return cls(
            access_token=os.getenv("UPSTOX_ACCESS_TOKEN", "").strip(),
            trading_mode=TradingMode(mode_raw),
            algo_name=os.getenv("ODYSSEY_ALGO_NAME", "odyssey-nifty-v1").strip(),
            underlying=os.getenv("ODYSSEY_UNDERLYING", "NIFTY").strip().upper(),
            nifty_index_key=os.getenv(
                "ODYSSEY_NIFTY_INDEX_KEY", "NSE_INDEX|Nifty 50"
            ).strip(),
            option_expiry=expiry,
            strategy_name=strategy,
            product=ProductType(product_raw),
            poll_interval_sec=int(os.getenv("ODYSSEY_POLL_INTERVAL_SEC", "30")),
            max_open_positions=int(os.getenv("ODYSSEY_MAX_OPEN_POSITIONS", "2")),
            max_daily_loss_inr=float(os.getenv("ODYSSEY_MAX_DAILY_LOSS_INR", "5000")),
            max_order_lots=int(os.getenv("ODYSSEY_MAX_ORDER_LOTS", "1")),
            momentum_threshold_points=float(
                os.getenv("ODYSSEY_MOMENTUM_THRESHOLD_POINTS", "50")
            ),
            output_dir=Path(os.getenv("ODYSSEY_OUTPUT_DIR", "data")),
            journal_enabled=_env_bool("ODYSSEY_JOURNAL_ENABLED", True),
            log_level=log_level,
            log_file=log_file,
            kill_switch=_env_bool("ODYSSEY_KILL_SWITCH", False),
        )

    def validate(self) -> None:
        if not self.access_token or self.access_token == "your_upstox_access_token_here":
            raise ValueError(
                "UPSTOX_ACCESS_TOKEN is not set. Copy .env.example to .env and add your token."
            )
        if self.poll_interval_sec < 5:
            raise ValueError("ODYSSEY_POLL_INTERVAL_SEC must be >= 5")
        if self.max_open_positions < 1:
            raise ValueError("ODYSSEY_MAX_OPEN_POSITIONS must be >= 1")
        if self.max_order_lots < 1:
            raise ValueError("ODYSSEY_MAX_ORDER_LOTS must be >= 1")
        if self.max_daily_loss_inr <= 0:
            raise ValueError("ODYSSEY_MAX_DAILY_LOSS_INR must be > 0")
        if not self.algo_name:
            raise ValueError("ODYSSEY_ALGO_NAME must not be empty")
