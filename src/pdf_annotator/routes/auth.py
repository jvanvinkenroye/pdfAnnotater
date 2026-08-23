"""
Authentication routes for login, logout, and registration.

Provides endpoints for user authentication and session management.
"""

import secrets
import sqlite3

from flask import (
    Blueprint,
    current_app,
    jsonify,
    redirect,
    render_template,
    request,
    url_for,
)
from flask.typing import ResponseReturnValue
from flask_login import current_user, login_required, login_user, logout_user
from werkzeug.security import check_password_hash, generate_password_hash

from pdf_annotator.forms import (
    ChangePasswordForm,
    LoginForm,
    RegisterForm,
    _first_error,
)
from pdf_annotator.models.database import DatabaseManager
from pdf_annotator.models.user import User

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")


@auth_bp.route("/login", methods=["GET"])
def login() -> ResponseReturnValue:
    """Display login form."""
    return render_template("auth/login.html")


@auth_bp.route("/login", methods=["POST"])
def login_post() -> ResponseReturnValue:
    """
    Handle login form submission.

    Validates credentials and establishes session.

    Returns:
        Redirect to documents page on success, or re-render login with error
    """
    form = LoginForm()
    if not form.validate_on_submit():
        return render_template("auth/login.html", error=_first_error(form)), 400

    username = form.username.data or ""
    password = form.password.data or ""

    db = DatabaseManager()
    user_data = db.get_user_by_username(username)

    if not user_data or not check_password_hash(user_data["password_hash"], password):
        return (
            render_template("auth/login.html", error="Ungültige Anmeldedaten."),
            401,
        )

    if not user_data["is_active"]:
        return (
            render_template("auth/login.html", error="Benutzerkonto ist deaktiviert."),
            403,
        )

    # Create User object and log in
    user = User(
        user_data["id"],
        user_data["username"],
        user_data["email"],
        bool(user_data["is_active"]),
        bool(user_data.get("is_admin", False)),
        user_data.get("theme"),
    )
    login_user(user)

    return redirect(url_for("upload.list_documents"))


@auth_bp.route("/logout", methods=["GET"])
@login_required
def logout() -> ResponseReturnValue:
    """Log out current user and redirect to login page."""
    logout_user()
    return redirect(url_for("auth.login"))


def _registration_blocked() -> ResponseReturnValue | None:
    """
    Return a 403 response when self-registration is disabled.

    The very first user may always register (a locked-down fresh install
    still needs its initial admin account).
    """
    if current_app.config.get("REGISTRATION_ENABLED", True):
        return None
    db = DatabaseManager()
    if db.count_users() == 0:
        return None
    return (
        render_template(
            "auth/register.html",
            error=(
                "Die Registrierung ist deaktiviert. "
                "Bitte wenden Sie sich an den Administrator."
            ),
        ),
        403,
    )


@auth_bp.route("/register", methods=["GET"])
def register() -> ResponseReturnValue:
    """Display registration form."""
    blocked = _registration_blocked()
    if blocked:
        return blocked
    return render_template("auth/register.html")


@auth_bp.route("/register", methods=["POST"])
def register_post() -> ResponseReturnValue:
    """
    Handle registration form submission.

    Validates input and creates new user account.

    Returns:
        Redirect to documents page on success, or re-render register with error
    """
    blocked = _registration_blocked()
    if blocked:
        return blocked

    form = RegisterForm()
    if not form.validate_on_submit():
        return render_template("auth/register.html", error=_first_error(form)), 400

    invite_code = current_app.config.get("REGISTRATION_INVITE_CODE")
    if invite_code and not secrets.compare_digest(
        form.invite_code.data or "", invite_code
    ):
        return (
            render_template("auth/register.html", error="Ungültiger Einladungscode."),
            403,
        )

    username = form.username.data or ""
    email = form.email.data or ""
    password = form.password.data or ""

    db = DatabaseManager()

    # Check if username already exists
    if db.get_user_by_username(username):
        return (
            render_template(
                "auth/register.html",
                error="Benutzername bereits vergeben.",
            ),
            409,
        )

    # Create user
    password_hash = generate_password_hash(password)
    try:
        user_id = db.create_user(username, email, password_hash)
    except sqlite3.IntegrityError:
        return (
            render_template(
                "auth/register.html",
                error="Registrierung fehlgeschlagen. E-Mail möglicherweise bereits verwendet.",
            ),
            409,
        )

    # Make first user an admin
    is_first_user = db.count_users() == 1
    if is_first_user:
        db.set_user_admin(user_id, True)

    # Log in automatically
    user = User(user_id, username, email, True, is_first_user)
    login_user(user)

    return redirect(url_for("upload.list_documents"))


@auth_bp.route("/change-password", methods=["GET"])
@login_required
def change_password() -> ResponseReturnValue:
    """Display change-password form."""
    return render_template("auth/change_password.html")


@auth_bp.route("/change-password", methods=["POST"])
@login_required
def change_password_post() -> ResponseReturnValue:
    """
    Handle change-password form submission.

    Verifies the current password before setting the new one.

    Returns:
        Redirect to documents page on success, or re-render form with error
    """
    form = ChangePasswordForm()

    # Verify the current password before any format validation, matching
    # the previous behavior (wrong current password wins with a 401).
    db = DatabaseManager()
    user_data = db.get_user_by_id(current_user.id)

    if not user_data or not check_password_hash(
        user_data["password_hash"], form.current_password.data or ""
    ):
        return (
            render_template(
                "auth/change_password.html",
                error="Aktuelles Passwort ist falsch.",
            ),
            401,
        )

    if not form.validate_on_submit():
        return (
            render_template("auth/change_password.html", error=_first_error(form)),
            400,
        )

    db.update_password(
        current_user.id, generate_password_hash(form.new_password.data or "")
    )

    return render_template(
        "auth/change_password.html", success="Passwort erfolgreich geändert."
    )


@auth_bp.route("/theme", methods=["POST"])
@login_required
def set_theme() -> ResponseReturnValue:
    """
    Save theme preference for the current user.

    Accepts JSON body with 'theme' key (light/dark/brutalist/compact).
    """
    data = request.get_json(silent=True) or {}
    theme = data.get("theme")
    if theme not in ("light", "dark", "brutalist", "compact"):
        return jsonify({"error": "Ungültiges Theme"}), 400
    db = DatabaseManager()
    db.set_user_theme(current_user.id, theme)
    return jsonify({"success": True})
