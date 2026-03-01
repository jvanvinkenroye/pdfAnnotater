"""
User model for Flask-Login integration.

Provides User class for authentication and session management.
"""

from flask_login import UserMixin


class User(UserMixin):
    """
    User model implementing Flask-Login UserMixin.

    Represents an authenticated user with ID, username, email, and admin status.
    """

    def __init__(
        self,
        user_id: str,
        username: str,
        email: str,
        is_active: bool = True,
        is_admin: bool = False,
        theme: str | None = None,
    ) -> None:
        """
        Initialize User instance.

        Args:
            user_id: Unique user identifier
            username: Username for login
            email: User email address
            is_active: Whether user account is active (default: True)
            is_admin: Whether user is an administrator (default: False)
            theme: Preferred theme ('light', 'dark', 'brutalist') or None
        """
        self.id = user_id
        self.username = username
        self.email = email
        self._is_active = is_active
        self._is_admin = is_admin
        self.theme = theme

    @property
    def is_active(self) -> bool:
        """Return whether user account is active."""
        return self._is_active

    @property
    def is_admin(self) -> bool:
        """Return whether user is an administrator."""
        return self._is_admin
