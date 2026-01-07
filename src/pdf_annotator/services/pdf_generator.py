"""
PDF Generator module for PDF Annotator.

Creates annotated PDFs with timestamps and formatted notes.
"""

from datetime import datetime
from pathlib import Path

import fitz  # PyMuPDF

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


def calculate_footer_rect(page_rect: fitz.Rect, footer_height: float = 80) -> fitz.Rect:
    """
    Calculate rectangle for footer area where annotations will be placed.

    Args:
        page_rect: Page rectangle (from page.rect)
        footer_height: Height of footer in points (default: 80)

    Returns:
        fitz.Rect: Footer rectangle with margins

    Example:
        page_rect = page.rect
        footer = calculate_footer_rect(page_rect, 80)
    """
    margin = 10
    return fitz.Rect(
        margin,  # x0 (left)
        page_rect.height - footer_height,  # y0 (top of footer)
        page_rect.width - margin,  # x1 (right)
        page_rect.height - margin,  # y1 (bottom)
    )


def add_annotation_to_page(
    page: fitz.Page,
    note_text: str,
    timestamp: str,
    font_name: str = "courier",
    font_size: float = 9,
    font_color: tuple[float, float, float] = (0, 0.5, 0),
    background_color: tuple[float, float, float] = (1, 1, 0.9),
) -> bool:
    """
    Add annotation text to PDF page footer.

    Args:
        page: PyMuPDF page object
        note_text: Annotation text content
        timestamp: Formatted timestamp string
        font_name: Font name (default: "courier")
        font_size: Font size in points (default: 9)
        font_color: RGB color tuple (0-1 range, default: green)
        background_color: RGB background color (0-1 range, default: light yellow)

    Returns:
        bool: True if successful, False otherwise

    Example:
        success = add_annotation_to_page(
            page,
            "This is a note",
            "[2026-01-07 20:45]"
        )
    """
    try:
        page_rect = page.rect
        footer_rect = calculate_footer_rect(page_rect)

        # Draw background rectangle for better readability
        page.draw_rect(
            footer_rect,
            color=background_color,
            fill=background_color,
            width=0.5,
        )

        # Combine timestamp and note text
        full_text = f"{timestamp}\n{note_text}"

        # Insert text into footer
        page.insert_textbox(
            footer_rect,
            full_text,
            fontsize=font_size,
            fontname=font_name,
            color=font_color,
            align=0,  # Left-aligned
        )

        logger.debug(f"Added annotation to page {page.number + 1}")
        return True

    except Exception as e:
        logger.error(f"Failed to add annotation to page {page.number + 1}: {e}")
        return False


def create_annotated_pdf(
    doc_id: str,
    output_path: Path,
    db: DatabaseManager,
    font_name: str = "courier",
    font_size: float = 9,
    font_color: tuple[float, float, float] = (0, 0.5, 0),
) -> bool:
    """
    Create annotated PDF with all notes from database.

    Loads original PDF, adds annotations to pages with notes,
    and saves to output path.

    Args:
        doc_id: UUID of document
        output_path: Path where annotated PDF will be saved
        db: DatabaseManager instance
        font_name: Font for annotations (default: "courier")
        font_size: Font size in points (default: 9)
        font_color: RGB color tuple (0-1 range, default: green)

    Returns:
        bool: True if successful, False otherwise

    Example:
        db = DatabaseManager()
        success = create_annotated_pdf(
            "abc-123",
            Path("output_annotated.pdf"),
            db
        )
    """
    try:
        logger.info(f"Creating annotated PDF for document {doc_id}")

        # Get document info
        doc_info = db.get_document(doc_id)
        if not doc_info:
            logger.error(f"Document {doc_id} not found")
            return False

        # Get all annotations
        annotations = db.get_all_annotations(doc_id)
        logger.info(f"Found {len(annotations)} annotations")

        # Open original PDF
        original_path = Path(doc_info["file_path"])
        if not original_path.exists():
            logger.error(f"Original PDF not found: {original_path}")
            return False

        pdf_doc = fitz.open(str(original_path))

        # Add annotations to respective pages
        annotation_count = 0
        for ann in annotations:
            page_number = ann["page_number"]
            note_text = ann["note_text"]
            updated_at = ann["updated_at"]

            # Skip empty notes
            if not note_text.strip():
                continue

            # Convert to datetime and format timestamp
            if isinstance(updated_at, str):
                # Parse string timestamp from database
                updated_dt = datetime.strptime(updated_at, "%Y-%m-%d %H:%M:%S")
            else:
                updated_dt = updated_at

            timestamp = format_timestamp(updated_dt)

            # Get page (0-indexed)
            if page_number < 1 or page_number > len(pdf_doc):
                logger.warning(f"Page {page_number} out of range, skipping annotation")
                continue

            page = pdf_doc[page_number - 1]

            # Add annotation
            if add_annotation_to_page(
                page, note_text, timestamp, font_name, font_size, font_color
            ):
                annotation_count += 1

        # Ensure output directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Save annotated PDF
        pdf_doc.save(str(output_path))
        pdf_doc.close()

        logger.info(
            f"Successfully created annotated PDF with {annotation_count} "
            f"annotations: {output_path}"
        )
        return True

    except Exception as e:
        logger.error(f"Failed to create annotated PDF: {e}")
        return False


def generate_annotated_filename(original_filename: str) -> str:
    """
    Generate filename for annotated PDF.

    Args:
        original_filename: Original PDF filename

    Returns:
        str: New filename with "_annotiert" suffix

    Example:
        new_name = generate_annotated_filename("report.pdf")
        # Returns: "report_annotiert.pdf"
    """
    stem = Path(original_filename).stem
    suffix = Path(original_filename).suffix
    return f"{stem}_annotiert{suffix}"
