"""Shared logging setup for backend services."""

import logging
from logging import Logger


def configure_logging(level: str = "INFO") -> None:
    """Configure the application logger once for local execution."""
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )


def get_logger(name: str) -> Logger:
    """Return a namespaced logger."""
    return logging.getLogger(name)

