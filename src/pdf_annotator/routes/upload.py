"""
Upload route for PDF Annotator.

Handles PDF file uploads, validation, and storage.
"""

from pathlib import Path
from typing import Any
from uuid import uuid4

from flask import (
    Blueprint,
    current_app,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    send_file,
    url_for,
)
from flask_login import current_user, login_required

from pdf_annotator.models.database import DatabaseManager
from pdf_annotator.services.pdf_processor import get_page_count, validate_pdf
from pdf_annotator.utils.logger import get_logger
from pdf_annotator.utils.validators import (
    sanitize_filename,
    validate_doc_id,
    validate_uploaded_file,
)

logger = get_logger(__name__)

# Create Blueprint
upload_bp = Blueprint("upload", __name__)


@upload_bp.route("/", methods=["GET"])
@login_required
def index() -> str:
    """
    Render upload page.

    Returns:
        str: Rendered HTML template
    """
    return render_template("index.html")


@upload_bp.route("/documents", methods=["GET"])
@login_required
def list_documents() -> str:
    """
    Render document list page.

    Shows all uploaded documents for current user with metadata.

    Returns:
        str: Rendered HTML template
    """
    db = DatabaseManager()
    documents = db.get_all_documents(current_user.id)

    logger.info(f"Listing {len(documents)} documents for user {current_user.username}")

    return render_template("documents.html", documents=documents)


@upload_bp.route("/upload", methods=["POST"])
@login_required
def upload_file() -> Any:
    """
    Handle PDF file upload.

    Validates file, saves to uploads directory, and creates database entry for current user.

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
        storage_id = str(uuid4())
        file_extension = Path(original_filename).suffix
        storage_filename = f"{storage_id}{file_extension}"
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

        # Truncate metadata to configured max lengths
        max_name = current_app.config.get("MAX_NAME_LENGTH", 100)
        max_title = current_app.config.get("MAX_TITLE_LENGTH", 200)
        max_year = current_app.config.get("MAX_YEAR_LENGTH", 4)
        max_subject = current_app.config.get("MAX_SUBJECT_LENGTH", 200)
        first_name = first_name[:max_name]
        last_name = last_name[:max_name]
        title = title[:max_title]
        year = year[:max_year]
        subject = subject[:max_subject]

        # Create database entry
        db = DatabaseManager()
        doc_id = db.create_document(
            current_user.id,
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


@upload_bp.route("/delete/<doc_id>", methods=["DELETE"])
@login_required
def delete_document(doc_id: str) -> Any:
    """
    Delete document, annotations, and PDF file for current user.

    Args:
        doc_id: UUID of document to delete

    Returns:
        JSON response with success/error message

    Example:
        DELETE /delete/abc-123
        Response: {"success": true}
    """
    try:
        is_valid, error_msg = validate_doc_id(doc_id)
        if not is_valid:
            return jsonify({"error": error_msg}), 400

        db = DatabaseManager()

        # Get document info to access file path
        doc_info = db.get_document(doc_id)

        if not doc_info:
            logger.warning(f"Delete attempt for non-existent document: {doc_id}")
            return jsonify({"error": "Dokument nicht gefunden"}), 404

        # Check ownership
        if doc_info.get("user_id") != current_user.id:
            logger.warning(
                f"Unauthorized delete attempt: user {current_user.id} tried to delete "
                f"document owned by {doc_info.get('user_id')}"
            )
            return jsonify({"error": "Nicht berechtigt"}), 403

        # Delete from database first (CASCADE deletes annotations)
        # This prevents data loss if database deletion fails
        success = db.delete_document(doc_id)

        if not success:
            logger.error(f"Failed to delete document from database: {doc_id}")
            return jsonify({"error": "Fehler beim Löschen aus der Datenbank"}), 500

        # Only delete file after successful database deletion
        file_path = Path(doc_info["file_path"])
        if file_path.exists():
            try:
                file_path.unlink()
                logger.info(f"Deleted file: {file_path}")
            except OSError as e:
                logger.warning(
                    f"File deletion failed but DB entry removed: {file_path}, {e}"
                )
                # Continue - file can be cleaned up later
        else:
            logger.warning(f"File not found during deletion: {file_path}")

        logger.info(f"Document deleted: {doc_id}")
        return jsonify({"success": True, "message": "Dokument erfolgreich gelöscht"})

    except Exception as e:
        logger.error(f"Error deleting document {doc_id}: {e}", exc_info=True)
        return jsonify({"error": "Interner Serverfehler beim Löschen"}), 500


@upload_bp.route("/export", methods=["GET"])
@login_required
def export_data() -> Any:
    """
    Export all user's documents and annotations as ZIP archive.

    Returns:
        ZIP file download

    Example:
        GET /export
        Response: PDF_Annotator_Backup_20260123.zip
    """
    try:
        from pdf_annotator.services.data_manager import DataManager

        db = DatabaseManager()
        upload_folder = Path(current_app.config["UPLOAD_FOLDER"])
        manager = DataManager(upload_folder)

        # Get user's documents
        user_docs = db.get_all_documents(current_user.id)
        doc_ids = [doc["id"] for doc in user_docs]

        # Create export
        zip_path = manager.export_data(doc_ids)

        logger.info(f"Data exported to: {zip_path}")

        # Send file and delete after
        return send_file(
            zip_path,
            mimetype="application/zip",
            as_attachment=True,
            download_name=zip_path.name,
        )

    except Exception as e:
        logger.error(f"Export failed: {e}", exc_info=True)
        return jsonify({"error": "Fehler beim Exportieren der Daten"}), 500


@upload_bp.route("/export/info", methods=["GET"])
@login_required
def export_info() -> Any:
    """
    Get information about current user's data for export.

    Returns:
        JSON with document count, annotation count, estimated size

    Example:
        GET /export/info
        Response: {"document_count": 5, "annotation_count": 42, "estimated_size_mb": 12.5}
    """
    try:
        from pdf_annotator.services.data_manager import DataManager

        db = DatabaseManager()
        upload_folder = Path(current_app.config["UPLOAD_FOLDER"])
        manager = DataManager(upload_folder)

        # Get user's documents
        user_docs = db.get_all_documents(current_user.id)
        doc_ids = [doc["id"] for doc in user_docs]

        info = manager.get_export_info(doc_ids)
        return jsonify(info)

    except Exception as e:
        logger.error(f"Export info failed: {e}", exc_info=True)
        return jsonify({"error": "Fehler beim Abrufen der Export-Informationen"}), 500


@upload_bp.route("/import", methods=["POST"])
@login_required
def import_data() -> Any:
    """
    Import data from ZIP archive and associate with current user.

    Request:
        - Form data with 'file' field containing ZIP backup

    Returns:
        JSON with import statistics

    Example:
        POST /import
        Response: {"documents_imported": 5, "annotations_imported": 42}
    """
    try:
        from pdf_annotator.services.data_manager import DataManager

        # Check if file is in request
        if "file" not in request.files:
            return jsonify({"error": "Keine Datei gefunden"}), 400

        file = request.files["file"]

        if not file.filename:
            return jsonify({"error": "Keine Datei ausgewählt"}), 400

        if not file.filename.lower().endswith(".zip"):
            return jsonify({"error": "Nur ZIP-Dateien werden akzeptiert"}), 400

        # Save to temp location
        import tempfile

        with tempfile.NamedTemporaryFile(delete=False, suffix=".zip") as tmp:
            file.save(tmp.name)
            tmp_path = Path(tmp.name)

        try:
            upload_folder = Path(current_app.config["UPLOAD_FOLDER"])
            manager = DataManager(upload_folder)

            # Import data and assign to current user
            stats = manager.import_data(tmp_path, current_user.id)

            logger.info(
                f"Data imported: {stats['documents_imported']} docs, "
                f"{stats['annotations_imported']} annotations"
            )

            return jsonify(
                {
                    "success": True,
                    "message": f"{stats['documents_imported']} Dokumente und "
                    f"{stats['annotations_imported']} Notizen importiert",
                    **stats,
                }
            )

        finally:
            # Clean up temp file
            tmp_path.unlink(missing_ok=True)

    except ValueError as e:
        logger.warning(f"Import validation failed: {e}")
        error_msg = str(e)
        # Provide user-friendly error messages
        if "nicht gefunden" in error_msg.lower():
            error_msg = "Ungültiges Backup-Format: metadata.json fehlt"
        elif "corrupted" in error_msg.lower() or "json" in error_msg.lower():
            error_msg = "Backup-Datei ist beschädigt oder ungültig"
        elif "version" in error_msg.lower():
            error_msg = f"Inkompatible Backup-Version: {error_msg}"
        return jsonify({"error": error_msg}), 400
    except Exception as e:
        logger.error(f"Import failed: {e}", exc_info=True)
        return jsonify(
            {"error": f"Fehler beim Importieren: {str(e)[:100]}"}
        ), 500
