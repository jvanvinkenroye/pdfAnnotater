"""
AI-assisted note editing for PDF Annotator.

Dispatches free-form text edit/generate requests to a configured
third-party provider (Anthropic or OpenAI). Disabled unless AI_PROVIDER
is set.
"""

from flask import current_app

from pdf_annotator.utils.logger import get_logger

logger = get_logger(__name__)

DEFAULT_ANTHROPIC_MODEL = "claude-haiku-4-5"
DEFAULT_OPENAI_MODEL = "gpt-4o-mini"

_EDIT_SYSTEM_PROMPT = (
    "Du bearbeitest den Notiztext eines Nutzers gemäß seiner Anweisung. "
    "Gib ausschließlich den bearbeiteten Text zurück, ohne Erklärungen, "
    "Anführungszeichen oder zusätzliche Kommentare."
)
_GENERATE_SYSTEM_PROMPT = (
    "Du formulierst aus Stichpunkten oder einer kurzen Anweisung des Nutzers "
    "einen vollständigen, gut lesbaren Notiztext auf Deutsch. Gib "
    "ausschließlich den Notiztext zurück, ohne Erklärungen, Anführungszeichen "
    "oder zusätzliche Kommentare."
)


class AIProviderError(Exception):
    """Raised when the configured AI provider request fails."""


class AIFeatureDisabledError(AIProviderError):
    """Raised when no AI_PROVIDER is configured."""


class AIConfigError(AIProviderError):
    """Raised when AI_PROVIDER is set but its API key is missing."""


def _build_prompt(instruction: str, source_text: str | None) -> tuple[str, str]:
    """Return (system_prompt, user_prompt) for the given mode."""
    if source_text:
        user_prompt = f"Anweisung: {instruction}\n\nText:\n{source_text}"
        return _EDIT_SYSTEM_PROMPT, user_prompt
    return _GENERATE_SYSTEM_PROMPT, instruction


def _call_anthropic(system_prompt: str, user_prompt: str, model: str) -> str:
    import anthropic

    api_key = current_app.config.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise AIConfigError("ANTHROPIC_API_KEY ist nicht gesetzt")

    client = anthropic.Anthropic(api_key=api_key)
    try:
        response = client.messages.create(
            model=model,
            max_tokens=2048,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
        )
    except anthropic.APIError as e:
        logger.error("Anthropic API error: %s", e)
        raise AIProviderError("Fehler bei der Anfrage an den KI-Dienst") from e

    block = response.content[0]
    if block.type != "text":
        raise AIProviderError("Unerwartete Antwort vom KI-Dienst")
    return block.text.strip()


def _call_openai(system_prompt: str, user_prompt: str, model: str) -> str:
    import openai

    api_key = current_app.config.get("OPENAI_API_KEY")
    if not api_key:
        raise AIConfigError("OPENAI_API_KEY ist nicht gesetzt")

    base_url = current_app.config.get("OPENAI_BASE_URL")
    client = openai.OpenAI(api_key=api_key, base_url=base_url or None)
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )
    except openai.APIError as e:
        logger.error("OpenAI API error: %s", e)
        raise AIProviderError("Fehler bei der Anfrage an den KI-Dienst") from e

    content = response.choices[0].message.content
    return (content or "").strip()


def generate_text(instruction: str, source_text: str | None) -> str:
    """
    Edit or generate note text via the configured AI provider.

    Args:
        instruction: Free-form user instruction
        source_text: Selected text to edit, or None/empty to generate
            new text from the instruction alone

    Raises:
        AIFeatureDisabledError: No AI_PROVIDER configured
        AIConfigError: Provider configured but its API key is missing
        AIProviderError: The provider request itself failed

    Returns:
        The AI-generated/edited text
    """
    provider = current_app.config.get("AI_PROVIDER")
    if not provider:
        raise AIFeatureDisabledError("Keine AI_PROVIDER konfiguriert")

    system_prompt, user_prompt = _build_prompt(instruction, source_text)
    model = current_app.config.get("AI_MODEL")

    if provider == "anthropic":
        return _call_anthropic(
            system_prompt, user_prompt, model or DEFAULT_ANTHROPIC_MODEL
        )
    if provider == "openai":
        return _call_openai(system_prompt, user_prompt, model or DEFAULT_OPENAI_MODEL)

    raise AIConfigError(f"Unbekannter AI_PROVIDER: {provider}")
