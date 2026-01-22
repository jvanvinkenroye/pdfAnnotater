"""
Desktop application wrapper for PDF Annotator.

Uses flaskwebgui to run Flask app in a native desktop window.
"""

import os
import sys

from flaskwebgui import FlaskUI

from pdf_annotator.app import create_app


def get_window_size() -> tuple[int, int]:
    """
    Get optimal window size based on screen.

    Returns:
        Tuple of (width, height) in pixels
    """
    # Default size that works well for PDF annotation
    return 1400, 900


def run_desktop() -> None:
    """
    Run PDF Annotator as a desktop application.

    Creates a Flask app and wraps it in a native window using flaskwebgui.
    The browser chrome is hidden and the app appears as a standalone application.

    Data is stored in platform-specific directories:
    - macOS: ~/Library/Application Support/PDF-Annotator/
    - Linux: ~/.local/share/pdf-annotator/
    """
    # Use production config for installed desktop app (platform-specific paths)
    os.environ.setdefault("FLASK_ENV", "production")

    # Create Flask app
    app = create_app()

    # Get window dimensions
    width, height = get_window_size()

    # Create desktop UI wrapper
    ui = FlaskUI(
        app=app,
        server="flask",
        width=width,
        height=height,
        # Use a specific port to avoid conflicts
        port=5123,
        # Custom window title
        # browser_path can be set to use specific browser
    )

    # Run the desktop application
    ui.run()


def main() -> None:
    """Entry point for desktop application."""
    try:
        run_desktop()
    except KeyboardInterrupt:
        print("\nPDF Annotator beendet.")
        sys.exit(0)
    except Exception as e:
        print(f"Fehler beim Starten: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
