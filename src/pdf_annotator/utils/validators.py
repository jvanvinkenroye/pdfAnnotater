"""
Validation module for PDF Annotator.

Provides file and input validation functions.
"""

import re
from pathlib import Path

from werkzeug.datastructures import FileStorage

from pdf_annotator.utils.logger import get_logger

logger = get_logger(__name__)


UUID_PATTERN = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    re.IGNORECASE,
)


def validate_doc_id(doc_id: str) -> tuple[bool, str | None]:
    """
    Validate that doc_id is a valid UUID format.

    Args:
        doc_id: Document ID to validate

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not doc_id or not UUID_PATTERN.match(doc_id):
        return False, "Ungültige Dokument-ID"
    return True, None


def allowed_file(filename: str, allowed_extensions: set) -> bool:
    """
    Check if filename has allowed extension.

    Args:
        filename: Name of file to check
        allowed_extensions: Set of allowed extensions (e.g., {"pdf"})

    Returns:
        bool: True if extension is allowed, False otherwise

    Example:
        if allowed_file("document.pdf", {"pdf"}):
            print("Valid file type")
    """
    return "." in filename and filename.rsplit(".", 1)[1].lower() in allowed_extensions


def validate_uploaded_file(
    file: FileStorage, max_size: int, allowed_extensions: set
) -> tuple[bool, str | None]:
    """
    Validate uploaded file.

    Checks:
    - File is not None
    - Filename is not empty
    - Extension is allowed
    - File size is within limit

    Args:
        file: Werkzeug FileStorage object
        max_size: Maximum file size in bytes
        allowed_extensions: Set of allowed extensions

    Returns:
        Tuple of (is_valid, error_message)
        - (True, None) if valid
        - (False, error_message) if invalid

    Example:
        is_valid, error = validate_uploaded_file(
            file,
            max_size=50*1024*1024,
            allowed_extensions={"pdf"}
        )
        if not is_valid:
            return jsonify({"error": error}), 400
    """
    # Check if file exists
    if not file:
        return False, "Keine Datei hochgeladen"

    # Check if filename exists
    if not file.filename or file.filename == "":
        return False, "Dateiname ist leer"

    # Check file extension
    if not allowed_file(file.filename, allowed_extensions):
        return False, f"Nur {', '.join(allowed_extensions)} Dateien erlaubt"

    # Check file size (by seeking to end)
    file.seek(0, 2)  # Seek to end
    file_size = file.tell()
    file.seek(0)  # Reset to beginning

    if file_size > max_size:
        max_size_mb = max_size / (1024 * 1024)
        return False, f"Datei zu groß (max. {max_size_mb:.0f} MB)"

    if file_size == 0:
        return False, "Datei ist leer"

    logger.info(f"File validation passed: {file.filename} ({file_size} bytes)")
    return True, None


def sanitize_filename(filename: str) -> str:
    """
    Sanitize filename by removing dangerous characters while preserving Unicode.

    Args:
        filename: Original filename

    Returns:
        str: Sanitized filename

    Example:
        safe_name = sanitize_filename("../../../etc/passwd.pdf")
        # Returns: "passwd.pdf"
    """
    # Get just the filename, not the path
    filename = Path(filename).name

    # Remove dangerous characters
    dangerous_chars = ["<", ">", ":", '"', "/", "\\", "|", "?", "*"]
    for char in dangerous_chars:
        filename = filename.replace(char, "_")

    return filename


def validate_page_number(page_number: int, max_pages: int) -> tuple[bool, str | None]:
    """
    Validate page number is within valid range.

    Args:
        page_number: Page number to validate (1-indexed)
        max_pages: Maximum number of pages in document

    Returns:
        Tuple of (is_valid, error_message)

    Example:
        is_valid, error = validate_page_number(5, 10)
        if not is_valid:
            return jsonify({"error": error}), 400
    """
    if page_number < 1:
        return False, "Seitenzahl muss mindestens 1 sein"

    if page_number > max_pages:
        return False, f"Seitenzahl darf nicht größer als {max_pages} sein"

    return True, None


def validate_note_text(
    note_text: str, max_length: int = 5000
) -> tuple[bool, str | None]:
    """
    Validate annotation note text.

    Args:
        note_text: Note text to validate
        max_length: Maximum allowed length (default: 5000)

    Returns:
        Tuple of (is_valid, error_message)

    Example:
        is_valid, error = validate_note_text(note, max_length=5000)
        if not is_valid:
            return jsonify({"error": error}), 400
    """
    if not isinstance(note_text, str):
        return False, "Notiz muss ein Text sein"

    if len(note_text) > max_length:
        return False, f"Notiz zu lang (max. {max_length} Zeichen)"

    return True, None


def validate_file_type(filename: str) -> tuple[bool, str | None]:
    """
    Validate that file is a PDF.

    Args:
        filename: Name of file to validate

    Returns:
        Tuple of (is_valid, error_message)

    Example:
        is_valid, error = validate_file_type("document.pdf")
        if not is_valid:
            return jsonify({"error": error}), 400
    """
    if not allowed_file(filename, {"pdf"}):
        return False, "Nur PDF-Dateien erlaubt"

    return True, None


def validate_file_size(file_size: int, max_size: int) -> tuple[bool, str | None]:
    """
    Validate file size is within limit.

    Args:
        file_size: Size of file in bytes
        max_size: Maximum allowed size in bytes

    Returns:
        Tuple of (is_valid, error_message)

    Example:
        is_valid, error = validate_file_size(file_size, 50*1024*1024)
        if not is_valid:
            return jsonify({"error": error}), 400
    """
    if file_size == 0:
        return False, "Datei ist leer"

    if file_size > max_size:
        max_size_mb = max_size / (1024 * 1024)
        return False, f"Datei zu groß (max. {max_size_mb:.0f} MB)"

    return True, None


def validate_file_path(file_path: Path, base_dir: Path) -> tuple[bool, str | None]:
    """
    Validate that file path is within the allowed base directory.

    Prevents path traversal attacks by ensuring the resolved path
    is a subdirectory of the base directory.

    Args:
        file_path: Path to validate
        base_dir: Base directory that file must be within

    Returns:
        Tuple of (is_valid, error_message)

    Example:
        is_valid, error = validate_file_path(
            Path("uploads/file.pdf"),
            Path("/app/data/uploads")
        )
        if not is_valid:
            logger.error(f"Path traversal attempt: {error}")
            return jsonify({"error": "Ungültiger Dateipfad"}), 400
    """
    try:
        # Resolve both paths to absolute paths
        resolved_file = file_path.resolve()
        resolved_base = base_dir.resolve()

        # Check if file path is relative to base directory
        # is_relative_to() raises ValueError if not relative
        if not resolved_file.is_relative_to(resolved_base):
            logger.warning(
                f"Path traversal attempt: {file_path} is not within {base_dir}"
            )
            return False, "Dateipfad liegt außerhalb des erlaubten Verzeichnisses"

        return True, None

    except (ValueError, RuntimeError, OSError) as e:
        logger.error(f"Error validating file path: {e}")
        return False, "Ungültiger Dateipfad"
