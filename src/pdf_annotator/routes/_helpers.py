"""
Shared helpers for route modules.
"""

from collections.abc import Callable
from functools import wraps
from typing import Any, TypeVar

from flask import abort, jsonify, render_template, request
from flask_login import current_user
from werkzeug.exceptions import HTTPException

from pdf_annotator.models.database import DatabaseManager
from pdf_annotator.utils.logger import get_logger
from pdf_annotator.utils.validators import validate_doc_id

logger = get_logger(__name__)

# Endpoints under these paths answer errors as JSON; everything else gets
# the HTML error page. Kept in sync with the blueprints' API surfaces.
_JSON_PATH_PREFIXES = (
    "/viewer/api/",
    "/export",
    "/delete/",
    "/import",
    "/upload",
    "/ai/",
    "/swb/",
    "/auth/theme",
)


def wants_json() -> bool:
    """Whether the current request should receive JSON error responses."""
    if request.path.startswith(_JSON_PATH_PREFIXES):
        return True
    if request.accept_mimetypes.best == "application/json":
        return True
    return bool(request.is_json)


def get_owned_document(doc_id: str) -> dict[str, Any]:
    """
    Validate doc_id, fetch the document, and verify ownership — or abort.

    Aborts with 400 (invalid id), 404 (unknown document), or 403 (owned by
    someone else). The app-level error handlers render the abort as JSON
    or HTML depending on the request (see wants_json). Call this before
    entering any try/except Exception block, which would otherwise swallow
    the HTTPException into a 500.
    """
    is_valid, error_msg = validate_doc_id(doc_id)
    if not is_valid:
        abort(400, description=error_msg)

    db = DatabaseManager()
    doc_info = db.get_document(doc_id)

    if not doc_info:
        logger.warning("Document not found: %s", doc_id)
        abort(404, description="Dokument nicht gefunden")

    if doc_info.get("user_id") != current_user.id:
        logger.warning(
            "Unauthorized access: user %s tried to access document owned by %s",
            current_user.id,
            doc_info.get("user_id"),
        )
        abort(403, description="Nicht berechtigt")

    return doc_info


F = TypeVar("F", bound=Callable[..., Any])


def handle_errors(
    message: str = "Interner Serverfehler",
    html_message: str = "Ein interner Serverfehler ist aufgetreten.",
) -> Callable[[F], F]:
    """
    Replace per-route try/except Exception blocks.

    HTTPExceptions (aborts from get_owned_document etc.) are re-raised so
    they reach the app error handlers. Any other exception is logged and
    answered as 500 with the route's German message — JSON for API paths,
    the HTML error page otherwise.
    """

    def decorator(f: F) -> F:
        @wraps(f)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            try:
                return f(*args, **kwargs)
            except HTTPException:
                raise
            except Exception as e:
                logger.error("Error in %s: %s", request.path, e, exc_info=True)
                if wants_json():
                    return jsonify({"error": message}), 500
                return (
                    render_template(
                        "error.html",
                        error_title="Serverfehler",
                        error_message=html_message,
                    ),
                    500,
                )

        return wrapper  # type: ignore[return-value]

    return decorator
