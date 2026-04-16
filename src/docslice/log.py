"""Logging configuration for docslice.

Every module does:
    from docslice.log import get_logger
    logger = get_logger(__name__)

Entrypoints call setup_logging() once at startup.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

LOG_DIR = Path.home() / ".docslice"
LOG_FILE = LOG_DIR / "docslice.log"

FILE_FMT = "%(asctime)s  %(levelname)-8s  %(name)s  %(message)s"
CONSOLE_FMT = "%(message)s"
VERBOSE_CONSOLE_FMT = "%(levelname)-8s  %(name)s  %(message)s"


def get_logger(name: str) -> logging.Logger:
    """Return a child logger under the 'docslice' hierarchy."""
    return logging.getLogger(name)


def setup_logging(
    *,
    level: str = "INFO",
    log_to_file: bool = True,
    verbose: bool = False,
    quiet: bool = False,
) -> None:
    """Configure the 'docslice' root logger. Call ONCE from entrypoints.

    Args:
        level: Base log level (DEBUG, INFO, WARNING, ERROR, CRITICAL).
        log_to_file: Write to ~/.docslice/docslice.log.
        verbose: Console shows logger name + level prefix.
        quiet: Console level is WARNING (suppresses INFO).
    """
    root = logging.getLogger("docslice")
    root.setLevel(getattr(logging, level.upper(), logging.INFO))
    root.handlers.clear()

    console = logging.StreamHandler(sys.stderr)
    console_level = logging.WARNING if quiet else root.level
    console.setLevel(console_level)
    console_fmt = VERBOSE_CONSOLE_FMT if verbose else CONSOLE_FMT
    console.setFormatter(logging.Formatter(console_fmt))
    root.addHandler(console)

    if log_to_file:
        try:
            LOG_DIR.mkdir(parents=True, exist_ok=True)
            fh = logging.FileHandler(LOG_FILE, encoding="utf-8", mode="a")
            fh.setLevel(logging.DEBUG)
            fh.setFormatter(logging.Formatter(FILE_FMT))
            root.addHandler(fh)
        except OSError:
            console.setLevel(logging.DEBUG)
            root.warning(
                "Could not create log file at %s - console only",
                LOG_FILE,
            )
