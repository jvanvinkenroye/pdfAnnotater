"""
Flask application entry point for PDF Annotator.

Creates and configures Flask application with all routes and settings.
"""

import os
from typing import Any

from flask import Flask
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect

from pdf_annotator.config import config
from pdf_annotator.models.database import DatabaseManager
from pdf_annotator.models.user import User
from pdf_annotator.routes.admin import admin_bp
from pdf_annotator.routes.auth import auth_bp
from pdf_annotator.routes.export import export_bp
from pdf_annotator.routes.upload import upload_bp
from pdf_annotator.routes.viewer import viewer_bp
from pdf_annotator.utils.logger import setup_logger


def create_app(config_name: str | None = None) -> Flask:
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
        config_name = os.environ.get("APP_ENV", "development")

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

    # Initialize Flask-Login
    login_manager = LoginManager()
    login_manager.login_view = "auth.login"
    login_manager.login_message = "Bitte zuerst einloggen."
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id: str) -> User | None:
        """Load user from database by ID."""
        db = DatabaseManager()
        data = db.get_user_by_id(user_id)
        if data:
            return User(
                data["id"],
                data["username"],
                data["email"],
                bool(data["is_active"]),
                bool(data.get("is_admin", False)),
                data.get("theme"),
            )
        return None

    # Initialize CSRF protection
    csrf = CSRFProtect(app)

    # Exempt save_annotation from CSRF for sendBeacon support
    # (sendBeacon cannot send custom headers; endpoint validates doc_id UUID)
    csrf.exempt("pdf_annotator.routes.viewer.save_annotation")

    # Initialize rate limiter
    limiter = Limiter(
        get_remote_address,
        app=app,
        default_limits=["200 per minute"],
        storage_uri="memory://",
    )

    # Initialize database
    db = DatabaseManager(app.config["DATABASE_PATH"])
    db.init_db()
    logger.info("Database initialized")

    # Register blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(upload_bp)
    app.register_blueprint(viewer_bp)
    app.register_blueprint(export_bp)
    app.register_blueprint(admin_bp, url_prefix="/admin")

    logger.info("All blueprints registered")

    # Apply stricter rate limits to resource-intensive endpoints
    limiter.limit("5 per minute")(
        app.view_functions["auth.login_post"]
    )  # Brute-force protection
    limiter.limit("10 per minute")(app.view_functions["upload.upload_file"])
    limiter.limit("60 per minute")(app.view_functions["viewer.get_page_image"])
    limiter.limit("10 per minute")(app.view_functions["upload.import_data"])
    limiter.limit("30 per minute")(app.view_functions["auth.set_theme"])

    # Security headers
    @app.after_request
    def set_security_headers(response):
        """Add security headers to all responses."""
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: blob:; "
            "font-src 'self' data:"
        )
        return response

    # Error handlers
    @app.errorhandler(404)
    def not_found(e: Any) -> tuple:
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
    def internal_error(e: Any) -> tuple:
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
    def request_entity_too_large(e: Any) -> tuple:
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


def run_server(host: str = "0.0.0.0", port: int = 8000) -> None:
    """
    Run Gunicorn-compatible server entry point.

    Args:
        host: Host to bind to (default: 0.0.0.0)
        port: Port to bind to (default: 8000)

    Note:
        Use with Gunicorn: gunicorn --workers 4 --bind 0.0.0.0:8000 pdf_annotator.app:run_server
    """
    app = create_app("production")
    app.run(host=host, port=port, debug=False)


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
