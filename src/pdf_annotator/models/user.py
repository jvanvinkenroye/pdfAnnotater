"""
User model for Flask-Login integration.

Provides User class for authentication and session management.
"""

from flask_login import UserMixin


class User(UserMixin):
    """
    User model implementing Flask-Login UserMixin.

    Represents an authenticated user with ID, username, and email.
    """

    def __init__(
        self, user_id: str, username: str, email: str, is_active: bool = True
    ) -> None:
        """
        Initialize User instance.

        Args:
            user_id: Unique user identifier
            username: Username for login
            email: User email address
            is_active: Whether user account is active (default: True)
        """
        self.id = user_id
        self.username = username
        self.email = email
        self._is_active = is_active

    @property
    def is_active(self) -> bool:
        """Return whether user account is active."""
        return self._is_active
