"""
Configuration module for PDF Annotator.

Provides configuration classes for different environments (development, production).
"""

from __future__ import annotations

import os
import secrets
import sys
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from flask import Flask


def get_data_dir() -> Path:
    """
    Get platform-specific data directory following OS conventions.

    Returns:
        Path to application data directory:
        - macOS: ~/Library/Application Support/PDF-Annotator/
        - Linux: ~/.local/share/pdf-annotator/
        - Windows: %APPDATA%/PDF-Annotator/
    """
    app_name = "PDF-Annotator"

    if sys.platform == "darwin":  # macOS
        base = Path.home() / "Library" / "Application Support"
    elif sys.platform == "win32":  # Windows
        base = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
    else:  # Linux and others (XDG spec)
        xdg_default = str(Path.home() / ".local" / "share")
        xdg_data = os.environ.get("XDG_DATA_HOME", xdg_default)
        base = Path(xdg_data)

    return base / app_name


class Config:
    """
    Base configuration class.

    Contains common configuration settings for all environments.
    """

    # Project root directory
    BASE_DIR = Path(__file__).resolve().parent.parent.parent

    # Flask settings
    # Generate random secret key for development if not set
    SECRET_KEY = os.environ.get("SECRET_KEY") or secrets.token_hex(32)
    DEBUG = False
    TESTING = False

    # Upload settings
    MAX_CONTENT_LENGTH = 50 * 1024 * 1024  # 50 MB max file size
    UPLOAD_FOLDER = BASE_DIR / "data" / "uploads"
    EXPORT_FOLDER = BASE_DIR / "data" / "exports"
    ALLOWED_EXTENSIONS = {"pdf"}

    # Input validation limits
    MAX_FILENAME_LENGTH = 255
    MAX_NAME_LENGTH = 100  # For first/last name
    MAX_TITLE_LENGTH = 200
    MAX_YEAR_LENGTH = 4
    MAX_SUBJECT_LENGTH = 200
    MAX_NOTE_LENGTH = 5000

    # Database settings
    DATABASE_PATH = BASE_DIR / "data" / "annotations.db"

    # PDF rendering settings
    PDF_RENDER_DPI = 150  # DPI for browser preview (lower = faster)
    PDF_EXPORT_DPI = 300  # DPI for PDF export (higher = better quality)
    PDF_ANNOTATION_FONTSIZE = 9
    PDF_ANNOTATION_FONT = "courier"
    PDF_ANNOTATION_COLOR = (0, 0.5, 0)  # Green in RGB 0-1 range

    # Logging
    LOG_LEVEL = "INFO"
    LOG_FILE = BASE_DIR / "data" / "app.log"

    @staticmethod
    def init_app(app: Flask) -> None:
        """
        Initialize application with configuration.

        Args:
            app: Flask application instance
        """
        # Ensure required directories exist
        Config.UPLOAD_FOLDER.mkdir(parents=True, exist_ok=True)
        Config.EXPORT_FOLDER.mkdir(parents=True, exist_ok=True)
        Config.DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)


class DevelopmentConfig(Config):
    """
    Development environment configuration.

    Enables debug mode and verbose logging.
    """

    DEBUG = True
    LOG_LEVEL = "DEBUG"


class ProductionConfig(Config):
    """
    Production environment configuration.

    Uses platform-specific data directories and environment variables.
    """

    DEBUG = False
    SECRET_KEY = os.environ.get("SECRET_KEY") or secrets.token_hex(32)

    # Use platform-specific data directory
    DATA_DIR = get_data_dir()
    UPLOAD_FOLDER = DATA_DIR / "uploads"
    EXPORT_FOLDER = DATA_DIR / "exports"
    DATABASE_PATH = DATA_DIR / "annotations.db"
    LOG_FILE = DATA_DIR / "app.log"

    @staticmethod
    def init_app(app: Flask) -> None:
        """
        Initialize production application.

        Args:
            app: Flask application instance
        """
        # Use ProductionConfig paths, not base Config
        app.config["UPLOAD_FOLDER"].mkdir(parents=True, exist_ok=True)
        app.config["EXPORT_FOLDER"].mkdir(parents=True, exist_ok=True)
        app.config["DATABASE_PATH"].parent.mkdir(parents=True, exist_ok=True)


class TestingConfig(Config):
    """
    Testing environment configuration.

    Uses in-memory database and test-specific settings.
    """

    TESTING = True
    DEBUG = True
    DATABASE_PATH = ":memory:"  # In-memory database for tests
    WTF_CSRF_ENABLED = False  # Disable CSRF for test client


# Configuration dictionary
config = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "testing": TestingConfig,
    "default": DevelopmentConfig,
}
