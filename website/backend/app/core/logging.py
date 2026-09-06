"""Process-wide console logging helpers.

Application processes emit logs to stderr. Container runtimes and service
managers own collection, rotation, retention, and export.
"""

import logging
import os

LOG_FORMAT = (
    "%(asctime)s | %(name)s | %(levelname)-8s | "
    "%(module)s.%(funcName)s:%(lineno)d | %(message)s"
)
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def get_stream_logger(logger_name: str, level: str | None = None) -> logging.Logger:
    """Return an idempotently configured stderr logger."""
    configured_level = (level or os.getenv("LOG_LEVEL", "INFO")).upper()
    numeric_level = getattr(logging, configured_level, logging.INFO)
    logger = logging.getLogger(logger_name)

    if logger.handlers:
        logger.setLevel(numeric_level)
        return logger

    console_level = os.getenv("CONSOLE_LOG_LEVEL", configured_level).upper()
    console_numeric_level = getattr(logging, console_level, numeric_level)
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT))
    handler.setLevel(console_numeric_level)
    logger.addHandler(handler)
    logger.setLevel(numeric_level)
    logger.propagate = False
    return logger
