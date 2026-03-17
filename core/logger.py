"""
core/logger.py
--------------
Centralized Loguru logger setup.
Import `logger` from here instead of directly from loguru.
"""

import sys
from loguru import logger
from config.settings import settings

# Remove default handler
logger.remove()

# Pretty console handler
logger.add(
    sys.stderr,
    level=settings.log_level.upper(),
    format=(
        "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
        "<level>{message}</level>"
    ),
    colorize=True,
)

# (Optional) File handler – uncomment to enable persistent logs
# logger.add("logs/app.log", rotation="10 MB", retention="7 days", level="DEBUG")

__all__ = ["logger"]
