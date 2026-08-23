"""
Export route for PDF Annotator.

Handles PDF and Markdown export with downloads.
"""

import json
import time
from pathlib import Path
from typing import Any
from uuid import uuid4

from flask import Blueprint, abort, current_app, jsonify
from flask_login import current_user, login_required

from pdf_annotator.models.database import get_db
from pdf_annotator.routes._helpers import get_owned_document, handle_errors
from pdf_annotator.services.jobs import submit_job
from pdf_annotator.services.markdown_exporter import (
    export_to_markdown,
    generate_markdown_filename,
)
from pdf_annotator.services.pdf_generator import (
    create_annotated_pdf,
    generate_annotated_filename,
)
from pdf_annotator.utils.downloads import send_file_response
from pdf_annotator.utils.logger import get_logger
from pdf_annotator.utils.validators import validate_file_path

logger = get_logger(__name__)

# Create Blueprint
export_bp = Blueprint("export", __name__, url_prefix="/export")

# Max age for export files before cleanup (1 hour)
EXPORT_MAX_AGE_SECONDS = 3600


def cleanup_old_exports() -> None:
    """Remove export files older than EXPORT_MAX_AGE_SECONDS."""
    try:
        export_folder = Path(current_app.config["EXPORT_FOLDER"])
        if not export_folder.exists():
            return

        now = time.time()
        for file_path in export_folder.iterdir():
            if file_path.is_file():
                age = now - file_path.stat().st_mtime
                if age > EXPORT_MAX_AGE_SECONDS:
                    file_path.unlink(missing_ok=True)
                    logger.debug("Cleaned up old export: %s", file_path.name)
    except Exception as e:
        logger.warning(f"Export cleanup failed: {e}")


@export_bp.route("/original/<doc_id>", methods=["GET"])
@login_required
@handle_errors("Interner Serverfehler beim Download")
def download_original_pdf(doc_id: str) -> Any:
    """
    Download original PDF file.

    Sends the original uploaded PDF file as download.

    Args:
        doc_id: UUID of document

    Returns:
        PDF file download or error response

    Example:
        GET /export/original/abc-123

        Response: Original PDF file download
    """
    doc_info = get_owned_document(doc_id)

    logger.info(f"Downloading original PDF for document {doc_id}")

    # Get file path
    file_path = Path(doc_info["file_path"])

    # Validate path to prevent path traversal attacks
    upload_folder = Path(current_app.config["UPLOAD_FOLDER"])
    is_valid, error_msg = validate_file_path(file_path, upload_folder)
    if not is_valid:
        logger.error(f"Path traversal attempt blocked: {file_path}")
        return jsonify({"error": "Ungültiger Dateipfad"}), 400

    if not file_path.exists():
        logger.error(f"PDF file not found: {file_path}")
        return jsonify({"error": "PDF-Datei nicht gefunden"}), 404

    # Send file
    original_filename = doc_info["original_filename"]
    logger.info(f"Sending original PDF: {original_filename}")
    return send_file_response(file_path, original_filename, "application/pdf")


@export_bp.route("/pdf/<doc_id>", methods=["POST"])
@login_required
@handle_errors("Interner Serverfehler beim Export")
def export_pdf(doc_id: str) -> Any:
    """
    Export annotated PDF.

    The 300-DPI export runs as a background job: the response is 202 with
    a job_id to poll via GET /viewer/api/jobs/<job_id>; the finished file
    is fetched from GET /export/download/<job_id>.

    Args:
        doc_id: UUID of document

    Returns:
        JSON with job_id (202) or error response

    Example:
        POST /export/pdf/abc-123

        Response: {"success": true, "job_id": "..."}
    """
    doc_info = get_owned_document(doc_id)

    db = get_db()

    logger.info(f"Exporting annotated PDF for document {doc_id}")

    # Clean up old export files before creating new ones
    cleanup_old_exports()

    # Get last edited timestamp from annotations
    annotations = db.get_all_annotations(doc_id)
    last_edited = None
    if annotations:
        # Find the most recent updated_at timestamp
        last_edited = max(ann["updated_at"] for ann in annotations)

    # Generate output filename with metadata
    export_filename = generate_annotated_filename(doc_info, last_edited)

    # Create unique temporary file path
    export_id = str(uuid4())
    export_path = (
        Path(current_app.config["EXPORT_FOLDER"]) / f"{export_id}_{export_filename}"
    )

    # Ensure export directory exists
    export_path.parent.mkdir(parents=True, exist_ok=True)

    # Config values captured now — the runner must not touch current_app.
    font_name = current_app.config.get("PDF_ANNOTATION_FONT", "courier")
    font_size = current_app.config.get("PDF_ANNOTATION_FONTSIZE", 9)
    font_color = current_app.config.get("PDF_ANNOTATION_COLOR", (0, 0.5, 0))

    def runner() -> dict[str, Any]:
        success = create_annotated_pdf(
            doc_id,
            export_path,
            db,
            font_name=font_name,
            font_size=font_size,
            font_color=font_color,
        )
        if not success:
            raise RuntimeError("Fehler beim Erstellen des annotierten PDFs")
        return {"result_path": str(export_path), "filename": export_filename}

    job_id = submit_job(db, "export_pdf", doc_id, current_user.id, runner)

    return jsonify({"success": True, "job_id": job_id}), 202


@export_bp.route("/download/<job_id>", methods=["GET"])
@login_required
@handle_errors("Interner Serverfehler beim Download")
def download_job_result(job_id: str) -> Any:
    """
    Download the artifact produced by a finished export job.

    Args:
        job_id: UUID of the export job

    Returns:
        File download (or Desktop-Mode JSON), 409 while the job is still
        running, 404 for unknown jobs or vanished artifacts.
    """
    db = get_db()
    job = db.get_job(job_id)

    if not job:
        abort(404, description="Job nicht gefunden")
    if job["user_id"] != current_user.id:
        abort(403, description="Nicht berechtigt")
    if job["status"] != "done" or not job["result_path"]:
        return jsonify({"error": "Export ist noch nicht fertig"}), 409

    file_path = Path(job["result_path"])
    if not file_path.is_file():
        return jsonify({"error": "Exportdatei nicht mehr vorhanden"}), 404

    result = json.loads(job["result_json"] or "{}")
    filename = result.get("filename", file_path.name)
    return send_file_response(file_path, filename, "application/pdf")


@export_bp.route("/markdown/<doc_id>", methods=["POST"])
@login_required
@handle_errors("Interner Serverfehler beim Export")
def export_markdown(doc_id: str) -> Any:
    """
    Export annotations as Markdown.

    Creates Markdown file with all annotations and sends as download.

    Args:
        doc_id: UUID of document

    Returns:
        Markdown file download or error response

    Example:
        POST /export/markdown/abc-123

        Response: Markdown file download
    """
    doc_info = get_owned_document(doc_id)

    db = get_db()

    logger.info(f"Exporting Markdown for document {doc_id}")

    # Clean up old export files before creating new ones
    cleanup_old_exports()

    # Get last edited timestamp from annotations
    annotations = db.get_all_annotations(doc_id)
    last_edited = None
    if annotations:
        # Find the most recent updated_at timestamp
        last_edited = max(ann["updated_at"] for ann in annotations)

    # Generate output filename with metadata
    export_filename = generate_markdown_filename(doc_info, last_edited)

    # Create unique temporary file path
    export_id = str(uuid4())
    export_path = (
        Path(current_app.config["EXPORT_FOLDER"]) / f"{export_id}_{export_filename}"
    )

    # Ensure export directory exists
    export_path.parent.mkdir(parents=True, exist_ok=True)

    # Generate Markdown
    success = export_to_markdown(doc_id, export_path, db)

    if not success:
        logger.error(f"Failed to create Markdown export for {doc_id}")
        return (
            jsonify({"error": "Fehler beim Erstellen der Markdown-Datei"}),
            500,
        )

    # Send file
    logger.info(f"Sending Markdown file: {export_filename}")
    return send_file_response(export_path, export_filename, "text/markdown")
