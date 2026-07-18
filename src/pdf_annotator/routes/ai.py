"""
AI-assisted note editing route for PDF Annotator.

Stateless text edit/generate endpoint for the note editor's optional AI
assistant. Not tied to any document, so no ownership check is needed —
only authentication and rate limiting.
"""

from typing import Any

from flask import Blueprint, jsonify, request
from flask_login import login_required

from pdf_annotator.services.ai_client import (
    AIConfigError,
    AIFeatureDisabledError,
    AIProviderError,
    generate_text,
)
from pdf_annotator.utils.logger import get_logger
from pdf_annotator.utils.validators import validate_ai_instruction, validate_note_text

logger = get_logger(__name__)

ai_bp = Blueprint("ai", __name__, url_prefix="/viewer/api/ai")

VALID_MODES = {"edit", "generate", "context"}
# Modes that operate on a piece of existing text (note selection or a PDF
# quote) rather than generating from the instruction alone.
MODES_REQUIRING_SOURCE_TEXT = {"edit", "context"}


@ai_bp.route("/text", methods=["POST"])
@login_required
def generate_or_edit_text() -> Any:
    """
    Edit selected note text, generate new note text, or formulate a note
    from a read-only context excerpt (e.g. a PDF quote) via a configured
    AI provider.

    Request Body:
        {
            "mode": "edit" | "generate" | "context",
            "instruction": "free-form instruction",
            "source_text": "selected/context text (required for edit/context)"
        }

    Returns:
        JSON with the AI result or an error response

    Example:
        POST /viewer/api/ai/text
        Body: {"mode": "edit", "instruction": "kürze das", "source_text": "..."}

        Response:
        {"result": "..."}
    """
    try:
        data = request.get_json()
        if not data:
            logger.warning("No JSON data in request")
            return jsonify({"error": "Keine Daten gesendet"}), 400

        mode = data.get("mode")
        if mode not in VALID_MODES:
            return jsonify({"error": "Ungültiger Modus"}), 400

        instruction = data.get("instruction", "")
        is_valid, error_msg = validate_ai_instruction(instruction)
        if not is_valid:
            return jsonify({"error": error_msg}), 400

        source_text = data.get("source_text", "")
        if mode in MODES_REQUIRING_SOURCE_TEXT:
            if not source_text or not source_text.strip():
                return jsonify({"error": "Kein Text ausgewählt"}), 400
            is_valid, error_msg = validate_note_text(source_text)
            if not is_valid:
                return jsonify({"error": error_msg}), 400

        result = generate_text(
            mode,
            instruction,
            source_text if mode in MODES_REQUIRING_SOURCE_TEXT else None,
        )

        return jsonify({"result": result})

    except AIFeatureDisabledError:
        return jsonify({"error": "KI-Funktion ist nicht aktiviert"}), 400
    except AIConfigError as e:
        logger.error("AI config error: %s", e)
        return jsonify({"error": "KI-Dienst nicht konfiguriert"}), 503
    except AIProviderError as e:
        logger.error("AI provider error: %s", e)
        return jsonify({"error": "Interner Serverfehler"}), 500
    except Exception as e:
        logger.error(f"Error in AI text endpoint: {e}", exc_info=True)
        return jsonify({"error": "Interner Serverfehler"}), 500
