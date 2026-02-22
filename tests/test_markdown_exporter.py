"""
Unit tests for Markdown exporter service.

Tests export format, empty annotations, page references, and UTF-8 encoding.
"""

from pdf_annotator.services.markdown_exporter import (
    export_to_markdown,
    generate_markdown_filename,
)


class TestExportToMarkdown:
    """Test Markdown export."""

    def test_export_with_annotations(self, db, sample_pdf, tmp_path):
        doc_id = db.create_document(
            "test.pdf",
            str(sample_pdf),
            2,
            first_name="Max",
            last_name="Mustermann",
        )
        db.upsert_annotation(doc_id, 1, "Notiz Seite eins")
        db.upsert_annotation(doc_id, 2, "Notiz Seite zwei")

        output = tmp_path / "notes.md"
        result = export_to_markdown(doc_id, output, db)

        assert result is True
        assert output.exists()

        content = output.read_text(encoding="utf-8")
        assert "# Notizen zu test.pdf" in content
        assert "## Seite 1" in content
        assert "## Seite 2" in content
        assert "Notiz Seite eins" in content
        assert "Notiz Seite zwei" in content

    def test_export_empty_annotations_skipped(self, db, sample_pdf, tmp_path):
        doc_id = db.create_document("test.pdf", str(sample_pdf), 2)
        db.upsert_annotation(doc_id, 1, "")
        db.upsert_annotation(doc_id, 2, "   ")

        output = tmp_path / "notes.md"
        result = export_to_markdown(doc_id, output, db)

        assert result is True
        content = output.read_text(encoding="utf-8")
        assert "Keine Notizen vorhanden" in content

    def test_export_page_references_correct(self, db, sample_pdf, tmp_path):
        doc_id = db.create_document("test.pdf", str(sample_pdf), 2)
        # Only annotate page 2
        db.upsert_annotation(doc_id, 2, "Nur Seite 2 hat Notizen")

        output = tmp_path / "notes.md"
        export_to_markdown(doc_id, output, db)

        content = output.read_text(encoding="utf-8")
        assert "## Seite 2" in content
        assert "Seite 1" not in content

    def test_export_utf8_encoding(self, db, sample_pdf, tmp_path):
        doc_id = db.create_document("test.pdf", str(sample_pdf), 2)
        db.upsert_annotation(doc_id, 1, "Umlaute: ae oe ue ss und Sonderzeichen")

        output = tmp_path / "notes.md"
        export_to_markdown(doc_id, output, db)

        content = output.read_text(encoding="utf-8")
        assert "ae oe ue ss" in content

    def test_export_nonexistent_doc(self, db, tmp_path):
        output = tmp_path / "notes.md"
        result = export_to_markdown("nonexistent", output, db)
        assert result is False


class TestGenerateMarkdownFilename:
    """Test Markdown filename generation."""

    def test_filename_with_metadata(self):
        doc_info = {
            "last_name": "Mustermann",
            "first_name": "Max",
            "original_filename": "report.pdf",
        }
        name = generate_markdown_filename(doc_info, "2026-01-08 12:00:00")
        assert "Mustermann" in name
        assert "Max" in name
        assert "_notizen.md" in name

    def test_filename_without_metadata(self):
        doc_info = {
            "last_name": "",
            "first_name": "",
            "original_filename": "report.pdf",
        }
        name = generate_markdown_filename(doc_info, None)
        assert name == "report_notizen.md"
