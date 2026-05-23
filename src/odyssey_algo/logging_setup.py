"""Logging configuration."""

from __future__ import annotations

import logging
from pathlib import Path

_CONFIGURED = False


def setup_logging(level: str, log_file: Path | None) -> logging.Logger:
    """Configure application logging once and return the package logger."""
    global _CONFIGURED

    logger = logging.getLogger("odyssey_algo")
    if _CONFIGURED:
        return logger

    numeric_level = getattr(logging, level.upper(), logging.INFO)
    logger.setLevel(numeric_level)

    formatter = logging.Formatter("[%(asctime)s] [%(levelname)s] %(message)s")

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)

    if log_file is not None:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    _CONFIGURED = True
    return logger
