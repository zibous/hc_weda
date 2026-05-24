# -*- coding: utf-8 -*-
"""
Logging Setup
==============
Zentraler Logger mit Rotating File Handler.
Unterstuetzt Console und File Logging.
"""

import logging
import os
from logging.handlers import RotatingFileHandler


def setup_logger(name: str) -> logging.Logger:
    """Erstellt einen konfigurierten Logger."""
    logger = logging.getLogger(name)

    key = os.getenv("LOG_LEVEL", "INFO").strip().upper()
    level = getattr(logging, key, logging.INFO)
    logger.setLevel(level)

    logger.propagate = False
    if logger.hasHandlers():
        logger.handlers.clear()

    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s (%(filename)s:%(lineno)d): %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    if os.getenv("LOG_MODE", "console") == "file":
        os.makedirs("logs", exist_ok=True)
        handler = RotatingFileHandler(
            os.getenv("LOG_FILE", "logs/app.log"),
            maxBytes=int(os.getenv("LOG_MAX_BYTES", 1_000_000)),
            backupCount=int(os.getenv("LOG_BACKUP_COUNT", 3)),
            encoding="utf-8",
        )
    else:
        handler = logging.StreamHandler()

    handler.setFormatter(formatter)
    logger.addHandler(handler)

    return logger
