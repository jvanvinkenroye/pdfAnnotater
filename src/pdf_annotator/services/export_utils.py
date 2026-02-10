"""
Shared utilities for export services.

Common functions used by both PDF generator and Markdown exporter.
"""

from datetime import datetime
from pathlib import Path


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


def parse_timestamp(updated_at: str | datetime) -> datetime:
    """
    Parse a timestamp from database into a datetime object.

    Args:
        updated_at: Timestamp string (YYYY-MM-DD HH:MM:SS) or datetime

    Returns:
        datetime object
    """
    if isinstance(updated_at, str):
        return datetime.strptime(updated_at, "%Y-%m-%d %H:%M:%S")
    return updated_at


def format_date_for_filename(last_edited: str | datetime | None) -> str:
    """
    Extract date string (YYYY-MM-DD) from a timestamp for use in filenames.

    Args:
        last_edited: Timestamp string, datetime, or None

    Returns:
        str: Date string or empty string
    """
    if not last_edited:
        return ""
    try:
        if isinstance(last_edited, datetime):
            return last_edited.strftime("%Y-%m-%d")
        return str(last_edited)[:10]
    except (ValueError, AttributeError, TypeError):
        return ""


def generate_export_filename(
    doc_info: dict,
    last_edited: str | None,
    suffix: str,
) -> str:
    """
    Generate export filename based on metadata.

    Format: NachnameVornameDate_suffix.ext

    Args:
        doc_info: Document info dict with metadata
        last_edited: Last edited timestamp
        suffix: Filename suffix (e.g., "annotiert.pdf" or "notizen.md")

    Returns:
        str: Sanitized filename
    """
    last_name = doc_info.get("last_name", "").strip()
    first_name = doc_info.get("first_name", "").strip()
    date_str = format_date_for_filename(last_edited)

    parts = []
    if last_name:
        parts.append(last_name)
    if first_name:
        parts.append(first_name)
    if date_str:
        parts.append(date_str)

    if not parts:
        stem = Path(doc_info.get("original_filename", "document")).stem
        return f"{stem}_{suffix}"

    filename = "".join(parts) + f"_{suffix}"

    # Sanitize filename
    invalid_chars = ["<", ">", ":", '"', "/", "\\", "|", "?", "*"]
    for char in invalid_chars:
        filename = filename.replace(char, "_")

    return filename
