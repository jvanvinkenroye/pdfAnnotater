"""
PDF Processing module for PDF Annotator.

Handles PDF rendering and validation using PyMuPDF (fitz).
"""

from functools import lru_cache
from pathlib import Path

import fitz  # PyMuPDF

from pdf_annotator.utils.logger import get_logger

logger = get_logger(__name__)


def validate_pdf(file_path: Path) -> bool:
    """
    Validate if file is a valid PDF document.

    Args:
        file_path: Path to PDF file

    Returns:
        bool: True if valid PDF, False otherwise

    Example:
        if validate_pdf(Path("document.pdf")):
            print("Valid PDF")
    """
    try:
        with fitz.open(str(file_path)) as doc:
            page_count = len(doc)
            logger.debug("Validated PDF: %s (%d pages)", file_path.name, page_count)
            return page_count > 0
    except Exception as e:
        logger.error(f"PDF validation failed for {file_path}: {e}")
        return False


def get_page_count(file_path: Path) -> int:
    """
    Get number of pages in PDF.

    Args:
        file_path: Path to PDF file

    Returns:
        int: Number of pages

    Raises:
        ValueError: If file is not a valid PDF

    Example:
        page_count = get_page_count(Path("document.pdf"))
        print(f"Document has {page_count} pages")
    """
    try:
        with fitz.open(str(file_path)) as doc:
            return len(doc)
    except Exception as e:
        logger.error(f"Failed to get page count for {file_path}: {e}")
        raise ValueError(f"Invalid PDF file: {e}") from e


def get_page_dimensions(file_path: Path, page_num: int) -> tuple[float, float]:
    """
    Get dimensions (width, height) of a PDF page in points.

    Args:
        file_path: Path to PDF file
        page_num: Page number (1-indexed)

    Returns:
        Tuple of (width, height) in points

    Raises:
        ValueError: If page number is invalid

    Example:
        width, height = get_page_dimensions(Path("doc.pdf"), 1)
        print(f"Page 1: {width}x{height} points")
    """
    try:
        with fitz.open(str(file_path)) as doc:
            if page_num < 1 or page_num > len(doc):
                raise ValueError(f"Page number {page_num} out of range (1-{len(doc)})")
            page = doc[page_num - 1]  # Convert to 0-indexed
            rect = page.rect
            return (rect.width, rect.height)
    except Exception as e:
        logger.error(
            f"Failed to get dimensions for page {page_num} of {file_path}: {e}"
        )
        raise


@lru_cache(maxsize=50)
def _render_page_cached(file_path: str, page_num: int, dpi: int) -> bytes:
    """
    Internal cached page rendering. Raises on failure so errors are never cached.

    File path must be a string (not Path) for LRU cache compatibility.
    """
    logger.debug("Rendering page %d from %s", page_num, Path(file_path).name)
    doc = fitz.open(file_path)

    if page_num < 1 or page_num > len(doc):
        doc.close()
        raise ValueError(f"Page {page_num} out of range (1-{len(doc)}) for {file_path}")

    # Get page (0-indexed)
    page = doc[page_num - 1]

    # Calculate zoom factor from DPI (PyMuPDF default is 72 DPI)
    zoom = dpi / 72
    mat = fitz.Matrix(zoom, zoom)

    pix = page.get_pixmap(matrix=mat)
    png_bytes = pix.tobytes("png")
    doc.close()

    logger.debug(
        "Successfully rendered page %d (%dx%d pixels)",
        page_num,
        pix.width,
        pix.height,
    )
    return bytes(png_bytes)


def render_page_to_image(file_path: str, page_num: int, dpi: int = 300) -> bytes | None:
    """
    Render PDF page to PNG image.

    Wraps the cached internal renderer. Returns None on error instead of raising,
    so callers do not need to handle exceptions.

    Args:
        file_path: Path to PDF file (as string)
        page_num: Page number (1-indexed)
        dpi: Resolution for rendering (default: 300)

    Returns:
        bytes: PNG image data or None on error

    Example:
        image_bytes = render_page_to_image("/path/to/doc.pdf", 1, dpi=300)
        if image_bytes:
            with open("page1.png", "wb") as f:
                f.write(image_bytes)
    """
    try:
        return _render_page_cached(file_path, page_num, dpi)
    except Exception as e:
        logger.error("Failed to render page %d from %s: %s", page_num, file_path, e)
        return None


def clear_render_cache() -> None:
    """
    Clear the LRU cache for rendered pages.

    Useful for freeing memory or when PDF files are updated.

    Example:
        clear_render_cache()
        logger.info("Render cache cleared")
    """
    _render_page_cached.cache_clear()
    logger.info("PDF render cache cleared")


@lru_cache(maxsize=50)
def get_page_text_layout(file_path: str, page_num: int) -> dict:
    """
    Extract word-level text with bounding boxes for a PDF page.

    Used to build a selectable/copyable text overlay on top of the raster
    page image. Coordinates are in PDF points, matching get_page_dimensions.

    Args:
        file_path: Path to PDF file (as string, for LRU cache compatibility)
        page_num: Page number (1-indexed)

    Raises:
        ValueError: If page number is invalid

    Returns:
        dict with page_width, page_height (points) and lines, each a list
        of words with text and x0/y0/x1/y1 bounding box in points.
    """
    doc = fitz.open(file_path)
    try:
        if page_num < 1 or page_num > len(doc):
            raise ValueError(
                f"Page {page_num} out of range (1-{len(doc)}) for {file_path}"
            )

        page = doc[page_num - 1]
        rect = page.rect
        words = page.get_text("words")

        # Group words by (block_no, line_no) to preserve line breaks on copy.
        lines_by_key: dict[tuple[int, int], list[dict]] = {}
        for x0, y0, x1, y1, text, block_no, line_no, _word_no in words:
            key = (block_no, line_no)
            lines_by_key.setdefault(key, []).append(
                {"text": text, "x0": x0, "y0": y0, "x1": x1, "y1": y1}
            )

        lines = [lines_by_key[key] for key in sorted(lines_by_key)]

        return {
            "page_width": rect.width,
            "page_height": rect.height,
            "lines": [{"words": line_words} for line_words in lines],
        }
    finally:
        doc.close()


def clear_text_layout_cache() -> None:
    """
    Clear the LRU cache for extracted text layouts.

    Must be called alongside clear_render_cache() whenever a PDF's content
    changes (replace/append/delete page), otherwise stale word/bbox data
    could be served after the image cache has already been invalidated.
    """
    get_page_text_layout.cache_clear()
    logger.info("PDF text layout cache cleared")


def get_cache_info() -> dict:
    """
    Get information about the render cache.

    Returns:
        dict: Cache statistics (hits, misses, size, maxsize)

    Example:
        info = get_cache_info()
        print(f"Cache hits: {info['hits']}, misses: {info['misses']}")
    """
    cache_info = _render_page_cached.cache_info()
    return {
        "hits": cache_info.hits,
        "misses": cache_info.misses,
        "size": cache_info.currsize,
        "maxsize": cache_info.maxsize,
    }
