"""
Unit tests for PDF generator service.

Tests annotated PDF creation, edge cases, and special characters.
"""

from pathlib import Path

import fitz

from pdf_annotator.models.database import DatabaseManager
from pdf_annotator.services.pdf_generator import (
    add_annotation_to_page,
    calculate_footer_rect,
    generate_annotated_filename,
)


class TestCalculateFooterRect:
    """Test footer rectangle calculation."""

    def test_footer_rect_default(self):
        page_rect = fitz.Rect(0, 0, 595, 842)
        footer = calculate_footer_rect(page_rect)
        assert footer.x0 == 10
        assert footer.y1 == 832  # 842 - 10
        assert footer.x1 == 585  # 595 - 10

    def test_footer_rect_custom_height(self):
        page_rect = fitz.Rect(0, 0, 595, 842)
        footer = calculate_footer_rect(page_rect, footer_height=100)
        assert footer.y0 == 742  # 842 - 100


class TestAddAnnotationToPage:
    """Test adding annotations to PDF pages."""

    def test_add_annotation_success(self):
        doc = fitz.open()
        page = doc.new_page(width=595, height=842)
        result = add_annotation_to_page(page, "Test note", "[2026-01-01 12:00]")
        assert result is True
        doc.close()

    def test_add_annotation_with_special_chars(self):
        doc = fitz.open()
        page = doc.new_page(width=595, height=842)
        result = add_annotation_to_page(
            page,
            "Umlaute: ae oe ue ss",
            "[2026-01-01 12:00]",
        )
        assert result is True
        doc.close()

    def test_add_annotation_long_text(self):
        doc = fitz.open()
        page = doc.new_page(width=595, height=842)
        long_text = "Lorem ipsum dolor sit amet. " * 50
        result = add_annotation_to_page(page, long_text, "[2026-01-01 12:00]")
        assert result is True
        doc.close()


class TestCreateAnnotatedPdf:
    """Test full annotated PDF creation (requires app context)."""

    def test_create_annotated_pdf(self, app, sample_pdf):
        with app.app_context():
            db = DatabaseManager()

            # Store PDF in upload folder
            import shutil

            upload_path = Path(app.config["UPLOAD_FOLDER"]) / "test.pdf"
            shutil.copy2(sample_pdf, upload_path)

            doc_id = db.create_document(
                "test.pdf",
                str(upload_path),
                2,
            )
            db.upsert_annotation(doc_id, 1, "Annotation page 1")
            db.upsert_annotation(doc_id, 2, "Annotation page 2")

            from pdf_annotator.services.pdf_generator import create_annotated_pdf

            output = Path(app.config["EXPORT_FOLDER"]) / "output.pdf"
            result = create_annotated_pdf(doc_id, output, db)

            assert result is True
            assert output.exists()
            assert output.stat().st_size > 0

            # Verify output is valid PDF
            out_doc = fitz.open(str(output))
            assert len(out_doc) == 2
            out_doc.close()

    def test_create_annotated_pdf_empty_annotations(self, app, sample_pdf):
        with app.app_context():
            db = DatabaseManager()

            import shutil

            upload_path = Path(app.config["UPLOAD_FOLDER"]) / "test.pdf"
            shutil.copy2(sample_pdf, upload_path)

            doc_id = db.create_document("test.pdf", str(upload_path), 2)
            # Only empty annotations
            db.upsert_annotation(doc_id, 1, "")
            db.upsert_annotation(doc_id, 2, "   ")

            from pdf_annotator.services.pdf_generator import create_annotated_pdf

            output = Path(app.config["EXPORT_FOLDER"]) / "output.pdf"
            result = create_annotated_pdf(doc_id, output, db)

            assert result is True
            assert output.exists()

    def test_create_annotated_pdf_nonexistent_doc(self, app):
        with app.app_context():
            db = DatabaseManager()

            from pdf_annotator.services.pdf_generator import create_annotated_pdf

            output = Path(app.config["EXPORT_FOLDER"]) / "output.pdf"
            result = create_annotated_pdf("nonexistent", output, db)
            assert result is False


class TestGenerateAnnotatedFilename:
    """Test filename generation."""

    def test_filename_with_metadata(self):
        doc_info = {
            "last_name": "Mustermann",
            "first_name": "Max",
            "original_filename": "report.pdf",
        }
        name = generate_annotated_filename(doc_info, "2026-01-08 12:00:00")
        assert "Mustermann" in name
        assert "Max" in name
        assert "2026-01-08" in name
        assert "_annotiert.pdf" in name

    def test_filename_without_metadata(self):
        doc_info = {
            "last_name": "",
            "first_name": "",
            "original_filename": "report.pdf",
        }
        name = generate_annotated_filename(doc_info, None)
        assert "report_annotiert.pdf" == name
