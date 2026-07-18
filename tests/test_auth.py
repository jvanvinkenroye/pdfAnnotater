"""
Tests for authentication routes, focused on the change-password feature.
"""

from werkzeug.security import check_password_hash

from pdf_annotator.models.database import DatabaseManager


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
