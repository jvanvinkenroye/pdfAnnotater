"""
Viewer route for PDF Annotator.

Handles viewer page and API endpoints for PDF rendering and annotations.
"""

from flask import Blueprint, Response, current_app, jsonify, render_template, request

from pdf_annotator.models.database import DatabaseManager
from pdf_annotator.services.pdf_processor import render_page_to_image
from pdf_annotator.utils.logger import get_logger
from pdf_annotator.utils.validators import validate_note_text, validate_page_number

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
