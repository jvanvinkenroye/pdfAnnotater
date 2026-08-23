"""
Form definitions for the authentication views.

Validation rules and every user-facing message mirror the previous
hand-rolled checks in routes/auth.py exactly; only the mechanics moved
into Flask-WTF form classes.
"""

from flask_wtf import FlaskForm
from wtforms import PasswordField, StringField
from wtforms.validators import DataRequired, EqualTo, Length, ValidationError


def _strip(value: str | None) -> str | None:
    return value.strip() if isinstance(value, str) else value


def _first_error(form: FlaskForm) -> str | None:
    """
    Return the message to show for a failed validation.

    Missing-field (DataRequired) errors win over format errors regardless
    of field order, mirroring the previous checks which tested presence of
    all fields first.
    """
    for field in form:
        if field.errors and not field.data:
            return str(field.errors[0])
    for field in form:
        if field.errors:
            return str(field.errors[0])
    return None


class LoginForm(FlaskForm):
    username = StringField(
        "Benutzername",
        filters=[_strip],
        validators=[DataRequired(message="Benutzername und Passwort erforderlich.")],
    )
    password = PasswordField(
        "Passwort",
        validators=[DataRequired(message="Benutzername und Passwort erforderlich.")],
    )


class RegisterForm(FlaskForm):
    username = StringField(
        "Benutzername",
        filters=[_strip],
        validators=[
            DataRequired(message="Alle Felder erforderlich."),
            Length(
                min=3,
                max=50,
                message="Benutzername muss zwischen 3 und 50 Zeichen lang sein.",
            ),
        ],
    )
    email = StringField(
        "E-Mail",
        filters=[_strip],
        validators=[DataRequired(message="Alle Felder erforderlich.")],
    )
    password = PasswordField(
        "Passwort",
        validators=[
            DataRequired(message="Alle Felder erforderlich."),
            Length(min=8, message="Passwort muss mindestens 8 Zeichen lang sein."),
        ],
    )
    password_confirm = PasswordField(
        "Passwort bestätigen",
        validators=[
            EqualTo("password", message="Passwörter stimmen nicht überein."),
        ],
    )

    def validate_email(self, field: StringField) -> None:
        # Same basic check as before; deliberately permissive so no
        # previously accepted address is rejected now.
        email = field.data or ""
        if "@" not in email or "." not in email.split("@")[1]:
            raise ValidationError("Ungültige E-Mail-Adresse.")


class ChangePasswordForm(FlaskForm):
    current_password = PasswordField(
        "Aktuelles Passwort",
        validators=[DataRequired(message="Aktuelles Passwort ist falsch.")],
    )
    new_password = PasswordField(
        "Neues Passwort",
        validators=[
            DataRequired(message="Neues Passwort muss mindestens 8 Zeichen lang sein."),
            Length(
                min=8, message="Neues Passwort muss mindestens 8 Zeichen lang sein."
            ),
        ],
    )
    new_password_confirm = PasswordField(
        "Neues Passwort bestätigen",
        validators=[
            EqualTo("new_password", message="Neue Passwörter stimmen nicht überein."),
        ],
    )
