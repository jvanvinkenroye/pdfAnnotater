"""
Unit tests for PDF processor service.

Tests PDF validation, page counting, rendering, and cache.
"""

import fitz
import pytest

from pdf_annotator.services.pdf_processor import (
    clear_render_cache,
    clear_text_layout_cache,
    get_cache_info,
    get_page_count,
    get_page_dimensions,
    get_page_text_layout,
    render_page_to_image,
    validate_pdf,
)


class TestValidatePdf:
    """Test PDF validation."""

    def test_valid_pdf(self, sample_pdf):
        assert validate_pdf(sample_pdf) is True

    def test_invalid_file(self, tmp_path):
        invalid = tmp_path / "not_a_pdf.pdf"
        invalid.write_text("This is not a PDF")
        assert validate_pdf(invalid) is False

    def test_nonexistent_file(self, tmp_path):
        assert validate_pdf(tmp_path / "missing.pdf") is False

    def test_empty_file(self, tmp_path):
        empty = tmp_path / "empty.pdf"
        empty.write_bytes(b"")
        assert validate_pdf(empty) is False


class TestGetPageCount:
    """Test page counting."""

    def test_correct_page_count(self, sample_pdf):
        assert get_page_count(sample_pdf) == 2

    def test_three_page_pdf(self, sample_pdf_3pages):
        assert get_page_count(sample_pdf_3pages) == 3

    def test_invalid_file_raises(self, tmp_path):
        invalid = tmp_path / "bad.pdf"
        invalid.write_text("not a pdf")
        with pytest.raises(ValueError):
            get_page_count(invalid)


class TestRenderPageToImage:
    """Test page rendering."""

    def setup_method(self):
        clear_render_cache()

    def test_render_valid_page(self, sample_pdf):
        result = render_page_to_image(str(sample_pdf), 1, dpi=72)
        assert result is not None
        assert isinstance(result, bytes)
        # PNG magic bytes
        assert result[:4] == b"\x89PNG"

    def test_render_second_page(self, sample_pdf):
        result = render_page_to_image(str(sample_pdf), 2, dpi=72)
        assert result is not None

    def test_render_invalid_page_returns_none(self, sample_pdf):
        result = render_page_to_image(str(sample_pdf), 99, dpi=72)
        assert result is None

    def test_render_page_zero_returns_none(self, sample_pdf):
        result = render_page_to_image(str(sample_pdf), 0, dpi=72)
        assert result is None


class TestCache:
    """Test render cache functions."""

    def setup_method(self):
        clear_render_cache()

    def test_clear_cache(self, sample_pdf):
        render_page_to_image(str(sample_pdf), 1, dpi=72)
        clear_render_cache()
        info = get_cache_info()
        assert info["size"] == 0

    def test_cache_info_structure(self):
        info = get_cache_info()
        assert "hits" in info
        assert "misses" in info
        assert "size" in info
        assert "maxsize" in info


class TestGetPageTextLayout:
    """Test word/bbox text extraction for the selectable text overlay."""

    def setup_method(self):
        clear_text_layout_cache()

    def test_page_dimensions_match_get_page_dimensions(self, sample_pdf):
        width, height = get_page_dimensions(sample_pdf, 1)
        layout = get_page_text_layout(str(sample_pdf), 1)
        assert layout["page_width"] == width
        assert layout["page_height"] == height

    def test_words_have_well_formed_bboxes(self, sample_pdf):
        layout = get_page_text_layout(str(sample_pdf), 1)
        words = [w for line in layout["lines"] for w in line["words"]]
        assert words
        for word in words:
            assert word["x0"] < word["x1"]
            assert word["y0"] < word["y1"]

    def test_extracts_known_text(self, sample_pdf):
        layout = get_page_text_layout(str(sample_pdf), 1)
        words = [w["text"] for line in layout["lines"] for w in line["words"]]
        assert "Test" in words
        assert "Page" in words

    def test_invalid_page_raises(self, sample_pdf):
        with pytest.raises(ValueError):
            get_page_text_layout(str(sample_pdf), 99)

    def test_lines_sorted_by_visual_position(self, tmp_path):
        """
        Regression test: lines must be ordered top-to-bottom by their
        on-page position, not by PDF content-stream order — a footer
        emitted as the first block used to come first in the DOM, which
        broke browser drag-selection (selection follows DOM order).
        """
        pdf_path = tmp_path / "footer_first.pdf"
        doc = fitz.open()
        page = doc.new_page(width=595, height=842)
        # Insert the footer FIRST (bottom of page), then the heading (top):
        # content-stream order is now the reverse of visual order.
        page.insert_text((72, 800), "Fusszeile", fontsize=9)
        page.insert_text((72, 100), "Ueberschrift", fontsize=24)
        doc.save(str(pdf_path))
        doc.close()

        layout = get_page_text_layout(str(pdf_path), 1)
        line_texts = [
            " ".join(w["text"] for w in line["words"]) for line in layout["lines"]
        ]

        assert line_texts.index("Ueberschrift") < line_texts.index("Fusszeile")

    def test_rotated_page_coordinates_mapped_to_rendered_space(self, tmp_path):
        """
        Regression test: pages with a /Rotate flag (typical for scanned/
        OCRed documents) render rotated via get_pixmap(), but
        get_text("words") reports coordinates in the unrotated space —
        the overlay used to end up mirrored to the wrong corner.
        """
        pdf_path = tmp_path / "rotated.pdf"
        doc = fitz.open()
        page = doc.new_page(width=595, height=842)
        # Word near the top-left in unrotated space...
        page.insert_text((72, 100), "Marker", fontsize=24)
        page.set_rotation(180)
        doc.save(str(pdf_path))
        doc.close()

        layout = get_page_text_layout(str(pdf_path), 1)
        words = [w for line in layout["lines"] for w in line["words"]]
        marker = next(w for w in words if w["text"] == "Marker")

        # ...must appear near the bottom-right in the rendered (rotated) view
        assert marker["x0"] > layout["page_width"] / 2
        assert marker["y0"] > layout["page_height"] / 2
        assert marker["x0"] < marker["x1"]
        assert marker["y0"] < marker["y1"]

    def test_clear_text_layout_cache(self, sample_pdf):
        get_page_text_layout(str(sample_pdf), 1)
        clear_text_layout_cache()
        assert get_page_text_layout.cache_info().currsize == 0
