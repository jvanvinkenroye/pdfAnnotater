"""
Desktop application wrapper for PDF Annotator.

Uses flaskwebgui to run Flask app in a native desktop window.
Falls back to default browser if no Chromium-based browser is found.
"""

import os
import shutil
import sys
import webbrowser
from threading import Timer

from pdf_annotator.app import create_app


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


def run_with_flaskwebgui(app: any, width: int, height: int) -> None:
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


def run_with_browser(app: any, port: int = 5123) -> None:
    """
    Run app as web server and open in default browser.

    Args:
        app: Flask application instance
        port: Port to run server on
    """
    url = f"http://127.0.0.1:{port}"

    def open_browser() -> None:
        webbrowser.open(url)

    print("Kein Chromium-Browser gefunden. Öffne Standard-Browser...")
    print(f"URL: {url}")
    print("Beenden mit Ctrl+C")

    # Open browser after short delay to let server start
    Timer(1.5, open_browser).start()

    # Run Flask server
    app.run(host="127.0.0.1", port=port, debug=False)


def run_desktop() -> None:
    """
    Run PDF Annotator as a desktop application.

    Tries to use flaskwebgui with a Chromium browser for native app experience.
    Falls back to default browser if no Chromium browser is available.

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

    # Check for Chromium browser
    browser_path = find_chromium_browser()

    if browser_path:
        # Use flaskwebgui for native app experience
        run_with_flaskwebgui(app, width, height)
    else:
        # Fallback to default browser
        run_with_browser(app)


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
