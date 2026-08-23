"""
Tests for content-negotiating error handlers and get_owned_document.
"""

import uuid

UNKNOWN_ID = str(uuid.uuid4())


class TestJsonErrors:
    """API paths answer errors as JSON."""

    def test_invalid_doc_id_returns_json_400(self, logged_in_client):
        response = logged_in_client.get("/viewer/api/annotation/not-a-uuid/1")
        assert response.status_code == 400
        assert response.get_json()["error"] == "Ungültige Dokument-ID"

    def test_unknown_document_returns_json_404(self, logged_in_client):
        response = logged_in_client.get(f"/viewer/api/annotation/{UNKNOWN_ID}/1")
        assert response.status_code == 404
        assert response.get_json()["error"] == "Dokument nicht gefunden"

    def test_foreign_document_returns_json_403(self, client, uploaded_pdf, second_user):
        login = client.post(
            "/auth/login",
            data={"username": "seconduser", "password": "secondpassword"},
        )
        assert login.status_code == 302

        response = client.get(f"/viewer/api/annotation/{uploaded_pdf}/1")
        assert response.status_code == 403
        assert response.get_json()["error"] == "Nicht berechtigt"

    def test_export_route_errors_as_json(self, logged_in_client):
        response = logged_in_client.post(f"/export/pdf/{UNKNOWN_ID}")
        assert response.status_code == 404
        assert response.get_json()["error"] == "Dokument nicht gefunden"

    def test_delete_route_errors_as_json(self, logged_in_client):
        response = logged_in_client.delete("/delete/not-a-uuid")
        assert response.status_code == 400
        assert response.get_json()["error"] == "Ungültige Dokument-ID"


class TestHtmlErrors:
    """Browser page requests get the HTML error page."""

    def test_viewer_page_invalid_id_renders_html_400(self, logged_in_client):
        response = logged_in_client.get("/viewer/not-a-uuid")
        assert response.status_code == 400
        assert "text/html" in response.content_type
        assert "Ungültige Anfrage" in response.data.decode()

    def test_viewer_page_unknown_doc_renders_html_404(self, logged_in_client):
        response = logged_in_client.get(f"/viewer/{UNKNOWN_ID}")
        assert response.status_code == 404
        assert "text/html" in response.content_type
        assert "Seite nicht gefunden" in response.data.decode()

    def test_unknown_url_renders_html_404(self, logged_in_client):
        response = logged_in_client.get("/gibt-es-nicht")
        assert response.status_code == 404
        assert "text/html" in response.content_type
