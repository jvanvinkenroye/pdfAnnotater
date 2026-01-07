"""
Configuration module for PDF Annotator.

Provides configuration classes for different environments (development, production).
"""

import os
from pathlib import Path


class Config:
    """
    Base configuration class.

    Contains common configuration settings for all environments.
    """

    # Project root directory
    BASE_DIR = Path(__file__).resolve().parent.parent.parent

    # Flask settings
    SECRET_KEY = os.environ.get("SECRET_KEY") or "dev-secret-key-change-in-production"
    DEBUG = False
    TESTING = False

    # Upload settings
    MAX_CONTENT_LENGTH = 50 * 1024 * 1024  # 50 MB max file size
    UPLOAD_FOLDER = BASE_DIR / "data" / "uploads"
    EXPORT_FOLDER = BASE_DIR / "data" / "exports"
    ALLOWED_EXTENSIONS = {"pdf"}

    # Database settings
    DATABASE_PATH = BASE_DIR / "data" / "annotations.db"

    # PDF rendering settings
    PDF_RENDER_DPI = 300  # DPI for PDF to image conversion
    PDF_ANNOTATION_FONTSIZE = 9
    PDF_ANNOTATION_FONT = "courier"
    PDF_ANNOTATION_COLOR = (0, 0.5, 0)  # Green in RGB 0-1 range

    # Logging
    LOG_LEVEL = "INFO"
    LOG_FILE = BASE_DIR / "data" / "app.log"

    @staticmethod
    def init_app(app: any) -> None:
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

    Disables debug mode and uses environment variables for sensitive data.
    """

    DEBUG = False
    SECRET_KEY = os.environ.get("SECRET_KEY") or None

    @staticmethod
    def init_app(app: any) -> None:
        """
        Initialize production application.

        Args:
            app: Flask application instance

        Raises:
            ValueError: If SECRET_KEY is not set
        """
        Config.init_app(app)

        # Ensure SECRET_KEY is set in production
        if not app.config.get("SECRET_KEY"):
            raise ValueError("SECRET_KEY must be set in production environment")


class TestingConfig(Config):
    """
    Testing environment configuration.

    Uses in-memory database and test-specific settings.
    """

    TESTING = True
    DEBUG = True
    DATABASE_PATH = ":memory:"  # In-memory database for tests


# Configuration dictionary
config = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "testing": TestingConfig,
    "default": DevelopmentConfig,
}
