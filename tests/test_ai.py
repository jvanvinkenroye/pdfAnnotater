"""
Tests for the AI-assisted note editing feature.

Service tests mock the provider SDK clients directly (no real API calls).
Route tests patch the service function to avoid re-mocking SDK internals.
"""

import pytest

from pdf_annotator.services import ai_client
from pdf_annotator.services.ai_client import (
    AIConfigError,
    AIFeatureDisabledError,
    AIProviderError,
    generate_text,
)


class TestGenerateTextDispatch:
    """Test provider dispatch and error handling in generate_text()."""

    def test_disabled_when_no_provider_configured(self, app):
        with app.app_context():
            app.config["AI_PROVIDER"] = None
            with pytest.raises(AIFeatureDisabledError):
                generate_text("kürze das", "Ein langer Text.")

    def test_config_error_when_anthropic_key_missing(self, app):
        with app.app_context():
            app.config["AI_PROVIDER"] = "anthropic"
            app.config["ANTHROPIC_API_KEY"] = None
            with pytest.raises(AIConfigError):
                generate_text("kürze das", "Ein langer Text.")

    def test_config_error_when_openai_key_missing(self, app):
        with app.app_context():
            app.config["AI_PROVIDER"] = "openai"
            app.config["OPENAI_API_KEY"] = None
            with pytest.raises(AIConfigError):
                generate_text("kürze das", "Ein langer Text.")

    def test_anthropic_provider_returns_response_text(self, app, monkeypatch):
        class FakeMessage:
            type = "text"
            text = "  Gekürzter Text.  "

        class FakeResponse:
            content = [FakeMessage()]

        class FakeMessages:
            def create(self, **kwargs):
                assert kwargs["model"] == "claude-haiku-4-5"
                assert "kürze" in kwargs["messages"][0]["content"]
                return FakeResponse()

        class FakeAnthropicClient:
            def __init__(self, api_key):
                self.messages = FakeMessages()

        import anthropic

        monkeypatch.setattr(anthropic, "Anthropic", FakeAnthropicClient)

        with app.app_context():
            app.config["AI_PROVIDER"] = "anthropic"
            app.config["ANTHROPIC_API_KEY"] = "test-key"
            result = generate_text("kürze das", "Ein langer Text.")

        assert result == "Gekürzter Text."

    def test_openai_provider_returns_response_text(self, app, monkeypatch):
        class FakeMessage:
            content = "  Generierter Text.  "

        class FakeChoice:
            message = FakeMessage()

        class FakeResponse:
            choices = [FakeChoice()]

        class FakeCompletions:
            def create(self, **kwargs):
                assert kwargs["model"] == "gpt-4o-mini"
                return FakeResponse()

        class FakeChat:
            def __init__(self):
                self.completions = FakeCompletions()

        class FakeOpenAIClient:
            def __init__(self, api_key):
                self.chat = FakeChat()

        import openai

        monkeypatch.setattr(openai, "OpenAI", FakeOpenAIClient)

        with app.app_context():
            app.config["AI_PROVIDER"] = "openai"
            app.config["OPENAI_API_KEY"] = "test-key"
            result = generate_text("Stichpunkte: A, B, C", None)

        assert result == "Generierter Text."

    def test_generate_mode_omits_source_text_from_prompt(self, app):
        system_prompt, user_prompt = ai_client._build_prompt("mach eine Notiz", None)
        assert user_prompt == "mach eine Notiz"

    def test_edit_mode_includes_source_text_in_prompt(self, app):
        system_prompt, user_prompt = ai_client._build_prompt(
            "kürze das", "Originaltext"
        )
        assert "kürze das" in user_prompt
        assert "Originaltext" in user_prompt


class TestAiTextRoute:
    """Test the /viewer/api/ai/text endpoint."""

    def test_disabled_by_default(self, app, logged_in_client):
        response = logged_in_client.post(
            "/viewer/api/ai/text",
            json={"mode": "generate", "instruction": "Stichpunkte", "source_text": ""},
        )
        assert response.status_code == 400
        assert "nicht aktiviert" in response.get_json()["error"]

    def test_edit_mode_success(self, app, logged_in_client, monkeypatch):
        monkeypatch.setattr(
            "pdf_annotator.routes.ai.generate_text",
            lambda instruction, source_text: "Ergebnis",
        )
        response = logged_in_client.post(
            "/viewer/api/ai/text",
            json={
                "mode": "edit",
                "instruction": "kürze das",
                "source_text": "Langer Text",
            },
        )
        assert response.status_code == 200
        assert response.get_json() == {"result": "Ergebnis"}

    def test_generate_mode_success_without_source_text(
        self, app, logged_in_client, monkeypatch
    ):
        monkeypatch.setattr(
            "pdf_annotator.routes.ai.generate_text",
            lambda instruction, source_text: "Neue Notiz",
        )
        response = logged_in_client.post(
            "/viewer/api/ai/text",
            json={
                "mode": "generate",
                "instruction": "Stichpunkte: A, B",
                "source_text": "",
            },
        )
        assert response.status_code == 200
        assert response.get_json() == {"result": "Neue Notiz"}

    def test_edit_mode_requires_source_text(self, app, logged_in_client, monkeypatch):
        monkeypatch.setattr(
            "pdf_annotator.routes.ai.generate_text",
            lambda instruction, source_text: "x",
        )
        response = logged_in_client.post(
            "/viewer/api/ai/text",
            json={"mode": "edit", "instruction": "kürze das", "source_text": ""},
        )
        assert response.status_code == 400

    def test_invalid_mode_rejected(self, app, logged_in_client):
        response = logged_in_client.post(
            "/viewer/api/ai/text",
            json={"mode": "delete", "instruction": "kürze das", "source_text": "x"},
        )
        assert response.status_code == 400

    def test_instruction_too_long_rejected(self, app, logged_in_client):
        response = logged_in_client.post(
            "/viewer/api/ai/text",
            json={"mode": "generate", "instruction": "x" * 501, "source_text": ""},
        )
        assert response.status_code == 400

    def test_missing_json_body_rejected(self, app, logged_in_client):
        response = logged_in_client.post(
            "/viewer/api/ai/text", data="{}", content_type="application/json"
        )
        assert response.status_code == 400

    def test_requires_login(self, client):
        response = client.post(
            "/viewer/api/ai/text",
            json={"mode": "generate", "instruction": "x", "source_text": ""},
        )
        assert response.status_code in (302, 401)

    def test_provider_error_maps_to_500(self, app, logged_in_client, monkeypatch):
        def raise_error(instruction, source_text):
            raise AIProviderError("boom")

        monkeypatch.setattr("pdf_annotator.routes.ai.generate_text", raise_error)
        response = logged_in_client.post(
            "/viewer/api/ai/text",
            json={"mode": "generate", "instruction": "x", "source_text": ""},
        )
        assert response.status_code == 500

    def test_config_error_maps_to_503(self, app, logged_in_client, monkeypatch):
        def raise_error(instruction, source_text):
            raise AIConfigError("boom")

        monkeypatch.setattr("pdf_annotator.routes.ai.generate_text", raise_error)
        response = logged_in_client.post(
            "/viewer/api/ai/text",
            json={"mode": "generate", "instruction": "x", "source_text": ""},
        )
        assert response.status_code == 503
