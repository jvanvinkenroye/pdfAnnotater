"""
Desktop application wrapper for PDF Annotator.

Uses flaskwebgui to run Flask app in a native desktop window.
Falls back to default browser if no Chromium-based browser is found.
"""

import argparse
import logging
import os
import shutil
import sys
import webbrowser
from threading import Timer
from typing import Any


def get_window_size() -> tuple[int, int]:
    """
    Get optimal window size based on screen.

    Returns:
        Tuple of (width, height) in pixels
    """
    # Default size that works well for PDF annotation
    return 1400, 900


def find_chromium_browser() -> str | None:
    """
    Find a Chromium-based browser on the system.

    Returns:
        Path to browser executable or None if not found
    """
    if sys.platform == "darwin":  # macOS
        browsers = [
            "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
            "/Applications/Chromium.app/Contents/MacOS/Chromium",
            "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
            "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser",
        ]
    elif sys.platform == "win32":  # Windows
        browsers = [
            shutil.which("chrome"),
            shutil.which("msedge"),
            shutil.which("chromium"),
        ]
    else:  # Linux
        browsers = [
            shutil.which("google-chrome"),
            shutil.which("google-chrome-stable"),
            shutil.which("chromium"),
            shutil.which("chromium-browser"),
            shutil.which("microsoft-edge"),
        ]

    for browser in browsers:
        if browser and os.path.exists(browser):
            return browser

    return None


_devnull_fd = None


def suppress_output() -> None:
    """Suppress stdout and stderr for quiet mode."""
    global _devnull_fd
    # Redirect stderr to devnull to suppress Chrome's verbose logging
    _devnull_fd = open(os.devnull, "w")  # noqa: SIM115
    sys.stderr = _devnull_fd

    # Suppress Flask/Werkzeug logging
    log = logging.getLogger("werkzeug")
    log.setLevel(logging.ERROR)

    # Suppress flaskwebgui logging
    logging.getLogger("flaskwebgui").setLevel(logging.ERROR)


def run_with_flaskwebgui(app: Any, width: int, height: int) -> None:
    """
    Run app with flaskwebgui (native window).

    Args:
        app: Flask application instance
        width: Window width in pixels
        height: Window height in pixels
    """
    from flaskwebgui import FlaskUI

    ui = FlaskUI(
        app=app,
        server="flask",
        width=width,
        height=height,
        port=5123,
    )
    ui.run()


def run_with_browser(app: Any, port: int = 5123, verbose: bool = False) -> None:
    """
    Run app as web server and open in default browser.

    Args:
        app: Flask application instance
        port: Port to run server on
        verbose: Whether to show verbose output
    """
    url = f"http://127.0.0.1:{port}"

    def open_browser() -> None:
        webbrowser.open(url)

    if verbose:
        print("Kein Chromium-Browser gefunden. Öffne Standard-Browser...")
        print(f"URL: {url}")
        print("Beenden mit Ctrl+C")

    # Open browser after short delay to let server start
    Timer(1.5, open_browser).start()

    # Run Flask server
    app.run(host="127.0.0.1", port=port, debug=False)


def run_desktop(verbose: bool = False) -> None:
    """
    Run PDF Annotator as a desktop application.

    Tries to use flaskwebgui with a Chromium browser for native app experience.
    Falls back to default browser if no Chromium browser is available.

    Args:
        verbose: Whether to show verbose output

    Data is stored in platform-specific directories:
    - macOS: ~/Library/Application Support/PDF-Annotator/
    - Linux: ~/.local/share/pdf-annotator/
    """
    # Suppress output unless verbose mode
    if not verbose:
        suppress_output()

    # Use production config for installed desktop app (platform-specific paths)
    os.environ.setdefault("APP_ENV", "production")

    # Import here to avoid logging before suppress_output
    from pdf_annotator.app import create_app

    # Create Flask app
    app = create_app()

    # Get window dimensions
    width, height = get_window_size()

    # Check for Chromium browser
    browser_path = find_chromium_browser()

    if browser_path:
        # Use flaskwebgui for native app experience
        run_with_flaskwebgui(app, width, height)
    else:
        # Fallback to default browser
        run_with_browser(app, verbose=verbose)


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="PDF Annotator - PDF annotation tool with side-by-side view"
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Show verbose output including browser and server logs",
    )
    return parser.parse_args()


def main() -> None:
    """Entry point for desktop application."""
    args = parse_args()

    try:
        run_desktop(verbose=args.verbose)
    except KeyboardInterrupt:
        print("\nPDF Annotator beendet.")
        sys.exit(0)
    except Exception as e:
        print(f"Fehler beim Starten: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
