"""
Export route for PDF Annotator.

Handles PDF and Markdown export with downloads.
"""

from pathlib import Path
from uuid import uuid4

from flask import Blueprint, current_app, jsonify, send_file

from pdf_annotator.models.database import DatabaseManager
from pdf_annotator.services.markdown_exporter import (
    export_to_markdown,
    generate_markdown_filename,
)
from pdf_annotator.services.pdf_generator import (
    create_annotated_pdf,
    generate_annotated_filename,
)
from pdf_annotator.utils.logger import get_logger

logger = get_logger(__name__)

# Create Blueprint
export_bp = Blueprint("export", __name__, url_prefix="/export")


@export_bp.route("/original/<doc_id>", methods=["GET"])
def download_original_pdf(doc_id: str) -> any:
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
    try:
        db = DatabaseManager()
        doc_info = db.get_document(doc_id)

        if not doc_info:
            logger.warning(f"Document not found: {doc_id}")
            return jsonify({"error": "Dokument nicht gefunden"}), 404

        logger.info(f"Downloading original PDF for document {doc_id}")

        # Get file path
        file_path = Path(doc_info["file_path"])

        if not file_path.exists():
            logger.error(f"PDF file not found: {file_path}")
            return jsonify({"error": "PDF-Datei nicht gefunden"}), 404

        # Send file
        original_filename = doc_info["original_filename"]
        logger.info(f"Sending original PDF: {original_filename}")
        return send_file(
            file_path,
            as_attachment=True,
            download_name=original_filename,
            mimetype="application/pdf",
        )

    except Exception as e:
        logger.error(
            f"Error downloading original PDF for document {doc_id}: {e}",
            exc_info=True,
        )
        return jsonify({"error": "Interner Serverfehler beim Download"}), 500


@export_bp.route("/pdf/<doc_id>", methods=["POST"])
def export_pdf(doc_id: str) -> any:
    """
    Export annotated PDF.

    Creates PDF with annotations and timestamps, then sends as download.

    Args:
        doc_id: UUID of document

    Returns:
        PDF file download or error response

    Example:
        POST /export/pdf/abc-123

        Response: PDF file download
    """
    try:
        db = DatabaseManager()
        doc_info = db.get_document(doc_id)

        if not doc_info:
            logger.warning(f"Document not found: {doc_id}")
            return jsonify({"error": "Dokument nicht gefunden"}), 404

        logger.info(f"Exporting annotated PDF for document {doc_id}")

        # Generate output filename
        original_filename = doc_info["original_filename"]
        export_filename = generate_annotated_filename(original_filename)

        # Create unique temporary file path
        export_id = str(uuid4())
        export_path = (
            Path(current_app.config["EXPORT_FOLDER"]) / f"{export_id}_{export_filename}"
        )

        # Ensure export directory exists
        export_path.parent.mkdir(parents=True, exist_ok=True)

        # Generate annotated PDF
        success = create_annotated_pdf(
            doc_id,
            export_path,
            db,
            font_name=current_app.config.get("PDF_ANNOTATION_FONT", "courier"),
            font_size=current_app.config.get("PDF_ANNOTATION_FONTSIZE", 9),
            font_color=current_app.config.get("PDF_ANNOTATION_COLOR", (0, 0.5, 0)),
        )

        if not success:
            logger.error(f"Failed to create annotated PDF for {doc_id}")
            return (
                jsonify({"error": "Fehler beim Erstellen des annotierten PDFs"}),
                500,
            )

        # Send file
        logger.info(f"Sending annotated PDF: {export_filename}")
        return send_file(
            export_path,
            as_attachment=True,
            download_name=export_filename,
            mimetype="application/pdf",
        )

    except Exception as e:
        logger.error(f"Error exporting PDF for document {doc_id}: {e}", exc_info=True)
        return jsonify({"error": "Interner Serverfehler beim Export"}), 500


@export_bp.route("/markdown/<doc_id>", methods=["POST"])
def export_markdown(doc_id: str) -> any:
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
    try:
        db = DatabaseManager()
        doc_info = db.get_document(doc_id)

        if not doc_info:
            logger.warning(f"Document not found: {doc_id}")
            return jsonify({"error": "Dokument nicht gefunden"}), 404

        logger.info(f"Exporting Markdown for document {doc_id}")

        # Generate output filename
        original_filename = doc_info["original_filename"]
        export_filename = generate_markdown_filename(original_filename)

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
        return send_file(
            export_path,
            as_attachment=True,
            download_name=export_filename,
            mimetype="text/markdown",
        )

    except Exception as e:
        logger.error(
            f"Error exporting Markdown for document {doc_id}: {e}",
            exc_info=True,
        )
        return jsonify({"error": "Interner Serverfehler beim Export"}), 500
