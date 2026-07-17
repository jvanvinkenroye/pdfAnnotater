"""
Unit tests for PDF processor service.

Tests PDF validation, page counting, rendering, and cache.
"""

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

    def test_clear_text_layout_cache(self, sample_pdf):
        get_page_text_layout(str(sample_pdf), 1)
        clear_text_layout_cache()
        assert get_page_text_layout.cache_info().currsize == 0
