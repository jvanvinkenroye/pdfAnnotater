"""
Tests for authentication routes, focused on the change-password feature
and the desktop auto-login mode.
"""

from pathlib import Path

from werkzeug.security import check_password_hash

from pdf_annotator.app import create_app
from pdf_annotator.models.database import DatabaseManager


class TestDesktopAutoLogin:
    """Test DESKTOP_AUTO_LOGIN (Toga desktop shell, see desktop_toga.py)."""

    def _make_auto_login_app(self, tmp_path, monkeypatch):
        monkeypatch.setenv("PDF_ANNOTATOR_DESKTOP_AUTO_LOGIN", "1")
        # Config reads env at import time -> patch the config class attr too
        from pdf_annotator.config import TestingConfig

        monkeypatch.setattr(TestingConfig, "DESKTOP_AUTO_LOGIN", True, raising=False)

        DatabaseManager._instance = None
        DatabaseManager._db_path = None
        app = create_app("testing")
        db_path = tmp_path / "autologin.db"
        app.config["DATABASE_PATH"] = db_path
        app.config["UPLOAD_FOLDER"] = tmp_path / "uploads"
        app.config["EXPORT_FOLDER"] = tmp_path / "exports"
        Path(app.config["UPLOAD_FOLDER"]).mkdir(exist_ok=True)
        Path(app.config["EXPORT_FOLDER"]).mkdir(exist_ok=True)
        DatabaseManager._instance = None
        DatabaseManager._db_path = None
        DatabaseManager(db_path).init_db()
        return app

    def test_first_request_is_logged_in_without_login(self, tmp_path, monkeypatch):
        app = self._make_auto_login_app(tmp_path, monkeypatch)
        client = app.test_client()

        response = client.get("/documents")

        # No redirect to the login page — auto-logged-in as "desktop"
        assert response.status_code == 200
        assert b"desktop" in response.data

    def test_desktop_user_created_once(self, tmp_path, monkeypatch):
        app = self._make_auto_login_app(tmp_path, monkeypatch)
        client = app.test_client()
        client.get("/documents")
        client.get("/documents")

        with app.app_context():
            db = DatabaseManager()
            users = db.get_all_users()
        desktop_users = [u for u in users if u["username"] == "desktop"]
        assert len(desktop_users) == 1
        assert desktop_users[0]["is_admin"] == 1

    def test_disabled_by_default(self, app, client):
        response = client.get("/documents")
        # Normal behavior: redirect to login
        assert response.status_code == 302
        assert "/auth/login" in response.headers["Location"]


class TestChangePassword:
    """Test the change-password form and route."""

    def test_form_renders_for_logged_in_user(self, app, logged_in_client):
        response = logged_in_client.get("/auth/change-password")
        assert response.status_code == 200
        assert "Passwort" in response.get_data(as_text=True)

    def test_requires_login(self, client):
        response = client.get("/auth/change-password")
        assert response.status_code == 302

    def test_successful_change(self, app, logged_in_client, user):
        response = logged_in_client.post(
            "/auth/change-password",
            data={
                "current_password": "testpassword",
                "new_password": "newpassword123",
                "new_password_confirm": "newpassword123",
            },
        )
        assert response.status_code == 200
        assert "erfolgreich" in response.get_data(as_text=True)

        db = DatabaseManager()
        with app.app_context():
            user_data = db.get_user_by_id(user)
        assert check_password_hash(user_data["password_hash"], "newpassword123")

    def test_wrong_current_password_rejected(self, app, logged_in_client, user):
        response = logged_in_client.post(
            "/auth/change-password",
            data={
                "current_password": "wrongpassword",
                "new_password": "newpassword123",
                "new_password_confirm": "newpassword123",
            },
        )
        assert response.status_code == 401

        db = DatabaseManager()
        with app.app_context():
            user_data = db.get_user_by_id(user)
        assert check_password_hash(user_data["password_hash"], "testpassword")

    def test_too_short_new_password_rejected(self, app, logged_in_client):
        response = logged_in_client.post(
            "/auth/change-password",
            data={
                "current_password": "testpassword",
                "new_password": "short",
                "new_password_confirm": "short",
            },
        )
        assert response.status_code == 400

    def test_mismatched_confirmation_rejected(self, app, logged_in_client):
        response = logged_in_client.post(
            "/auth/change-password",
            data={
                "current_password": "testpassword",
                "new_password": "newpassword123",
                "new_password_confirm": "differentpassword",
            },
        )
        assert response.status_code == 400
