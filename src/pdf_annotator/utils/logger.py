"""
Logging module for PDF Annotator.

Provides structured logging setup with console and file output.
"""

import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path


def setup_logger(
    name: str = "pdf_annotator",
    log_level: str = "INFO",
    log_file: Path | None = None,
) -> logging.Logger:
    """
    Set up logger with console and optional file output.

    Args:
        name: Logger name
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Path to log file (optional)

    Returns:
        Configured logger instance

    Example:
        logger = setup_logger("pdf_annotator", "DEBUG", Path("app.log"))
        logger.info("Application started")
        logger.error("An error occurred", exc_info=True)
    """
    # Create logger
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, log_level.upper()))

    # Remove existing handlers to avoid duplicates
    logger.handlers.clear()

    # Create formatters
    console_formatter = logging.Formatter(
        "%(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    file_formatter = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)s | %(funcName)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG)
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)

    # File handler with rotation (if log_file specified)
    if log_file:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = RotatingFileHandler(
            log_file, maxBytes=5 * 1024 * 1024, backupCount=3
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)

    return logger


def get_logger(name: str = "pdf_annotator") -> logging.Logger:
    """
    Get existing logger or create a new one.

    Args:
        name: Logger name

    Returns:
        Logger instance

    Example:
        logger = get_logger(__name__)
        logger.info("Processing PDF")
    """
    return logging.getLogger(name)
