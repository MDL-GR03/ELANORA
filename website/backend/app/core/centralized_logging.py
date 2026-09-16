"""Centralized logging system for automatic logger creation based on module names.

This module provides a way to automatically create loggers for all files in a directory
without having to manually create loggers in each file.
"""

import logging
import sys
from pathlib import Path
from typing import ClassVar

from app.core.logging import get_stream_logger

# Constants
MAX_FRAME_DEPTH = 10

# Try to import config, but don't fail if it's not available
try:
    from app.core.config import APP_NAME, LOG_LEVEL, ROOT_LOG_LEVEL

    HAS_CONFIG = True
except ImportError:
    HAS_CONFIG = False
    # Set defaults when config is not available
    APP_NAME = "elanora"
    LOG_LEVEL = "INFO"
    ROOT_LOG_LEVEL = "WARNING"


def setup_application_logging() -> None:
    """Set up application-wide logging configuration.

    This should be called once at application startup to:
    - Configure the root logger with appropriate level
    - Reduce noise from third-party libraries
    - Set consistent baseline logging behavior
    """
    root_numeric_level = getattr(logging, ROOT_LOG_LEVEL.upper(), logging.WARNING)

    logging.basicConfig(
        level=root_numeric_level,
        format="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Reduce noise from commonly verbose third-party libraries
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("requests").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)


class CentralizedLogger:
    """Centralized logging manager that automatically creates loggers based on module names."""

    _instance: ClassVar["CentralizedLogger | None"] = None
    _loggers: ClassVar[dict[str, logging.Logger]] = {}

    def __new__(cls) -> "CentralizedLogger":
        """Singleton pattern to ensure only one instance exists."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        """Initialize the centralized logger."""
        if not hasattr(self, "_initialized"):
            self._initialized = True

            self._app_name = APP_NAME

            # Setup application logging once
            setup_application_logging()

    def get_logger(self, module_name: str | None = None) -> logging.Logger:
        """Get a logger for the calling module automatically.

        Args:
            module_name: Optional module name. If not provided, will be auto-detected.

        Returns:
            Configured logger instance for the module.

        """
        if module_name is None:
            # Auto-detect the calling module
            # Go up the call stack to find the first frame outside of centralized_logging.py
            frame_depth = 1
            while frame_depth < MAX_FRAME_DEPTH:  # Safety limit
                try:
                    frame = sys._getframe(frame_depth)
                    frame_file = frame.f_globals.get("__file__", "unknown")
                    # Skip frames from this centralized_logging module
                    if "centralized_logging.py" not in frame_file:
                        module_name = self._extract_module_name(frame_file)
                        break
                    frame_depth += 1
                except ValueError:
                    # No more frames available
                    module_name = "unknown"
                    break
            else:
                module_name = "unknown"

        # Return existing logger if already created
        if module_name in self._loggers:
            return self._loggers[module_name]

        # Create new logger
        logger = self._create_module_logger(module_name)
        self._loggers[module_name] = logger
        return logger

    def _extract_module_name(self, file_path: str) -> str:
        """Extract a meaningful module name from file path."""
        if file_path == "unknown":
            return "unknown"

        path = Path(file_path)

        # Get relative path from project root
        try:
            # Find the app directory in the path
            parts = path.parts
            if "app" in parts:
                app_index = parts.index("app")
                # Take everything after 'app' directory
                module_parts = list(parts[app_index + 1 :])
                # Remove file extension and join with dots
                if module_parts:
                    module_parts[-1] = Path(module_parts[-1]).stem
                    # If we have parts after app, use them
                    if module_parts:
                        return f"{self._app_name}.{'.'.join(module_parts)}"
        except (ValueError, IndexError):
            pass

        # Fallback to just the filename without extension
        return f"{self._app_name}.{path.stem}"

    def _create_module_logger(self, module_name: str) -> logging.Logger:
        """Create a logger for a specific module."""
        return get_stream_logger(logger_name=module_name, level=LOG_LEVEL)

    def create_directory_logger(
        self, directory_path: str, logger_name: str | None = None
    ) -> logging.Logger:
        """Create a single logger for an entire directory.

        Args:
            directory_path: Path to the directory
            logger_name: Optional custom logger name

        Returns:
            Logger instance for the directory

        """
        if logger_name is None:
            dir_name = Path(directory_path).name
            logger_name = f"{self._app_name}.{dir_name}"

        if logger_name in self._loggers:
            return self._loggers[logger_name]

        logger = get_stream_logger(logger_name=logger_name, level=LOG_LEVEL)

        self._loggers[logger_name] = logger
        return logger


# Global instance
_centralized_logger = CentralizedLogger()


def get_logger(module_name: str | None = None) -> logging.Logger:
    """Get a logger for the current module. This is the main function to use.

    Usage in any file:
        from app.core.centralized_logging import get_logger
        logger = get_logger()  # Auto-detects module name
        logger.info("This is a log message")

    Args:
        module_name: Optional module name override

    Returns:
        Logger instance

    """
    return _centralized_logger.get_logger(module_name)


def get_directory_logger(
    directory_path: str, logger_name: str | None = None
) -> logging.Logger:
    """Get a single logger for an entire directory.

    Usage:
        from app.core.centralized_logging import get_directory_logger
        logger = get_directory_logger("api/v1")

    Args:
        directory_path: Path to the directory
        logger_name: Optional custom logger name

    Returns:
        Logger instance for the directory

    """
    return _centralized_logger.create_directory_logger(directory_path, logger_name)
