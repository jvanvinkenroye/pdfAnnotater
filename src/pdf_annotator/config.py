"""
Configuration module for PDF Annotator.

Provides configuration classes for different environments (development, production).
"""

from __future__ import annotations

import os
import secrets
import subprocess
import sys
import warnings
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


def get_downloads_dir() -> Path:
    """
    Get platform-specific Downloads directory, used by DESKTOP_MODE exports.

    Returns:
        Path to the user's Downloads directory:
        - macOS/Windows: ~/Downloads
        - Linux: `xdg-user-dir DOWNLOAD` output if available, else ~/Downloads
    """
    if sys.platform not in ("darwin", "win32"):
        try:
            result = subprocess.run(  # noqa: S603
                ["xdg-user-dir", "DOWNLOAD"],  # noqa: S607
                capture_output=True,
                text=True,
                timeout=2,
                check=True,
            )
            xdg_path = result.stdout.strip()
            if xdg_path:
                return Path(xdg_path)
        except (OSError, subprocess.SubprocessError):
            pass

    return Path.home() / "Downloads"


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
    MAX_AI_INSTRUCTION_LENGTH = 500

    # Database settings
    DATABASE_PATH: Path | str = BASE_DIR / "data" / "annotations.db"

    # Desktop-Mode: export routes write directly to disk instead of streaming
    # an HTTP download. Needed for WebView-based desktop shells (e.g. Toga)
    # that cannot handle Content-Disposition: attachment responses. Must
    # never be enabled for server/Docker deployments.
    DESKTOP_MODE = os.environ.get("PDF_ANNOTATOR_DESKTOP_MODE") == "1"
    DESKTOP_EXPORT_DIR: Path = get_downloads_dir()

    # AI-assisted note editing (optional, disabled by default). When enabled,
    # note text and the user's instruction are sent to the configured
    # third-party provider.
    AI_PROVIDER = os.environ.get("AI_PROVIDER")  # None = feature disabled
    AI_MODEL = os.environ.get("AI_MODEL")  # None = provider default
    ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")
    OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")

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
        Config.UPLOAD_FOLDER.mkdir(parents=True, exist_ok=True)
        Config.EXPORT_FOLDER.mkdir(parents=True, exist_ok=True)
        if isinstance(Config.DATABASE_PATH, Path):
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
        if not os.environ.get("SECRET_KEY"):
            warnings.warn(
                "SECRET_KEY ist nicht gesetzt! Sessions werden nach Neustart ungültig. "
                "Setzen Sie die Umgebungsvariable SECRET_KEY für Production.",
                stacklevel=2,
            )
        ai_provider = app.config.get("AI_PROVIDER")
        if ai_provider == "anthropic" and not app.config.get("ANTHROPIC_API_KEY"):
            warnings.warn(
                "AI_PROVIDER=anthropic gesetzt, aber ANTHROPIC_API_KEY fehlt. "
                "Die KI-Funktion wird bei jeder Anfrage fehlschlagen.",
                stacklevel=2,
            )
        elif ai_provider == "openai" and not app.config.get("OPENAI_API_KEY"):
            warnings.warn(
                "AI_PROVIDER=openai gesetzt, aber OPENAI_API_KEY fehlt. "
                "Die KI-Funktion wird bei jeder Anfrage fehlschlagen.",
                stacklevel=2,
            )
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
