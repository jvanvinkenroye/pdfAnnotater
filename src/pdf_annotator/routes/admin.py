"""
Admin routes for user management.

Provides endpoints for listing users and managing their status/privileges.
"""

from functools import wraps
from typing import Any

from flask import Blueprint, Response, abort, jsonify, render_template
from flask_login import current_user, login_required

from pdf_annotator.models.database import DatabaseManager, get_db

admin_bp = Blueprint("admin", __name__)

# Shared logic for the two flag-toggle endpoints; only field-specific
# strings and the setter differ.
_TOGGLE_SPECS: dict[str, dict[str, Any]] = {
    "is_active": {
        "setter": "set_user_active",
        "self_error": "Sie können sich nicht selbst deaktivieren",
        "last_admin_error": "Der letzte Admin kann nicht deaktiviert werden",
        "messages": ("Benutzer aktiviert", "Benutzer deaktiviert"),
    },
    "is_admin": {
        "setter": "set_user_admin",
        "self_error": "Sie können sich nicht selbst entziehen",
        "last_admin_error": "Der letzte Admin kann nicht entrollt werden",
        "messages": ("Admin-Rechte erteilt", "Admin-Rechte entzogen"),
    },
}


def _guard_user_action(
    db: DatabaseManager, user_id: str, self_error: str, last_admin_error: str
) -> tuple[dict[str, Any] | None, tuple[Response, int] | None]:
    """Common preamble: user must exist, must not be the caller, and the
    last admin is protected. Returns (user_data, None) or (None, error)."""
    user_data = db.get_user_by_id(user_id)

    if not user_data:
        return None, (jsonify({"error": "Benutzer nicht gefunden"}), 404)

    if user_id == current_user.id:
        return None, (jsonify({"error": self_error}), 403)

    if user_data["is_admin"] and db.count_admins() <= 1:
        return None, (jsonify({"error": last_admin_error}), 403)

    return user_data, None


def _toggle_user_flag(user_id: str, field: str) -> tuple[Response, int] | Response:
    spec = _TOGGLE_SPECS[field]
    db = get_db()

    user_data, error = _guard_user_action(
        db, user_id, spec["self_error"], spec["last_admin_error"]
    )
    if error:
        return error
    assert user_data is not None

    new_value = not user_data[field]
    success = getattr(db, spec["setter"])(user_id, new_value)

    if success:
        message_on, message_off = spec["messages"]
        return jsonify(
            {
                "success": True,
                field: new_value,
                "message": message_on if new_value else message_off,
            }
        )
    return jsonify({"error": "Fehler beim Aktualisieren"}), 500


def admin_required(f):
    """Decorator to require admin privileges."""

    @wraps(f)
    @login_required
    def decorated(*args, **kwargs):
        if not current_user.is_admin:
            abort(403)
        return f(*args, **kwargs)

    return decorated


@admin_bp.route("/", methods=["GET"])
@admin_required
def index() -> str:
    """Display admin panel with user list."""
    db = get_db()
    users = db.get_all_users()
    return render_template("admin/index.html", users=users, current_user=current_user)


@admin_bp.route("/user/<user_id>/toggle_active", methods=["POST"])
@admin_required
def toggle_active(user_id: str) -> tuple[Response, int] | Response:
    """Toggle user active status (activate/deactivate)."""
    return _toggle_user_flag(user_id, "is_active")


@admin_bp.route("/user/<user_id>/toggle_admin", methods=["POST"])
@admin_required
def toggle_admin(user_id: str) -> tuple[Response, int] | Response:
    """Toggle user admin status."""
    return _toggle_user_flag(user_id, "is_admin")


@admin_bp.route("/user/<user_id>", methods=["DELETE"])
@admin_required
def delete_user(user_id: str) -> tuple[Response, int] | Response:
    """Delete a user and all their documents."""
    db = get_db()

    user_data, error = _guard_user_action(
        db,
        user_id,
        "Sie können sich nicht selbst löschen",
        "Der letzte Admin kann nicht gelöscht werden",
    )
    if error:
        return error
    assert user_data is not None

    success = db.delete_user(user_id)

    if success:
        return jsonify(
            {"success": True, "message": f"Benutzer '{user_data['username']}' gelöscht"}
        )
    return jsonify({"error": "Fehler beim Löschen"}), 500
