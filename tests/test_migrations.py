"""
Tests for versioned schema migrations and the de-singletoned DatabaseManager.
"""

import sqlite3

from pdf_annotator.models.database import DatabaseManager
from pdf_annotator.models.migrations import MIGRATIONS, apply_migrations


def _user_version(db_path) -> int:
    conn = sqlite3.connect(str(db_path))
    try:
        return int(conn.execute("PRAGMA user_version").fetchone()[0])
    finally:
        conn.close()


class TestMigrations:
    def test_fresh_db_is_stamped_to_latest_version(self, tmp_path):
        db_path = tmp_path / "fresh.db"
        DatabaseManager(db_path).init_db()

        assert _user_version(db_path) == len(MIGRATIONS)

    def test_init_db_is_idempotent(self, tmp_path):
        db_path = tmp_path / "twice.db"
        db = DatabaseManager(db_path)
        db.init_db()
        db.init_db()

        assert _user_version(db_path) == len(MIGRATIONS)

    def test_legacy_unversioned_db_migrates_and_keeps_data(self, tmp_path):
        """A database created before versioning (user_version 0, partial
        schema, existing rows) converges and is stamped."""
        db_path = tmp_path / "legacy.db"
        conn = sqlite3.connect(str(db_path))
        # Old-style users table without is_admin/theme columns.
        conn.execute(
            """
            CREATE TABLE users (
                id TEXT PRIMARY KEY,
                username TEXT NOT NULL UNIQUE,
                email TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_active INTEGER DEFAULT 1
            )
            """
        )
        conn.execute(
            "INSERT INTO users (id, username, email, password_hash)"
            " VALUES ('u1', 'alt', 'alt@example.com', 'hash')"
        )
        conn.commit()
        conn.close()
        assert _user_version(db_path) == 0

        db = DatabaseManager(db_path)
        db.init_db()

        assert _user_version(db_path) == len(MIGRATIONS)
        user = db.get_user_by_username("alt")
        assert user is not None
        assert user["email"] == "alt@example.com"
        # Columns added by the baseline migration exist and default sanely.
        assert user.get("is_admin") in (0, None, False)

    def test_apply_migrations_runs_only_pending(self, tmp_path):
        db_path = tmp_path / "pending.db"
        conn = sqlite3.connect(str(db_path))
        apply_migrations(conn)
        version = conn.execute("PRAGMA user_version").fetchone()[0]
        # Re-running applies nothing and keeps the stamp.
        apply_migrations(conn)
        assert conn.execute("PRAGMA user_version").fetchone()[0] == version
        conn.close()


class TestNoSingleton:
    def test_two_instances_use_their_own_paths(self, tmp_path):
        """Regression test for the old singleton, which ignored the path
        passed to every constructor call after the first."""
        db_a = DatabaseManager(tmp_path / "a.db")
        db_b = DatabaseManager(tmp_path / "b.db")
        db_a.init_db()
        db_b.init_db()

        db_a.create_user("nur_in_a", "a@example.com", "hash")

        assert db_a.get_user_by_username("nur_in_a") is not None
        assert db_b.get_user_by_username("nur_in_a") is None

    def test_app_uses_configured_database(self, app):
        from pdf_annotator.models.database import get_db

        with app.app_context():
            assert str(get_db()._db_path) == str(app.config["DATABASE_PATH"])
