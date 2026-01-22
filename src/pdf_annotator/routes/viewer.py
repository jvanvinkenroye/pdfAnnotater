"""
Viewer route for PDF Annotator.

Handles viewer page and API endpoints for PDF rendering and annotations.
"""

from pathlib import Path

from flask import Blueprint, Response, current_app, jsonify, render_template, request

from pdf_annotator.models.database import DatabaseManager
from pdf_annotator.services.pdf_processor import get_page_count, render_page_to_image
from pdf_annotator.utils.logger import get_logger
from pdf_annotator.utils.validators import (
    validate_file_size,
    validate_file_type,
    validate_note_text,
    validate_page_number,
)

logger = get_logger(__name__)

# Create Blueprint
viewer_bp = Blueprint("viewer", __name__, url_prefix="/viewer")


@viewer_bp.route("/<doc_id>", methods=["GET"])
def view_document(doc_id: str) -> any:
    """
    Render viewer page for document.

    Args:
        doc_id: UUID of document

    Returns:
        Rendered HTML template or error response

    Example:
        GET /viewer/abc-123-def-456
    """
    try:
        db = DatabaseManager()
        doc_info = db.get_document(doc_id)

        if not doc_info:
            logger.warning(f"Document not found: {doc_id}")
            return render_template(
                "error.html",
                error_title="Dokument nicht gefunden",
                error_message=f"Das Dokument mit ID {doc_id} wurde nicht gefunden.",
            ), 404

        logger.info(f"Viewing document: {doc_id} ({doc_info['original_filename']})")

        return render_template(
            "viewer.html",
            doc_id=doc_id,
            original_filename=doc_info["original_filename"],
            page_count=doc_info["page_count"],
            first_name=doc_info.get("first_name", ""),
            last_name=doc_info.get("last_name", ""),
            title=doc_info.get("title", ""),
            year=doc_info.get("year", ""),
            subject=doc_info.get("subject", ""),
        )

    except Exception as e:
        logger.error(f"Error viewing document {doc_id}: {e}", exc_info=True)
        return render_template(
            "error.html",
            error_title="Serverfehler",
            error_message="Beim Laden des Dokuments ist ein Fehler aufgetreten.",
        ), 500


@viewer_bp.route("/api/page/<doc_id>/<int:page_number>", methods=["GET"])
def get_page_image(doc_id: str, page_number: int) -> Response:
    """
    Render PDF page as PNG image.

    Args:
        doc_id: UUID of document
        page_number: Page number (1-indexed)

    Returns:
        PNG image or error response

    Example:
        GET /viewer/api/page/abc-123/1
    """
    try:
        db = DatabaseManager()
        doc_info = db.get_document(doc_id)

        if not doc_info:
            logger.warning(f"Document not found: {doc_id}")
            return jsonify({"error": "Dokument nicht gefunden"}), 404

        # Validate page number
        is_valid, error_msg = validate_page_number(page_number, doc_info["page_count"])
        if not is_valid:
            logger.warning(f"Invalid page number {page_number} for document {doc_id}")
            return jsonify({"error": error_msg}), 400

        # Render page
        dpi = current_app.config.get("PDF_RENDER_DPI", 300)
        image_bytes = render_page_to_image(doc_info["file_path"], page_number, dpi=dpi)

        if image_bytes is None:
            logger.error(f"Failed to render page {page_number} of document {doc_id}")
            return jsonify({"error": "Fehler beim Rendern der Seite"}), 500

        # Return PNG image
        return Response(image_bytes, mimetype="image/png")

    except Exception as e:
        logger.error(
            f"Error rendering page {page_number} of {doc_id}: {e}",
            exc_info=True,
        )
        return jsonify({"error": "Interner Serverfehler"}), 500


@viewer_bp.route("/api/annotation/<doc_id>/<int:page_number>", methods=["GET"])
def get_annotation(doc_id: str, page_number: int) -> any:
    """
    Get annotation for specific page.

    Args:
        doc_id: UUID of document
        page_number: Page number (1-indexed)

    Returns:
        JSON with annotation data or error response

    Example:
        GET /viewer/api/annotation/abc-123/1

        Response:
        {
            "note_text": "This is a note",
            "updated_at": "2026-01-07 20:45:00"
        }
    """
    try:
        db = DatabaseManager()
        doc_info = db.get_document(doc_id)

        if not doc_info:
            logger.warning(f"Document not found: {doc_id}")
            return jsonify({"error": "Dokument nicht gefunden"}), 404

        # Validate page number
        is_valid, error_msg = validate_page_number(page_number, doc_info["page_count"])
        if not is_valid:
            logger.warning(f"Invalid page number {page_number} for document {doc_id}")
            return jsonify({"error": error_msg}), 400

        # Get annotation
        annotation = db.get_annotation(doc_id, page_number)

        if annotation:
            return jsonify(
                {
                    "note_text": annotation["note_text"],
                    "updated_at": str(annotation["updated_at"]),
                }
            )
        else:
            # Return empty annotation
            return jsonify({"note_text": "", "updated_at": None})

    except Exception as e:
        logger.error(
            f"Error getting annotation for page {page_number} of {doc_id}: {e}",
            exc_info=True,
        )
        return jsonify({"error": "Interner Serverfehler"}), 500


@viewer_bp.route("/api/annotation/<doc_id>/<int:page_number>", methods=["POST"])
def save_annotation(doc_id: str, page_number: int) -> any:
    """
    Save or update annotation for specific page.

    Args:
        doc_id: UUID of document
        page_number: Page number (1-indexed)

    Request Body:
        {
            "note_text": "Annotation text"
        }

    Returns:
        JSON with success status or error response

    Example:
        POST /viewer/api/annotation/abc-123/1
        Body: {"note_text": "This is a note"}

        Response:
        {
            "success": true,
            "updated_at": "2026-01-07 20:45:00"
        }
    """
    try:
        db = DatabaseManager()
        doc_info = db.get_document(doc_id)

        if not doc_info:
            logger.warning(f"Document not found: {doc_id}")
            return jsonify({"error": "Dokument nicht gefunden"}), 404

        # Validate page number
        is_valid, error_msg = validate_page_number(page_number, doc_info["page_count"])
        if not is_valid:
            logger.warning(f"Invalid page number {page_number} for document {doc_id}")
            return jsonify({"error": error_msg}), 400

        # Get note text from request
        data = request.get_json()
        if not data:
            logger.warning("No JSON data in request")
            return jsonify({"error": "Keine Daten gesendet"}), 400

        note_text = data.get("note_text", "")

        # Validate note text
        is_valid, error_msg = validate_note_text(note_text)
        if not is_valid:
            logger.warning(f"Invalid note text: {error_msg}")
            return jsonify({"error": error_msg}), 400

        # Save annotation
        db.upsert_annotation(doc_id, page_number, note_text)

        # Get updated annotation to return timestamp
        annotation = db.get_annotation(doc_id, page_number)

        logger.info(f"Saved annotation for page {page_number} of document {doc_id}")

        return jsonify({"success": True, "updated_at": str(annotation["updated_at"])})

    except Exception as e:
        logger.error(
            f"Error saving annotation for page {page_number} of {doc_id}: {e}",
            exc_info=True,
        )
        return jsonify({"error": "Interner Serverfehler"}), 500


@viewer_bp.route("/api/metadata/<doc_id>", methods=["POST"])
def update_metadata(doc_id: str) -> any:
    """
    Update document metadata.

    Args:
        doc_id: UUID of document

    Returns:
        JSON response with success status

    Example:
        POST /viewer/api/metadata/abc-123
        Body: {"first_name": "Max", "last_name": "Mustermann", ...}
    """
    try:
        db = DatabaseManager()
        doc_info = db.get_document(doc_id)

        if not doc_info:
            logger.warning(f"Document not found: {doc_id}")
            return jsonify({"error": "Dokument nicht gefunden"}), 404

        # Get metadata from request
        data = request.get_json()
        if not data:
            logger.warning("No JSON data in request")
            return jsonify({"error": "Keine Daten gesendet"}), 400

        # Extract metadata fields
        first_name = data.get("first_name", "").strip()
        last_name = data.get("last_name", "").strip()
        title = data.get("title", "").strip()
        year = data.get("year", "").strip()
        subject = data.get("subject", "").strip()

        # Validate input lengths
        if len(first_name) > current_app.config["MAX_NAME_LENGTH"]:
            return (
                jsonify(
                    {
                        "error": f"Vorname zu lang (max. {current_app.config['MAX_NAME_LENGTH']} Zeichen)"
                    }
                ),
                400,
            )
        if len(last_name) > current_app.config["MAX_NAME_LENGTH"]:
            return (
                jsonify(
                    {
                        "error": f"Nachname zu lang (max. {current_app.config['MAX_NAME_LENGTH']} Zeichen)"
                    }
                ),
                400,
            )
        if len(title) > current_app.config["MAX_TITLE_LENGTH"]:
            return (
                jsonify(
                    {
                        "error": f"Titel zu lang (max. {current_app.config['MAX_TITLE_LENGTH']} Zeichen)"
                    }
                ),
                400,
            )
        if len(year) > current_app.config["MAX_YEAR_LENGTH"]:
            return (
                jsonify(
                    {
                        "error": f"Jahr zu lang (max. {current_app.config['MAX_YEAR_LENGTH']} Zeichen)"
                    }
                ),
                400,
            )
        if len(subject) > current_app.config["MAX_SUBJECT_LENGTH"]:
            return (
                jsonify(
                    {
                        "error": f"Thema zu lang (max. {current_app.config['MAX_SUBJECT_LENGTH']} Zeichen)"
                    }
                ),
                400,
            )

        # Update metadata in database
        success = db.update_document_metadata(
            doc_id, first_name, last_name, title, year, subject
        )

        if not success:
            logger.error(f"Failed to update metadata for document {doc_id}")
            return (
                jsonify({"error": "Fehler beim Aktualisieren der Metadaten"}),
                500,
            )

        logger.info(f"Updated metadata for document {doc_id}")

        return jsonify({"success": True})

    except Exception as e:
        logger.error(
            f"Error updating metadata for document {doc_id}: {e}",
            exc_info=True,
        )
        return jsonify({"error": "Interner Serverfehler"}), 500


@viewer_bp.route("/api/replace/<doc_id>", methods=["POST"])
def replace_pdf(doc_id: str) -> any:
    """
    Replace existing PDF with a new version.

    Keeps all annotations and metadata, updates page count.

    Args:
        doc_id: UUID of document

    Returns:
        JSON response with success status and new page count

    Example:
        POST /viewer/api/replace/abc-123
        File: new_version.pdf
    """
    try:
        db = DatabaseManager()
        doc_info = db.get_document(doc_id)

        if not doc_info:
            logger.warning(f"Document not found: {doc_id}")
            return jsonify({"error": "Dokument nicht gefunden"}), 404

        # Check if file was uploaded
        if "file" not in request.files:
            logger.warning("No file in request")
            return jsonify({"error": "Keine Datei hochgeladen"}), 400

        file = request.files["file"]

        if file.filename == "":
            logger.warning("Empty filename")
            return jsonify({"error": "Kein Dateiname"}), 400

        # Validate file type
        is_valid, error_msg = validate_file_type(file.filename)
        if not is_valid:
            logger.warning(f"Invalid file type: {file.filename}")
            return jsonify({"error": error_msg}), 400

        # Validate file size
        file.seek(0, 2)  # Seek to end
        file_size = file.tell()
        file.seek(0)  # Reset to beginning

        is_valid, error_msg = validate_file_size(
            file_size, current_app.config["MAX_CONTENT_LENGTH"]
        )
        if not is_valid:
            logger.warning(f"File too large: {file_size} bytes")
            return jsonify({"error": error_msg}), 400

        logger.info(f"Replacing PDF for document {doc_id}")

        # Get file path
        file_path = Path(doc_info["file_path"])

        # Save new file (overwrites old one)
        file.save(file_path)
        logger.info(f"Saved new PDF to: {file_path}")

        # Get new page count
        new_page_count = get_page_count(str(file_path))
        logger.info(f"New PDF has {new_page_count} pages")

        # Update page count in database
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE documents SET page_count = ? WHERE id = ?",
                (new_page_count, doc_id),
            )

        logger.info(f"Successfully replaced PDF for document {doc_id}")

        return jsonify({"success": True, "page_count": new_page_count})

    except Exception as e:
        logger.error(
            f"Error replacing PDF for document {doc_id}: {e}",
            exc_info=True,
        )
        return jsonify({"error": "Interner Serverfehler"}), 500
