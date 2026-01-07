"""
Upload route for PDF Annotator.

Handles PDF file uploads, validation, and storage.
"""

from pathlib import Path
from uuid import uuid4

from flask import (
    Blueprint,
    current_app,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    url_for,
)

from pdf_annotator.models.database import DatabaseManager
from pdf_annotator.services.pdf_processor import get_page_count, validate_pdf
from pdf_annotator.utils.logger import get_logger
from pdf_annotator.utils.validators import sanitize_filename, validate_uploaded_file

logger = get_logger(__name__)

# Create Blueprint
upload_bp = Blueprint("upload", __name__)


@upload_bp.route("/", methods=["GET"])
def index() -> str:
    """
    Render upload page.

    Returns:
        str: Rendered HTML template
    """
    return render_template("index.html")


@upload_bp.route("/documents", methods=["GET"])
def list_documents() -> str:
    """
    Render document list page.

    Shows all uploaded documents with metadata.

    Returns:
        str: Rendered HTML template
    """
    db = DatabaseManager()
    documents = db.get_all_documents()

    logger.info(f"Listing {len(documents)} documents")

    return render_template("documents.html", documents=documents)


@upload_bp.route("/upload", methods=["POST"])
def upload_file() -> any:
    """
    Handle PDF file upload.

    Validates file, saves to uploads directory, and creates database entry.

    Request:
        - Form data with 'file' field containing PDF

    Returns:
        - On success: Redirect to viewer page
        - On error: JSON error response with 400 status

    Example:
        curl -F "file=@document.pdf" http://localhost:5000/upload
    """
    try:
        # Check if file is in request
        if "file" not in request.files:
            logger.warning("Upload attempt without file")
            return jsonify({"error": "Keine Datei gefunden"}), 400

        file = request.files["file"]

        # Validate file
        is_valid, error_msg = validate_uploaded_file(
            file,
            max_size=current_app.config["MAX_CONTENT_LENGTH"],
            allowed_extensions=current_app.config["ALLOWED_EXTENSIONS"],
        )

        if not is_valid:
            logger.warning(f"File validation failed: {error_msg}")
            return jsonify({"error": error_msg}), 400

        # Sanitize original filename
        original_filename = sanitize_filename(file.filename)
        logger.info(f"Processing upload: {original_filename}")

        # Generate unique filename for storage
        doc_id = str(uuid4())
        file_extension = Path(original_filename).suffix
        storage_filename = f"{doc_id}{file_extension}"
        storage_path = Path(current_app.config["UPLOAD_FOLDER"]) / storage_filename

        # Save file
        storage_path.parent.mkdir(parents=True, exist_ok=True)
        file.save(str(storage_path))
        logger.info(f"File saved to: {storage_path}")

        # Validate PDF
        if not validate_pdf(storage_path):
            # Clean up invalid file
            storage_path.unlink()
            logger.error(f"Invalid PDF file: {original_filename}")
            return (
                jsonify(
                    {
                        "error": "Ungültige PDF-Datei. Bitte versuchen Sie eine andere Datei."
                    }
                ),
                400,
            )

        # Get page count
        try:
            page_count = get_page_count(storage_path)
            logger.info(f"PDF has {page_count} pages")
        except Exception as e:
            # Clean up file
            storage_path.unlink()
            logger.error(f"Failed to get page count: {e}")
            return (
                jsonify(
                    {
                        "error": "Fehler beim Lesen der PDF-Datei. Ist die Datei beschädigt?"
                    }
                ),
                400,
            )

        # Get metadata from form
        first_name = request.form.get("first_name", "").strip()
        last_name = request.form.get("last_name", "").strip()
        title = request.form.get("title", "").strip()
        year = request.form.get("year", "").strip()
        subject = request.form.get("subject", "").strip()

        # Create database entry
        db = DatabaseManager()
        doc_id = db.create_document(
            original_filename,
            str(storage_path),
            page_count,
            first_name,
            last_name,
            title,
            year,
            subject,
        )

        # Initialize empty annotations for all pages
        for page_num in range(1, page_count + 1):
            db.upsert_annotation(doc_id, page_num, "")

        logger.info(f"Document created: {doc_id} with {page_count} pages")

        # Return success response with redirect URL
        # For AJAX requests, return JSON
        if request.headers.get("Accept") == "application/json":
            return jsonify(
                {
                    "success": True,
                    "doc_id": doc_id,
                    "page_count": page_count,
                    "redirect_url": url_for("viewer.view_document", doc_id=doc_id),
                }
            )

        # For regular form submit, redirect
        flash(f"PDF erfolgreich hochgeladen: {original_filename}", "success")
        return redirect(url_for("viewer.view_document", doc_id=doc_id))

    except Exception as e:
        logger.error(f"Upload failed: {e}", exc_info=True)
        return jsonify({"error": "Interner Serverfehler beim Upload"}), 500
