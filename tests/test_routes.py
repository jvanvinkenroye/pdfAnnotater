"""
Unit tests for Flask routes.

Tests upload, viewer, annotation, metadata, delete, and export endpoints.
"""

import json


class TestUploadRoutes:
    """Test upload endpoints."""

    def test_index_page(self, client):
        response = client.get("/")
        assert response.status_code == 200
        assert b"PDF Annotator" in response.data

    def test_upload_pdf_success(self, app, client, sample_pdf):
        data = {
            "file": (open(sample_pdf, "rb"), "test.pdf"),
            "first_name": "Max",
            "last_name": "Mustermann",
        }
        response = client.post(
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

    def test_upload_without_file(self, client):
        response = client.post(
            "/upload",
            data={},
            content_type="multipart/form-data",
        )
        assert response.status_code == 400

    def test_upload_non_pdf(self, client, tmp_path):
        txt_file = tmp_path / "test.txt"
        txt_file.write_text("not a pdf")
        data = {"file": (open(txt_file, "rb"), "test.txt")}
        response = client.post(
            "/upload",
            data=data,
            content_type="multipart/form-data",
        )
        assert response.status_code == 400

    def test_upload_invalid_pdf(self, client, tmp_path):
        fake_pdf = tmp_path / "fake.pdf"
        fake_pdf.write_text("this is not actually a PDF")
        data = {"file": (open(fake_pdf, "rb"), "fake.pdf")}
        response = client.post(
            "/upload",
            data=data,
            content_type="multipart/form-data",
        )
        assert response.status_code == 400


class TestDocumentList:
    """Test document listing."""

    def test_documents_page(self, client):
        response = client.get("/documents")
        assert response.status_code == 200
        assert b"Dokumente" in response.data


class TestDeleteDocument:
    """Test document deletion."""

    def test_delete_existing_document(self, app, client, uploaded_pdf):
        response = client.delete(f"/delete/{uploaded_pdf}")
        assert response.status_code == 200
        result = response.get_json()
        assert result["success"] is True

    def test_delete_invalid_doc_id(self, client):
        response = client.delete("/delete/not-a-uuid")
        assert response.status_code == 400

    def test_delete_nonexistent_document(self, client):
        fake_uuid = "00000000-0000-0000-0000-000000000000"
        response = client.delete(f"/delete/{fake_uuid}")
        assert response.status_code == 404


class TestViewerRoutes:
    """Test viewer endpoints."""

    def test_viewer_page(self, app, client, uploaded_pdf):
        response = client.get(f"/viewer/{uploaded_pdf}")
        assert response.status_code == 200
        assert b"Notizen" in response.data

    def test_viewer_invalid_doc_id(self, client):
        response = client.get("/viewer/not-a-uuid")
        assert response.status_code == 400

    def test_viewer_nonexistent_doc(self, client):
        fake_uuid = "00000000-0000-0000-0000-000000000000"
        response = client.get(f"/viewer/{fake_uuid}")
        assert response.status_code == 404


class TestPageImageApi:
    """Test page rendering API."""

    def test_get_page_image(self, app, client, uploaded_pdf):
        response = client.get(f"/viewer/api/page/{uploaded_pdf}/1")
        assert response.status_code == 200
        assert response.content_type == "image/png"
        # PNG magic bytes
        assert response.data[:4] == b"\x89PNG"

    def test_get_page_image_invalid_page(self, app, client, uploaded_pdf):
        response = client.get(f"/viewer/api/page/{uploaded_pdf}/99")
        assert response.status_code == 400

    def test_get_page_image_invalid_doc(self, client):
        response = client.get("/viewer/api/page/not-a-uuid/1")
        assert response.status_code == 400


class TestAnnotationApi:
    """Test annotation GET/POST API."""

    def test_get_annotation_empty(self, app, client, uploaded_pdf):
        response = client.get(f"/viewer/api/annotation/{uploaded_pdf}/1")
        assert response.status_code == 200
        data = response.get_json()
        assert "note_text" in data

    def test_save_and_get_annotation(self, app, client, uploaded_pdf):
        # Save
        response = client.post(
            f"/viewer/api/annotation/{uploaded_pdf}/1",
            data=json.dumps({"note_text": "Test note"}),
            content_type="application/json",
        )
        assert response.status_code == 200
        assert response.get_json()["success"] is True

        # Verify
        response = client.get(f"/viewer/api/annotation/{uploaded_pdf}/1")
        data = response.get_json()
        assert data["note_text"] == "Test note"

    def test_save_annotation_no_data(self, app, client, uploaded_pdf):
        response = client.post(
            f"/viewer/api/annotation/{uploaded_pdf}/1",
            data=json.dumps({}),
            content_type="application/json",
        )
        assert response.status_code == 400

    def test_save_annotation_invalid_page(self, app, client, uploaded_pdf):
        response = client.post(
            f"/viewer/api/annotation/{uploaded_pdf}/99",
            data=json.dumps({"note_text": "x"}),
            content_type="application/json",
        )
        assert response.status_code == 400


class TestMetadataApi:
    """Test metadata update API."""

    def test_update_metadata(self, app, client, uploaded_pdf):
        response = client.post(
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

    def test_update_metadata_no_data(self, app, client, uploaded_pdf):
        response = client.post(
            f"/viewer/api/metadata/{uploaded_pdf}",
            data=json.dumps({}),
            content_type="application/json",
        )
        assert response.status_code == 400

    def test_update_metadata_invalid_doc(self, client):
        response = client.post(
            "/viewer/api/metadata/not-a-uuid",
            data=json.dumps({"first_name": "X"}),
            content_type="application/json",
        )
        assert response.status_code == 400


class TestExportRoutes:
    """Test PDF and Markdown export."""

    def test_export_pdf(self, app, client, uploaded_pdf):
        # Add an annotation first
        client.post(
            f"/viewer/api/annotation/{uploaded_pdf}/1",
            data=json.dumps({"note_text": "Export test note"}),
            content_type="application/json",
        )

        response = client.post(f"/export/pdf/{uploaded_pdf}")
        assert response.status_code == 200
        assert response.content_type == "application/pdf"

    def test_export_markdown(self, app, client, uploaded_pdf):
        # Add an annotation first
        client.post(
            f"/viewer/api/annotation/{uploaded_pdf}/1",
            data=json.dumps({"note_text": "Markdown test note"}),
            content_type="application/json",
        )

        response = client.post(f"/export/markdown/{uploaded_pdf}")
        assert response.status_code == 200
        assert "markdown" in response.content_type or "text" in response.content_type

    def test_export_original_pdf(self, app, client, uploaded_pdf):
        response = client.get(f"/export/original/{uploaded_pdf}")
        assert response.status_code == 200
        assert response.content_type == "application/pdf"

    def test_export_nonexistent_doc(self, client):
        fake_uuid = "00000000-0000-0000-0000-000000000000"
        response = client.post(f"/export/pdf/{fake_uuid}")
        assert response.status_code == 404

    def test_export_info(self, app, client, uploaded_pdf):
        response = client.get("/export/info")
        assert response.status_code == 200
        data = response.get_json()
        assert "document_count" in data
        assert "annotation_count" in data
