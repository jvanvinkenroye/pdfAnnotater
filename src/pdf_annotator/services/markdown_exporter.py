"""
Markdown Exporter module for PDF Annotator.

Exports annotations to Markdown format with timestamps and page numbers.
"""

from datetime import datetime
from pathlib import Path

from pdf_annotator.models.database import DatabaseManager
from pdf_annotator.utils.logger import get_logger

logger = get_logger(__name__)


def format_timestamp(dt: datetime) -> str:
    """
    Format datetime to [YYYY-MM-DD HH:mm] format.

    Args:
        dt: Datetime object

    Returns:
        str: Formatted timestamp

    Example:
        ts = format_timestamp(datetime.now())
        # Returns: "[2026-01-07 20:45]"
    """
    return dt.strftime("[%Y-%m-%d %H:%M]")


def export_to_markdown(doc_id: str, output_path: Path, db: DatabaseManager) -> bool:
    """
    Export all annotations to Markdown file.

    Creates a Markdown document with:
    - Document title (original filename)
    - Annotations grouped by page number
    - Each annotation with timestamp

    Format:
        # Notizen zu <filename>

        ## Seite 1 - [2026-01-07 20:45]
        <note_text>

        ## Seite 3 - [2026-01-07 20:47]
        <note_text>

    Args:
        doc_id: UUID of document
        output_path: Path where Markdown file will be saved
        db: DatabaseManager instance

    Returns:
        bool: True if successful, False otherwise

    Example:
        db = DatabaseManager()
        success = export_to_markdown(
            "abc-123",
            Path("notes.md"),
            db
        )
    """
    try:
        logger.info(f"Exporting annotations to Markdown for document {doc_id}")

        # Get document info
        doc_info = db.get_document(doc_id)
        if not doc_info:
            logger.error(f"Document {doc_id} not found")
            return False

        # Get all annotations
        annotations = db.get_all_annotations(doc_id)

        # Filter out empty annotations
        annotations = [ann for ann in annotations if ann["note_text"].strip()]

        logger.info(f"Exporting {len(annotations)} non-empty annotations to Markdown")

        # Build Markdown content
        lines = []

        # Title
        original_filename = doc_info["original_filename"]
        lines.append(f"# Notizen zu {original_filename}")
        lines.append("")

        if not annotations:
            lines.append("_Keine Notizen vorhanden._")
        else:
            # Add each annotation
            for ann in annotations:
                page_number = ann["page_number"]
                note_text = ann["note_text"]
                updated_at = ann["updated_at"]

                # Convert to datetime and format timestamp
                if isinstance(updated_at, str):
                    # Parse string timestamp from database
                    updated_dt = datetime.strptime(updated_at, "%Y-%m-%d %H:%M:%S")
                else:
                    updated_dt = updated_at

                timestamp = format_timestamp(updated_dt)

                # Add annotation section
                lines.append(f"## Seite {page_number} - {timestamp}")
                lines.append("")
                lines.append(note_text.strip())
                lines.append("")

        # Join lines
        markdown_content = "\n".join(lines)

        # Ensure output directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Write to file
        output_path.write_text(markdown_content, encoding="utf-8")

        logger.info(f"Successfully exported to Markdown: {output_path}")
        return True

    except Exception as e:
        logger.error(f"Failed to export to Markdown: {e}")
        return False


def generate_markdown_filename(doc_info: dict, last_edited: str | None = None) -> str:
    """
    Generate filename for Markdown export based on metadata.

    Format: NachnameVornameZuletztbearbeitet_notizen.md

    Args:
        doc_info: Document info dict with metadata (last_name, first_name)
        last_edited: Last edited timestamp (YYYY-MM-DD HH:MM:SS format)

    Returns:
        str: New filename with metadata and "_notizen.md" suffix

    Example:
        doc_info = {"last_name": "Mustermann", "first_name": "Max", ...}
        new_name = generate_markdown_filename(doc_info, "2026-01-08 00:05:00")
        # Returns: "MustermannMax2026-01-08_notizen.md"
    """
    # Extract metadata
    last_name = doc_info.get("last_name", "").strip()
    first_name = doc_info.get("first_name", "").strip()

    # Format last edited date (YYYY-MM-DD)
    date_str = ""
    if last_edited:
        try:
            # Convert to string if it's a datetime object
            if isinstance(last_edited, datetime):
                date_str = last_edited.strftime("%Y-%m-%d")
            else:
                # It's already a string, extract date part
                date_str = str(last_edited)[:10]
        except (ValueError, AttributeError, TypeError):
            date_str = ""

    # Build filename parts
    parts = []
    if last_name:
        parts.append(last_name)
    if first_name:
        parts.append(first_name)
    if date_str:
        parts.append(date_str)

    # If no metadata, fall back to original filename
    if not parts:
        stem = Path(doc_info.get("original_filename", "document")).stem
        return f"{stem}_notizen.md"

    # Combine parts
    filename = "".join(parts) + "_notizen.md"

    # Sanitize filename - remove invalid characters
    invalid_chars = ['<', '>', ':', '"', '/', '\\', '|', '?', '*']
    for char in invalid_chars:
        filename = filename.replace(char, '_')

    return filename
