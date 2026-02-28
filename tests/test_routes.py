"""
Unit tests for Flask routes.

Tests upload, viewer, annotation, metadata, delete, and export endpoints.
"""

import json


class TestUploadRoutes:
    """Test upload endpoints."""

    def test_index_page(self, logged_in_client):
        response = logged_in_client.get("/")
        assert response.status_code == 200
        assert b"PDF Annotator" in response.data

    def test_upload_pdf_success(self, app, logged_in_client, sample_pdf):
        data = {
            "file": (open(sample_pdf, "rb"), "test.pdf"),
            "first_name": "Max",
            "last_name": "Mustermann",
        }
        response = logged_in_client.post(
            "/upload",
            data=data,
            content_type="multipart/form-data",
            headers={"Accept": "application/json"},
        )
        assert response.status_code == 200
        result = response.get_json()
        assert result["success"] is True
        assert "doc_id" in result
        assert "redirect_url" in result

    def test_upload_without_file(self, logged_in_client):
        response = logged_in_client.post(
            "/upload",
            data={},
            content_type="multipart/form-data",
        )
        assert response.status_code == 400

    def test_upload_non_pdf(self, logged_in_client, tmp_path):
        txt_file = tmp_path / "test.txt"
        txt_file.write_text("not a pdf")
        data = {"file": (open(txt_file, "rb"), "test.txt")}
        response = logged_in_client.post(
            "/upload",
            data=data,
            content_type="multipart/form-data",
        )
        assert response.status_code == 400

    def test_upload_invalid_pdf(self, logged_in_client, tmp_path):
        fake_pdf = tmp_path / "fake.pdf"
        fake_pdf.write_text("this is not actually a PDF")
        data = {"file": (open(fake_pdf, "rb"), "fake.pdf")}
        response = logged_in_client.post(
            "/upload",
            data=data,
            content_type="multipart/form-data",
        )
        assert response.status_code == 400


class TestDocumentList:
    """Test document listing."""

    def test_documents_page(self, logged_in_client):
        response = logged_in_client.get("/documents")
        assert response.status_code == 200
        assert b"Dokumente" in response.data


class TestDeleteDocument:
    """Test document deletion."""

    def test_delete_existing_document(self, app, logged_in_client, uploaded_pdf):
        response = logged_in_client.delete(f"/delete/{uploaded_pdf}")
        assert response.status_code == 200
        result = response.get_json()
        assert result["success"] is True

    def test_delete_invalid_doc_id(self, logged_in_client):
        response = logged_in_client.delete("/delete/not-a-uuid")
        assert response.status_code == 400

    def test_delete_nonexistent_document(self, logged_in_client):
        fake_uuid = "00000000-0000-0000-0000-000000000000"
        response = logged_in_client.delete(f"/delete/{fake_uuid}")
        assert response.status_code == 404


class TestViewerRoutes:
    """Test viewer endpoints."""

    def test_viewer_page(self, app, logged_in_client, uploaded_pdf):
        response = logged_in_client.get(f"/viewer/{uploaded_pdf}")
        assert response.status_code == 200
        assert b"Notizen" in response.data

    def test_viewer_invalid_doc_id(self, logged_in_client):
        response = logged_in_client.get("/viewer/not-a-uuid")
        assert response.status_code == 400

    def test_viewer_nonexistent_doc(self, logged_in_client):
        fake_uuid = "00000000-0000-0000-0000-000000000000"
        response = logged_in_client.get(f"/viewer/{fake_uuid}")
        assert response.status_code == 404


class TestPageImageApi:
    """Test page rendering API."""

    def test_get_page_image(self, app, logged_in_client, uploaded_pdf):
        response = logged_in_client.get(f"/viewer/api/page/{uploaded_pdf}/1")
        assert response.status_code == 200
        assert response.content_type == "image/png"
        # PNG magic bytes
        assert response.data[:4] == b"\x89PNG"

    def test_get_page_image_invalid_page(self, app, logged_in_client, uploaded_pdf):
        response = logged_in_client.get(f"/viewer/api/page/{uploaded_pdf}/99")
        assert response.status_code == 400

    def test_get_page_image_invalid_doc(self, logged_in_client):
        response = logged_in_client.get("/viewer/api/page/not-a-uuid/1")
        assert response.status_code == 400


class TestAnnotationApi:
    """Test annotation GET/POST API."""

    def test_get_annotation_empty(self, app, logged_in_client, uploaded_pdf):
        response = logged_in_client.get(f"/viewer/api/annotation/{uploaded_pdf}/1")
        assert response.status_code == 200
        data = response.get_json()
        assert "note_text" in data

    def test_save_and_get_annotation(self, app, logged_in_client, uploaded_pdf):
        # Save
        response = logged_in_client.post(
            f"/viewer/api/annotation/{uploaded_pdf}/1",
            data=json.dumps({"note_text": "Test note"}),
            content_type="application/json",
        )
        assert response.status_code == 200
        assert response.get_json()["success"] is True

        # Verify
        response = logged_in_client.get(f"/viewer/api/annotation/{uploaded_pdf}/1")
        data = response.get_json()
        assert data["note_text"] == "Test note"

    def test_save_annotation_no_data(self, app, logged_in_client, uploaded_pdf):
        response = logged_in_client.post(
            f"/viewer/api/annotation/{uploaded_pdf}/1",
            data=json.dumps({}),
            content_type="application/json",
        )
        assert response.status_code == 400

    def test_save_annotation_invalid_page(self, app, logged_in_client, uploaded_pdf):
        response = logged_in_client.post(
            f"/viewer/api/annotation/{uploaded_pdf}/99",
            data=json.dumps({"note_text": "x"}),
            content_type="application/json",
        )
        assert response.status_code == 400


class TestMetadataApi:
    """Test metadata update API."""

    def test_update_metadata(self, app, logged_in_client, uploaded_pdf):
        response = logged_in_client.post(
            f"/viewer/api/metadata/{uploaded_pdf}",
            data=json.dumps(
                {
                    "first_name": "Max",
                    "last_name": "Mustermann",
                    "title": "Neuer Titel",
                    "year": "2026",
                    "subject": "Informatik",
                }
            ),
            content_type="application/json",
            headers={"X-CSRFToken": "test"},
        )
        assert response.status_code == 200
        assert response.get_json()["success"] is True

    def test_update_metadata_no_data(self, app, logged_in_client, uploaded_pdf):
        response = logged_in_client.post(
            f"/viewer/api/metadata/{uploaded_pdf}",
            data=json.dumps({}),
            content_type="application/json",
        )
        assert response.status_code == 400

    def test_update_metadata_invalid_doc(self, logged_in_client):
        response = logged_in_client.post(
            "/viewer/api/metadata/not-a-uuid",
            data=json.dumps({"first_name": "X"}),
            content_type="application/json",
        )
        assert response.status_code == 400


class TestDeletePage:
    """Test page deletion API."""

    def test_delete_page_success(self, app, logged_in_client, uploaded_pdf_3pages):
        """Deleting page 2 from a 3-page PDF leaves 2 pages."""
        response = logged_in_client.delete(
            f"/viewer/api/page/{uploaded_pdf_3pages}/2"
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert data["page_count"] == 2

    def test_delete_last_remaining_page_rejected(self, app, logged_in_client, tmp_path, user, db):
        """Cannot delete the only page in a 1-page PDF."""
        import shutil
        from pathlib import Path

        import fitz

        pdf_path = tmp_path / "single.pdf"
        doc = fitz.open()
        page = doc.new_page(width=595, height=842)
        page.insert_text((72, 72), "Single page", fontsize=24)
        doc.save(str(pdf_path))
        doc.close()

        upload_path = Path(app.config["UPLOAD_FOLDER"]) / "single.pdf"
        shutil.copy2(pdf_path, upload_path)

        doc_id = db.create_document(
            user_id=user,
            filename="single.pdf",
            file_path=str(upload_path),
            page_count=1,
        )

        response = logged_in_client.delete(f"/viewer/api/page/{doc_id}/1")
        assert response.status_code == 400

    def test_delete_page_renumbers_annotations(self, app, logged_in_client, uploaded_pdf_3pages, db):
        """Annotations for pages after deleted page are renumbered."""
        response = logged_in_client.delete(
            f"/viewer/api/page/{uploaded_pdf_3pages}/2"
        )
        assert response.status_code == 200

        # Old page 3 annotation should now be on page 2
        ann = db.get_annotation(uploaded_pdf_3pages, 2)
        assert ann is not None
        assert ann["note_text"] == "Notiz Seite 3"

        # Old page 2 annotation should be gone
        annotations = db.get_all_annotations(uploaded_pdf_3pages)
        assert len(annotations) == 2

    def test_delete_page_invalid_page_number(self, app, logged_in_client, uploaded_pdf_3pages):
        """Invalid page number returns 400."""
        response = logged_in_client.delete(
            f"/viewer/api/page/{uploaded_pdf_3pages}/99"
        )
        assert response.status_code == 400


class TestExportRoutes:
    """Test PDF and Markdown export."""

    def test_export_pdf(self, app, logged_in_client, uploaded_pdf):
        # Add an annotation first
        logged_in_client.post(
            f"/viewer/api/annotation/{uploaded_pdf}/1",
            data=json.dumps({"note_text": "Export test note"}),
            content_type="application/json",
        )

        response = logged_in_client.post(f"/export/pdf/{uploaded_pdf}")
        assert response.status_code == 200
        assert response.content_type == "application/pdf"

    def test_export_markdown(self, app, logged_in_client, uploaded_pdf):
        # Add an annotation first
        logged_in_client.post(
            f"/viewer/api/annotation/{uploaded_pdf}/1",
            data=json.dumps({"note_text": "Markdown test note"}),
            content_type="application/json",
        )

        response = logged_in_client.post(f"/export/markdown/{uploaded_pdf}")
        assert response.status_code == 200
        assert "markdown" in response.content_type or "text" in response.content_type

    def test_export_original_pdf(self, app, logged_in_client, uploaded_pdf):
        response = logged_in_client.get(f"/export/original/{uploaded_pdf}")
        assert response.status_code == 200
        assert response.content_type == "application/pdf"

    def test_export_nonexistent_doc(self, logged_in_client):
        fake_uuid = "00000000-0000-0000-0000-000000000000"
        response = logged_in_client.post(f"/export/pdf/{fake_uuid}")
        assert response.status_code == 404

    def test_export_info(self, app, logged_in_client, uploaded_pdf):
        response = logged_in_client.get("/export/info")
        assert response.status_code == 200
        data = response.get_json()
        assert "document_count" in data
        assert "annotation_count" in data
