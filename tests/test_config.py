"""
Tests for configuration: persisted SECRET_KEY and session cookie flags.
"""

import os
import stat

import pytest
from flask import Flask
from werkzeug.middleware.proxy_fix import ProxyFix

from pdf_annotator.app import create_app
from pdf_annotator.config import ProductionConfig, _load_or_create_secret_key


class TestLoadOrCreateSecretKey:
    """Tests for the persistent secret key helper."""

    def test_creates_key_file_with_restrictive_permissions(self, tmp_path):
        key = _load_or_create_secret_key(tmp_path)

        key_file = tmp_path / "secret_key"
        assert key_file.exists()
        assert key_file.read_text().strip() == key
        assert len(key) == 64  # token_hex(32)
        mode = stat.S_IMODE(key_file.stat().st_mode)
        assert mode == 0o600

    def test_reuses_existing_key(self, tmp_path):
        first = _load_or_create_secret_key(tmp_path)
        second = _load_or_create_secret_key(tmp_path)
        assert first == second

    def test_reads_key_written_externally(self, tmp_path):
        (tmp_path / "secret_key").write_text("my-external-key\n")
        assert _load_or_create_secret_key(tmp_path) == "my-external-key"

    def test_creates_missing_data_dir(self, tmp_path):
        target = tmp_path / "nested" / "data"
        key = _load_or_create_secret_key(target)
        assert (target / "secret_key").read_text().strip() == key


def _make_production_app(tmp_path, monkeypatch) -> Flask:
    """Flask app with ProductionConfig, redirected to tmp paths."""
    monkeypatch.setattr(ProductionConfig, "DATA_DIR", tmp_path)
    app = Flask(__name__)
    app.config.from_object(ProductionConfig)
    app.config.update(
        UPLOAD_FOLDER=tmp_path / "uploads",
        EXPORT_FOLDER=tmp_path / "exports",
        DATABASE_PATH=tmp_path / "annotations.db",
        AI_PROVIDER=None,
    )
    return app


class TestProductionSecretKey:
    """Tests for ProductionConfig.init_app SECRET_KEY handling."""

    def test_env_key_wins(self, tmp_path, monkeypatch):
        monkeypatch.setenv("SECRET_KEY", "from-environment")
        monkeypatch.delenv("PDF_ANNOTATOR_BEHIND_PROXY", raising=False)
        app = _make_production_app(tmp_path, monkeypatch)
        app.config["SECRET_KEY"] = os.environ["SECRET_KEY"]

        ProductionConfig.init_app(app)

        assert app.config["SECRET_KEY"] == "from-environment"
        assert not (tmp_path / "secret_key").exists()

    def test_missing_key_behind_proxy_fails_hard(self, tmp_path, monkeypatch):
        monkeypatch.delenv("SECRET_KEY", raising=False)
        monkeypatch.setenv("PDF_ANNOTATOR_BEHIND_PROXY", "1")
        app = _make_production_app(tmp_path, monkeypatch)

        with pytest.raises(RuntimeError, match="SECRET_KEY"):
            ProductionConfig.init_app(app)

    def test_missing_key_without_proxy_persists_key(self, tmp_path, monkeypatch):
        monkeypatch.delenv("SECRET_KEY", raising=False)
        monkeypatch.delenv("PDF_ANNOTATOR_BEHIND_PROXY", raising=False)
        app = _make_production_app(tmp_path, monkeypatch)

        ProductionConfig.init_app(app)

        persisted = (tmp_path / "secret_key").read_text().strip()
        assert app.config["SECRET_KEY"] == persisted

        # A second app (e.g. another Gunicorn worker) gets the same key
        other = _make_production_app(tmp_path, monkeypatch)
        ProductionConfig.init_app(other)
        assert other.config["SECRET_KEY"] == persisted


class TestSessionCookieFlags:
    """Tests for hardened session cookie attributes."""

    def test_login_cookie_is_httponly_and_lax(self, client, user):
        response = client.post(
            "/auth/login",
            data={"username": "testuser", "password": "testpassword"},
        )

        cookies = response.headers.getlist("Set-Cookie")
        session_cookies = [c for c in cookies if c.startswith("session=")]
        assert session_cookies, "login did not set a session cookie"
        assert "HttpOnly" in session_cookies[0]
        assert "SameSite=Lax" in session_cookies[0]
        # Plain http (desktop/dev) must not mark the cookie Secure
        assert "Secure" not in session_cookies[0]


class TestBehindProxy:
    """Tests for the PDF_ANNOTATOR_BEHIND_PROXY reverse-proxy switch."""

    def test_flag_enables_proxyfix_secure_cookies_and_hsts(self, monkeypatch):
        monkeypatch.setenv("PDF_ANNOTATOR_BEHIND_PROXY", "1")
        app = create_app("testing")

        assert isinstance(app.wsgi_app, ProxyFix)
        assert app.config["SESSION_COOKIE_SECURE"] is True
        assert app.config["REMEMBER_COOKIE_SECURE"] is True
        assert app.config["PREFERRED_URL_SCHEME"] == "https"

        response = app.test_client().get("/health")
        assert response.headers["Strict-Transport-Security"].startswith("max-age=")

    def test_forwarded_proto_reaches_request_scheme(self, monkeypatch):
        monkeypatch.setenv("PDF_ANNOTATOR_BEHIND_PROXY", "1")
        app = create_app("testing")

        seen: dict[str, str] = {}

        @app.route("/_test_scheme")
        def _test_scheme() -> str:
            from flask import request

            seen["scheme"] = request.scheme
            seen["remote_addr"] = request.remote_addr or ""
            return "ok"

        app.test_client().get(
            "/_test_scheme",
            headers={
                "X-Forwarded-Proto": "https",
                "X-Forwarded-For": "203.0.113.7",
            },
        )
        assert seen["scheme"] == "https"
        assert seen["remote_addr"] == "203.0.113.7"

    def test_without_flag_no_proxyfix_and_no_hsts(self, client, app):
        assert not isinstance(app.wsgi_app, ProxyFix)
        response = client.get("/health")
        assert "Strict-Transport-Security" not in response.headers
