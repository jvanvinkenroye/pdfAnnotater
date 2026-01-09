"""
Unit tests for validators module.

Tests security-critical validation functions.
"""

import pytest
from pathlib import Path
from pdf_annotator.utils.validators import (
    validate_file_path,
    validate_note_text,
    sanitize_filename,
)


class TestValidateFilePath:
    """Test path traversal prevention."""

    def test_valid_path_within_base_dir(self, tmp_path):
        """Test that valid paths within base directory are accepted."""
        base_dir = tmp_path / "uploads"
        base_dir.mkdir()

        file_path = base_dir / "document.pdf"
        is_valid, error = validate_file_path(file_path, base_dir)

        assert is_valid is True
        assert error is None

    def test_path_traversal_attempt_rejected(self, tmp_path):
        """Test that path traversal attempts are blocked."""
        base_dir = tmp_path / "uploads"
        base_dir.mkdir()

        # Attempt to access parent directory
        file_path = base_dir / ".." / ".." / "etc" / "passwd"
        is_valid, error = validate_file_path(file_path, base_dir)

        assert is_valid is False
        assert "außerhalb" in error.lower()

    def test_absolute_path_outside_base_rejected(self, tmp_path):
        """Test that absolute paths outside base are rejected."""
        base_dir = tmp_path / "uploads"
        base_dir.mkdir()

        file_path = Path("/tmp/malicious.pdf")
        is_valid, error = validate_file_path(file_path, base_dir)

        assert is_valid is False
        assert error is not None


class TestValidateNoteText:
    """Test note text validation."""

    def test_valid_note_accepted(self):
        """Test that valid notes are accepted."""
        note = "This is a valid note with reasonable length."
        is_valid, error = validate_note_text(note, max_length=5000)

        assert is_valid is True
        assert error is None

    def test_empty_note_accepted(self):
        """Test that empty notes are accepted."""
        note = ""
        is_valid, error = validate_note_text(note, max_length=5000)

        assert is_valid is True
        assert error is None

    def test_oversized_note_rejected(self):
        """Test that oversized notes are rejected."""
        note = "x" * 6000  # Exceeds 5000 character limit
        is_valid, error = validate_note_text(note, max_length=5000)

        assert is_valid is False
        assert "zu lang" in error.lower()

    def test_non_string_note_rejected(self):
        """Test that non-string notes are rejected."""
        note = 12345  # Integer instead of string
        is_valid, error = validate_note_text(note, max_length=5000)

        assert is_valid is False
        assert "text" in error.lower()


class TestSanitizeFilename:
    """Test filename sanitization."""

    def test_path_traversal_removed(self):
        """Test that path traversal sequences are removed."""
        filename = "../../../etc/passwd.pdf"
        sanitized = sanitize_filename(filename)

        assert ".." not in sanitized
        assert "/" not in sanitized
        assert sanitized == "passwd.pdf"

    def test_dangerous_characters_replaced(self):
        """Test that dangerous characters are replaced."""
        filename = 'test<>:"|?*.pdf'
        sanitized = sanitize_filename(filename)

        # All dangerous characters should be replaced with underscore
        assert "<" not in sanitized
        assert ">" not in sanitized
        assert ":" not in sanitized
        assert '"' not in sanitized
        assert "|" not in sanitized
        assert "?" not in sanitized
        assert "*" not in sanitized
        assert sanitized == "test_______.pdf"

    def test_normal_filename_unchanged(self):
        """Test that normal filenames are not modified."""
        filename = "document_2024.pdf"
        sanitized = sanitize_filename(filename)

        assert sanitized == filename

    def test_unicode_filename_preserved(self):
        """Test that unicode characters are preserved."""
        filename = "Übung_Prüfung.pdf"
        sanitized = sanitize_filename(filename)

        assert "Ü" in sanitized
        assert "ü" in sanitized

    def test_xss_attempt_sanitized(self):
        """Test that XSS attempts in filenames are sanitized."""
        filename = "<script>alert('xss')</script>.pdf"
        sanitized = sanitize_filename(filename)

        # Dangerous characters should be removed
        assert "<" not in sanitized
        assert ">" not in sanitized
        assert "script" not in sanitized or "_" in sanitized  # XSS content removed or sanitized
        assert ".pdf" in sanitized  # Extension preserved


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
