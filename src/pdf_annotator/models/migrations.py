"""
Versioned schema migrations, tracked via SQLite's PRAGMA user_version.

Each entry in MIGRATIONS upgrades the schema by one version; a database
at version N gets MIGRATIONS[N:] applied in order and is stamped after
each step. New schema changes are added as a new function appended to
MIGRATIONS — never by editing an existing one.
"""

import sqlite3
from collections.abc import Callable

Migration = Callable[[sqlite3.Connection], None]


def _m001_baseline(conn: sqlite3.Connection) -> None:
    """
    Initial schema: users, documents, annotations, indices, trigger.

    Deliberately idempotent (IF NOT EXISTS / try-ALTER): databases created
    before schema versioning existed are at user_version 0 but already
    contain some or all of this schema. Running the baseline converges
    them and they get stamped to version 1 like a fresh database.
    """
    cursor = conn.cursor()

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY,
            username TEXT NOT NULL UNIQUE,
            email TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_active INTEGER DEFAULT 1
        )
    """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS documents (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            original_filename TEXT NOT NULL,
            file_path TEXT NOT NULL,
            page_count INTEGER NOT NULL,
            first_name TEXT DEFAULT '',
            last_name TEXT DEFAULT '',
            title TEXT DEFAULT '',
            year TEXT DEFAULT '',
            subject TEXT DEFAULT '',
            upload_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    """
    )

    # Columns added over time before versioned migrations existed; old
    # databases may miss any subset of them.
    legacy_columns = [
        ("documents", "first_name TEXT DEFAULT ''"),
        ("documents", "last_name TEXT DEFAULT ''"),
        ("documents", "title TEXT DEFAULT ''"),
        ("documents", "year TEXT DEFAULT ''"),
        ("documents", "subject TEXT DEFAULT ''"),
        ("documents", "user_id TEXT"),
        ("users", "is_admin INTEGER DEFAULT 0"),
        ("users", "theme TEXT DEFAULT NULL"),
    ]
    for table, col_def in legacy_columns:
        try:
            cursor.execute(f"ALTER TABLE {table} ADD COLUMN {col_def}")  # noqa: S608
        except sqlite3.OperationalError:
            pass  # Column already exists

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS annotations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            doc_id TEXT NOT NULL,
            page_number INTEGER NOT NULL,
            note_text TEXT DEFAULT '',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (doc_id) REFERENCES documents(id) ON DELETE CASCADE,
            UNIQUE(doc_id, page_number)
        )
    """
    )

    cursor.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_annotations_doc_id
        ON annotations(doc_id)
    """
    )
    cursor.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_annotations_page
        ON annotations(doc_id, page_number)
    """
    )
    cursor.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_annotations_updated_at
        ON annotations(updated_at)
    """
    )

    cursor.execute(
        """
        CREATE TRIGGER IF NOT EXISTS update_annotation_timestamp
        AFTER UPDATE ON annotations
        FOR EACH ROW
        BEGIN
            UPDATE annotations
            SET updated_at = CURRENT_TIMESTAMP
            WHERE id = NEW.id;
        END
    """
    )


def _m002_jobs(conn: sqlite3.Connection) -> None:
    """Background job tracking for OCR and annotated-PDF export."""
    conn.execute(
        """
        CREATE TABLE jobs (
            id TEXT PRIMARY KEY,
            type TEXT NOT NULL,
            doc_id TEXT NOT NULL,
            user_id TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending',
            result_path TEXT,
            result_json TEXT,
            error TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            started_at TIMESTAMP,
            finished_at TIMESTAMP,
            FOREIGN KEY (doc_id) REFERENCES documents(id) ON DELETE CASCADE
        )
        """
    )
    conn.execute("CREATE INDEX idx_jobs_doc_type_status ON jobs(doc_id, type, status)")
    conn.execute("CREATE INDEX idx_jobs_status ON jobs(status)")


MIGRATIONS: list[Migration] = [_m001_baseline, _m002_jobs]


def apply_migrations(conn: sqlite3.Connection) -> None:
    """Bring the connected database up to the latest schema version."""
    current = conn.execute("PRAGMA user_version").fetchone()[0]
    for number, migration in enumerate(MIGRATIONS[current:], start=current + 1):
        migration(conn)
        conn.execute(f"PRAGMA user_version = {number}")
