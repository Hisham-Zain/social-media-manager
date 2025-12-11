"""
Centralized Logging Configuration using Loguru.

Provides a pre-configured logger with:
- Console output with colors
- File rotation (10MB max, 7 days retention)
- Structured format with module names
- Intercept of standard library logging
"""

import sys
from pathlib import Path

from loguru import logger

# Remove default handler
logger.remove()

# Console handler with colors
logger.add(
    sys.stderr,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
    level="INFO",
    colorize=True,
)

# File handler with rotation
LOG_PATH = Path.home() / ".social_media_manager" / "logs"
LOG_PATH.mkdir(parents=True, exist_ok=True)

logger.add(
    LOG_PATH / "agencyos.log",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
    level="DEBUG",
    rotation="10 MB",  # Rotate when file reaches 10MB
    retention="7 days",  # Keep logs for 7 days
    compression="zip",  # Compress rotated logs
    enqueue=True,  # Thread-safe
)

# Also log to manager.log for backward compatibility
logger.add(
    "manager.log",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
    level="INFO",
    rotation="10 MB",
    retention="3 days",
)


def get_logger(name: str = None):
    """
    Get a logger bound with the given name.

    Args:
        name: Logger name (usually __name__).

    Returns:
        Loguru logger instance with bound context.
    """
    if name:
        return logger.bind(name=name)
    return logger


# Intercept standard library logging
class InterceptHandler:
    """Intercept stdlib logging and redirect to loguru."""

    def write(self, message: str) -> None:
        # Remove trailing newlines
        message = message.strip()
        if message:
            logger.opt(depth=6).info(message)

    def flush(self) -> None:
        pass


__all__ = ["logger", "get_logger"]
