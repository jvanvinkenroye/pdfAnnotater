"""
File response helper for PDF Annotator.

Handles the split between normal HTTP downloads (browser/server use) and
Desktop-Mode, where the server writes exports directly to disk because
WebView-based desktop shells cannot handle Content-Disposition: attachment
responses.
"""

import shutil
from pathlib import Path
from typing import Any

from flask import current_app, jsonify, send_file

from pdf_annotator.utils.logger import get_logger

logger = get_logger(__name__)


def send_file_response(path: Path, filename: str, mimetype: str) -> Any:
    """
    Send a generated file to the client.

    In DESKTOP_MODE, copies the file into the configured Downloads directory
    and returns JSON with the resulting path instead of streaming an HTTP
    download, since WebView-based desktop shells cannot process
    Content-Disposition: attachment responses.

    Args:
        path: Path to the already-generated file
        filename: Filename to present to the user
        mimetype: MIME type for the browser response (ignored in DESKTOP_MODE)

    Returns:
        Flask response: JSON with the saved path (DESKTOP_MODE) or a file
        download (default)
    """
    if current_app.config["DESKTOP_MODE"]:
        target = current_app.config["DESKTOP_EXPORT_DIR"] / filename
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.resolve() != path.resolve():
            shutil.copy(path, target)
        logger.info(f"Desktop-Mode export saved to: {target}")
        return jsonify({"success": True, "filename": filename, "path": str(target)})

    return send_file(
        path, as_attachment=True, download_name=filename, mimetype=mimetype
    )
