"""
Authentication routes for login, logout, and registration.

Provides endpoints for user authentication and session management.
"""

import sqlite3

from flask import Blueprint, redirect, render_template, request, url_for
from flask_login import login_required, login_user, logout_user
from werkzeug.security import check_password_hash, generate_password_hash

from pdf_annotator.models.database import DatabaseManager
from pdf_annotator.models.user import User

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")


@auth_bp.route("/login", methods=["GET"])
def login() -> str:
    """Display login form."""
    return render_template("auth/login.html")


@auth_bp.route("/login", methods=["POST"])
def login_post() -> str | tuple:
    """
    Handle login form submission.

    Validates credentials and establishes session.

    Returns:
        Redirect to documents page on success, or re-render login with error
    """
    username = request.form.get("username", "").strip()
    password = request.form.get("password", "")

    if not username or not password:
        return (
            render_template(
                "auth/login.html", error="Benutzername und Passwort erforderlich."
            ),
            400,
        )

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
    )
    login_user(user)

    return redirect(url_for("upload.list_documents"))


@auth_bp.route("/logout", methods=["GET"])
@login_required
def logout() -> str:
    """Log out current user and redirect to login page."""
    logout_user()
    return redirect(url_for("auth.login"))


@auth_bp.route("/register", methods=["GET"])
def register() -> str:
    """Display registration form."""
    return render_template("auth/register.html")


@auth_bp.route("/register", methods=["POST"])
def register_post() -> str | tuple:
    """
    Handle registration form submission.

    Validates input and creates new user account.

    Returns:
        Redirect to documents page on success, or re-render register with error
    """
    username = request.form.get("username", "").strip()
    email = request.form.get("email", "").strip()
    password = request.form.get("password", "")
    password_confirm = request.form.get("password_confirm", "")

    # Validation
    if not username or not email or not password:
        return (
            render_template(
                "auth/register.html",
                error="Alle Felder erforderlich.",
            ),
            400,
        )

    if len(username) < 3 or len(username) > 50:
        return (
            render_template(
                "auth/register.html",
                error="Benutzername muss zwischen 3 und 50 Zeichen lang sein.",
            ),
            400,
        )

    if len(password) < 8:
        return (
            render_template(
                "auth/register.html",
                error="Passwort muss mindestens 8 Zeichen lang sein.",
            ),
            400,
        )

    if password != password_confirm:
        return (
            render_template(
                "auth/register.html",
                error="Passwörter stimmen nicht überein.",
            ),
            400,
        )

    # Check if email format is valid (basic check)
    if "@" not in email or "." not in email.split("@")[1]:
        return (
            render_template(
                "auth/register.html",
                error="Ungültige E-Mail-Adresse.",
            ),
            400,
        )

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
