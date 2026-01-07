"""
Flask application entry point for PDF Annotator.

Creates and configures Flask application with all routes and settings.
"""

import os

from flask import Flask

from pdf_annotator.config import config
from pdf_annotator.models.database import DatabaseManager
from pdf_annotator.routes.export import export_bp
from pdf_annotator.routes.upload import upload_bp
from pdf_annotator.routes.viewer import viewer_bp
from pdf_annotator.utils.logger import setup_logger


def create_app(config_name: str = None) -> Flask:
    """
    Application factory for creating Flask app.

    Args:
        config_name: Configuration name (development, production, testing)
                    If None, uses FLASK_ENV environment variable or defaults to 'development'

    Returns:
        Flask: Configured Flask application instance

    Example:
        app = create_app('development')
        app.run(debug=True)
    """
    # Determine config
    if config_name is None:
        config_name = os.environ.get("FLASK_ENV", "development")

    # Create Flask app
    app = Flask(__name__, template_folder="templates", static_folder="static")

    # Load configuration
    app.config.from_object(config[config_name])
    config[config_name].init_app(app)

    # Setup logging
    logger = setup_logger(
        name="pdf_annotator",
        log_level=app.config["LOG_LEVEL"],
        log_file=app.config["LOG_FILE"],
    )

    logger.info(f"Starting PDF Annotator in {config_name} mode")

    # Initialize database
    db = DatabaseManager(app.config["DATABASE_PATH"])
    db.init_db()
    logger.info("Database initialized")

    # Register blueprints
    app.register_blueprint(upload_bp)
    app.register_blueprint(viewer_bp)
    app.register_blueprint(export_bp)

    logger.info("All blueprints registered")

    # Error handlers
    @app.errorhandler(404)
    def not_found(e: any) -> tuple:
        """Handle 404 errors."""
        from flask import render_template

        return (
            render_template(
                "error.html",
                error_title="Seite nicht gefunden",
                error_message="Die angeforderte Seite wurde nicht gefunden.",
            ),
            404,
        )

    @app.errorhandler(500)
    def internal_error(e: any) -> tuple:
        """Handle 500 errors."""
        from flask import render_template

        logger.error(f"Internal server error: {e}", exc_info=True)
        return (
            render_template(
                "error.html",
                error_title="Serverfehler",
                error_message="Ein interner Serverfehler ist aufgetreten.",
            ),
            500,
        )

    @app.errorhandler(413)
    def request_entity_too_large(e: any) -> tuple:
        """Handle file too large errors."""
        from flask import render_template

        max_size_mb = app.config["MAX_CONTENT_LENGTH"] / (1024 * 1024)
        return (
            render_template(
                "error.html",
                error_title="Datei zu groß",
                error_message=f"Die hochgeladene Datei überschreitet die maximale Größe von {max_size_mb:.0f} MB.",
            ),
            413,
        )

    return app


if __name__ == "__main__":
    # Create app
    app = create_app()

    # Get port from environment variable or use default
    port = int(os.environ.get("FLASK_RUN_PORT", 5000))

    # Run development server
    app.run(
        host="127.0.0.1",
        port=port,
        debug=app.config["DEBUG"],
    )
