"""
Admin routes for user management.

Provides endpoints for listing users and managing their status/privileges.
"""

from functools import wraps

from flask import Blueprint, abort, jsonify, render_template
from flask_login import current_user, login_required

from pdf_annotator.models.database import DatabaseManager

admin_bp = Blueprint("admin", __name__)


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
    db = DatabaseManager()
    users = db.get_all_users()
    return render_template("admin/index.html", users=users, current_user=current_user)


@admin_bp.route("/user/<user_id>/toggle_active", methods=["POST"])
@admin_required
def toggle_active(user_id: str):
    """Toggle user active status (activate/deactivate)."""
    db = DatabaseManager()
    user_data = db.get_user_by_id(user_id)

    if not user_data:
        return jsonify({"error": "Benutzer nicht gefunden"}), 404

    # Admin cannot deactivate themselves
    if user_id == current_user.id:
        return (
            jsonify({"error": "Sie können sich nicht selbst deaktivieren"}),
            403,
        )

    # Don't allow deactivating the last admin
    if user_data["is_admin"]:
        if db.count_admins() <= 1:
            return (
                jsonify({"error": "Der letzte Admin kann nicht deaktiviert werden"}),
                403,
            )

    new_is_active = not user_data["is_active"]
    success = db.set_user_active(user_id, new_is_active)

    if success:
        return jsonify(
            {
                "success": True,
                "is_active": new_is_active,
                "message": (
                    "Benutzer aktiviert" if new_is_active else "Benutzer deaktiviert"
                ),
            }
        )
    return jsonify({"error": "Fehler beim Aktualisieren"}), 500


@admin_bp.route("/user/<user_id>/toggle_admin", methods=["POST"])
@admin_required
def toggle_admin(user_id: str):
    """Toggle user admin status."""
    db = DatabaseManager()
    user_data = db.get_user_by_id(user_id)

    if not user_data:
        return jsonify({"error": "Benutzer nicht gefunden"}), 404

    # Admin cannot remove their own admin privileges
    if user_id == current_user.id:
        return (
            jsonify({"error": "Sie können sich nicht selbst entziehen"}),
            403,
        )

    # Don't allow removing the last admin
    if user_data["is_admin"]:
        if db.count_admins() <= 1:
            return (
                jsonify({"error": "Der letzte Admin kann nicht entrollt werden"}),
                403,
            )

    new_is_admin = not user_data["is_admin"]
    success = db.set_user_admin(user_id, new_is_admin)

    if success:
        return jsonify(
            {
                "success": True,
                "is_admin": new_is_admin,
                "message": (
                    "Admin-Rechte erteilt" if new_is_admin else "Admin-Rechte entzogen"
                ),
            }
        )
    return jsonify({"error": "Fehler beim Aktualisieren"}), 500


@admin_bp.route("/user/<user_id>", methods=["DELETE"])
@admin_required
def delete_user(user_id: str):
    """Delete a user and all their documents."""
    db = DatabaseManager()
    user_data = db.get_user_by_id(user_id)

    if not user_data:
        return jsonify({"error": "Benutzer nicht gefunden"}), 404

    # Admin cannot delete themselves
    if user_id == current_user.id:
        return jsonify({"error": "Sie können sich nicht selbst löschen"}), 403

    # Don't allow deleting the last admin
    if user_data["is_admin"]:
        if db.count_admins() <= 1:
            return jsonify(
                {"error": "Der letzte Admin kann nicht gelöscht werden"}
            ), 403

    success = db.delete_user(user_id)

    if success:
        return jsonify(
            {"success": True, "message": f"Benutzer '{user_data['username']}' gelöscht"}
        )
    return jsonify({"error": "Fehler beim Löschen"}), 500
