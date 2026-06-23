"""Configuration management using Pydantic Settings."""

from pydantic_settings import BaseSettings
from typing import Optional


class DatabaseSettings(BaseSettings):
    """Database configuration."""

    host: str = "localhost"
    port: int = 5432
    db: str = "odyssey_trading"
    user: str = "postgres"
    password: str = "postgres"
    echo: bool = False

    @property
    def database_url(self) -> str:
        """Construct PostgreSQL connection URL."""
        return f"postgresql+psycopg2://{self.user}:{self.password}@{self.host}:{self.port}/{self.db}"

    @property
    def async_database_url(self) -> str:
        """Construct async PostgreSQL connection URL."""
        return f"postgresql+asyncpg://{self.user}:{self.password}@{self.host}:{self.port}/{self.db}"

    class Config:
        env_prefix = "POSTGRES_"
        case_sensitive = False


class UpstoxSettings(BaseSettings):
    """Upstox API configuration."""

    api_key: str
    access_token: str

    class Config:
        env_prefix = "UPSTOX_"
        case_sensitive = False


class MarketSettings(BaseSettings):
    """Market configuration."""

    market_open_time: str = "09:15"  # IST
    market_close_time: str = "15:30"  # IST
    atm_check_interval: int = 60  # seconds
    instrument_master_refresh_time: str = "09:00"  # IST
    instrument_master_refresh_day: int = 0  # Monday
    timezone: str = "Asia/Kolkata"
    stream_mode: str = "full"  # full, ltpc, ltp, snapshot


class WebSocketSettings(BaseSettings):
    """WebSocket configuration."""

    max_reconnect_attempts: int = 10
    initial_reconnect_delay: int = 1  # seconds
    max_reconnect_delay: int = 60  # seconds
    heartbeat_interval: int = 30  # seconds
    heartbeat_timeout: int = 60  # seconds


class LoggingSettings(BaseSettings):
    """Logging configuration."""

    level: str = "INFO"
    format: str = "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"
    log_dir: str = "logs"
    log_file: str = "trading_system.log"
    rotation: str = "500 MB"
    retention: str = "7 days"


class Settings(BaseSettings):
    """Main application settings."""

    debug: bool = False
    app_name: str = "Odyssey Trading System"
    version: str = "1.0.0"

    # Sub-settings
    database: DatabaseSettings = DatabaseSettings()
    upstox: UpstoxSettings = UpstoxSettings()
    market: MarketSettings = MarketSettings()
    websocket: WebSocketSettings = WebSocketSettings()
    logging: LoggingSettings = LoggingSettings()

    class Config:
        env_file = ".env"
        case_sensitive = False


# Global settings instance
settings = Settings()
