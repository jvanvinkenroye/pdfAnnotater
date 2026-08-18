"""
Experimental Toga/Briefcase desktop entry point for PDF Annotator.

Hosts the real Flask app in a background thread and displays it in a
native toga.WebView (WKWebView on macOS) — same principle as the
flaskwebgui client (desktop.py), but without requiring an installed
Chrome. Sets DESKTOP_MODE (exports written to ~/Downloads, since
WKWebView can't handle Content-Disposition: attachment) and
DESKTOP_AUTO_LOGIN (no login screen for the local single-user case).

See ref/packaging-briefcase-evaluation.md for the full evaluation.
"""

import os
import socket
import threading
import time
from pathlib import Path

from pdf_annotator.utils.logger import get_logger

logger = get_logger(__name__)

HOST = "127.0.0.1"


def _find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((HOST, 0))
        return int(s.getsockname()[1])


def _wait_for_port(port: int, timeout: float = 15.0) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            with socket.create_connection((HOST, port), timeout=0.5):
                return True
        except OSError:
            time.sleep(0.1)
    return False


def _run_flask(port: int) -> None:
    from pdf_annotator.app import create_app

    app = create_app()
    app.run(host=HOST, port=port, use_reloader=False, threaded=True)


def main() -> None:
    """Start the Flask app in a thread and open it in a Toga WebView."""
    # Must be set before create_app() reads the config
    os.environ.setdefault("APP_ENV", "production")
    os.environ.setdefault("PDF_ANNOTATOR_DESKTOP_MODE", "1")
    os.environ.setdefault("PDF_ANNOTATOR_DESKTOP_AUTO_LOGIN", "1")

    try:
        import toga
    except ImportError as e:
        raise SystemExit(
            "Toga ist nicht installiert. Installation mit: "
            "uv sync --extra toga (oder: uv tool install '.[toga]')"
        ) from e

    port = _find_free_port()

    class PdfAnnotatorApp(toga.App):
        def startup(self) -> None:
            flask_thread = threading.Thread(
                target=_run_flask, args=(port,), daemon=True
            )
            flask_thread.start()

            if not _wait_for_port(port):
                raise SystemExit("Flask-Server ist nicht gestartet (Timeout)")

            window = toga.MainWindow(title="PDF Annotator", size=(1400, 900))
            window.content = toga.WebView(url=f"http://{HOST}:{port}/")
            self.main_window = window
            window.show()

    # Pass the icon as a path (without extension — Toga resolves the
    # platform-preferred format); constructing toga.Icon() here directly
    # would fail because the App singleton doesn't exist yet.
    icon_path = Path(__file__).parent / "resources" / "pdfannotator"

    PdfAnnotatorApp(
        formal_name="PDF Annotator",
        app_id="de.vanvinkenroye.pdfannotator",
        icon=str(icon_path),
    ).main_loop()


if __name__ == "__main__":
    main()
