"""
Tests for the Flask-WTF auth forms via the HTTP routes.

Asserts that status codes and German error messages match the previous
hand-rolled validation exactly.
"""


def _register(client, **overrides):
    data = {
        "username": "neueruser",
        "email": "neu@example.com",
        "password": "geheimespasswort",
        "password_confirm": "geheimespasswort",
    }
    data.update(overrides)
    return client.post("/auth/register", data=data)


class TestRegisterForm:
    def test_missing_field_message_wins(self, client):
        response = _register(client, email="")
        assert response.status_code == 400
        assert "Alle Felder erforderlich." in response.data.decode()

    def test_missing_field_beats_other_errors(self, client):
        # Short username AND missing email: presence error has priority,
        # as in the previous implementation.
        response = _register(client, username="ab", email="")
        assert response.status_code == 400
        assert "Alle Felder erforderlich." in response.data.decode()

    def test_short_username(self, client):
        response = _register(client, username="ab")
        assert response.status_code == 400
        assert (
            "Benutzername muss zwischen 3 und 50 Zeichen lang sein."
            in response.data.decode()
        )

    def test_short_password(self, client):
        response = _register(client, password="kurz", password_confirm="kurz")
        assert response.status_code == 400
        assert "Passwort muss mindestens 8 Zeichen lang sein." in response.data.decode()

    def test_password_mismatch(self, client):
        response = _register(client, password_confirm="etwasanderes")
        assert response.status_code == 400
        assert "Passwörter stimmen nicht überein." in response.data.decode()

    def test_invalid_email(self, client):
        response = _register(client, email="keine-email")
        assert response.status_code == 400
        assert "Ungültige E-Mail-Adresse." in response.data.decode()

    def test_duplicate_username(self, client, user):
        response = _register(client, username="testuser")
        assert response.status_code == 409
        assert "Benutzername bereits vergeben." in response.data.decode()

    def test_successful_registration_redirects(self, client):
        response = _register(client)
        assert response.status_code == 302

    def test_username_is_stripped(self, client, db):
        response = _register(client, username="  neueruser  ")
        assert response.status_code == 302
        assert db.get_user_by_username("neueruser") is not None


class TestRegistrationGate:
    def test_disabled_blocks_get_and_post(self, app, client, user):
        app.config["REGISTRATION_ENABLED"] = False

        assert client.get("/auth/register").status_code == 403
        response = _register(client)
        assert response.status_code == 403
        assert "Die Registrierung ist deaktiviert." in response.data.decode()

    def test_disabled_still_allows_first_user(self, app, client):
        app.config["REGISTRATION_ENABLED"] = False

        response = _register(client)
        assert response.status_code == 302

    def test_wrong_invite_code_rejected(self, app, client):
        app.config["REGISTRATION_INVITE_CODE"] = "geheim123"

        response = _register(client, invite_code="falsch")
        assert response.status_code == 403
        assert "Ungültiger Einladungscode." in response.data.decode()

    def test_missing_invite_code_rejected(self, app, client):
        app.config["REGISTRATION_INVITE_CODE"] = "geheim123"

        response = _register(client)
        assert response.status_code == 403

    def test_correct_invite_code_accepted(self, app, client):
        app.config["REGISTRATION_INVITE_CODE"] = "geheim123"

        response = _register(client, invite_code="geheim123")
        assert response.status_code == 302

    def test_login_page_hides_register_link_when_disabled(self, app, client):
        app.config["REGISTRATION_ENABLED"] = False

        html = client.get("/auth/login").data.decode()
        assert "Jetzt registrieren" not in html


class TestLoginForm:
    def test_missing_credentials(self, client):
        response = client.post("/auth/login", data={"username": "", "password": ""})
        assert response.status_code == 400
        assert "Benutzername und Passwort erforderlich." in response.data.decode()

    def test_wrong_credentials(self, client, user):
        response = client.post(
            "/auth/login", data={"username": "testuser", "password": "falsch1234"}
        )
        assert response.status_code == 401
        assert "Ungültige Anmeldedaten." in response.data.decode()

    def test_successful_login_redirects(self, client, user):
        response = client.post(
            "/auth/login", data={"username": "testuser", "password": "testpassword"}
        )
        assert response.status_code == 302


class TestChangePasswordForm:
    def test_wrong_current_password_wins(self, logged_in_client):
        # Wrong current password AND a too-short new password: the 401
        # must win, matching the previous check order.
        response = logged_in_client.post(
            "/auth/change-password",
            data={
                "current_password": "falsch",
                "new_password": "kurz",
                "new_password_confirm": "kurz",
            },
        )
        assert response.status_code == 401
        assert "Aktuelles Passwort ist falsch." in response.data.decode()

    def test_short_new_password(self, logged_in_client):
        response = logged_in_client.post(
            "/auth/change-password",
            data={
                "current_password": "testpassword",
                "new_password": "kurz",
                "new_password_confirm": "kurz",
            },
        )
        assert response.status_code == 400
        assert (
            "Neues Passwort muss mindestens 8 Zeichen lang sein."
            in response.data.decode()
        )

    def test_new_password_mismatch(self, logged_in_client):
        response = logged_in_client.post(
            "/auth/change-password",
            data={
                "current_password": "testpassword",
                "new_password": "langesneues1",
                "new_password_confirm": "langesneues2",
            },
        )
        assert response.status_code == 400
        assert "Neue Passwörter stimmen nicht überein." in response.data.decode()

    def test_successful_change(self, logged_in_client, client):
        response = logged_in_client.post(
            "/auth/change-password",
            data={
                "current_password": "testpassword",
                "new_password": "ganzneuespasswort",
                "new_password_confirm": "ganzneuespasswort",
            },
        )
        assert response.status_code == 200
        assert "Passwort erfolgreich geändert." in response.data.decode()

        login = client.post(
            "/auth/login",
            data={"username": "testuser", "password": "ganzneuespasswort"},
        )
        assert login.status_code == 302
