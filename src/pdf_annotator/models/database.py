"""
Database module for PDF Annotator.

Provides SQLite database management with schema creation and CRUD operations
for documents and annotations.
"""

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Optional
from uuid import uuid4


class DatabaseManager:
    """
    Singleton database manager for SQLite operations.

    Handles connection management, schema creation, and all database operations
    for documents and annotations.
    """

    _instance: Optional["DatabaseManager"] = None
    _db_path: Path | None = None

    def __new__(cls, db_path: Path | None = None) -> "DatabaseManager":
        """
        Create or return singleton instance.

        Args:
            db_path: Path to SQLite database file

        Returns:
            DatabaseManager instance
        """
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            if db_path:
                cls._db_path = db_path
            elif cls._db_path is None:
                # Default path
                cls._db_path = Path(__file__).parents[3] / "data" / "annotations.db"
        return cls._instance

    @contextmanager
    def get_connection(self) -> Any:
        """
        Context manager for database connections.

        Yields:
            sqlite3.Connection: Database connection

        Example:
            with db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM documents")
        """
        conn = sqlite3.connect(str(self._db_path), detect_types=sqlite3.PARSE_DECLTYPES)
        conn.row_factory = sqlite3.Row  # Enable column access by name
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def init_db(self) -> None:
        """
        Initialize database schema.

        Creates tables, indices, and triggers if they don't exist.
        Safe to call multiple times (idempotent).
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # Create documents table
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS documents (
                    id TEXT PRIMARY KEY,
                    original_filename TEXT NOT NULL,
                    file_path TEXT NOT NULL,
                    page_count INTEGER NOT NULL,
                    first_name TEXT DEFAULT '',
                    last_name TEXT DEFAULT '',
                    title TEXT DEFAULT '',
                    year TEXT DEFAULT '',
                    subject TEXT DEFAULT '',
                    upload_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """
            )

            # Migrate existing database (add new columns if they don't exist)
            try:
                cursor.execute(
                    "ALTER TABLE documents ADD COLUMN first_name TEXT DEFAULT ''"
                )
            except Exception:
                pass  # Column already exists

            try:
                cursor.execute(
                    "ALTER TABLE documents ADD COLUMN last_name TEXT DEFAULT ''"
                )
            except Exception:
                pass  # Column already exists

            try:
                cursor.execute("ALTER TABLE documents ADD COLUMN title TEXT DEFAULT ''")
            except Exception:
                pass  # Column already exists

            try:
                cursor.execute("ALTER TABLE documents ADD COLUMN year TEXT DEFAULT ''")
            except Exception:
                pass  # Column already exists

            try:
                cursor.execute(
                    "ALTER TABLE documents ADD COLUMN subject TEXT DEFAULT ''"
                )
            except Exception:
                pass  # Column already exists

            # Create annotations table
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

            # Create indices for performance
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

            # Create trigger for automatic updated_at
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

            conn.commit()

    def create_document(
        self,
        filename: str,
        file_path: str,
        page_count: int,
        first_name: str = "",
        last_name: str = "",
        title: str = "",
        year: str = "",
        subject: str = "",
    ) -> str:
        """
        Create a new document entry.

        Args:
            filename: Original filename of uploaded PDF
            file_path: Path where PDF is stored
            page_count: Number of pages in PDF
            first_name: First name of annotator (optional)
            last_name: Last name of annotator (optional)
            title: Document title (optional)
            year: Year (optional)
            subject: Subject/Theme (optional)

        Returns:
            str: UUID of created document

        Example:
            doc_id = db.create_document(
                "report.pdf", "/data/uploads/abc.pdf", 10,
                "Max", "Mustermann", "Projektbericht", "2026", "IT-Sicherheit"
            )
        """
        doc_id = str(uuid4())
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO documents (id, original_filename, file_path, page_count,
                                       first_name, last_name, title, year, subject)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    doc_id,
                    filename,
                    file_path,
                    page_count,
                    first_name,
                    last_name,
                    title,
                    year,
                    subject,
                ),
            )
        return doc_id

    def get_document(self, doc_id: str) -> dict[str, Any] | None:
        """
        Retrieve document by ID.

        Args:
            doc_id: UUID of document

        Returns:
            dict with document data or None if not found

        Example:
            doc = db.get_document("abc-123")
            print(doc["original_filename"], doc["page_count"])
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT id, original_filename, file_path, page_count, upload_timestamp,
                       first_name, last_name, title, year, subject
                FROM documents
                WHERE id = ?
            """,
                (doc_id,),
            )
            row = cursor.fetchone()
            if row:
                return dict(row)
        return None

    def update_document_metadata(
        self,
        doc_id: str,
        first_name: str,
        last_name: str,
        title: str,
        year: str,
        subject: str,
    ) -> bool:
        """
        Update metadata fields for a document.

        Args:
            doc_id: UUID of document
            first_name: First name
            last_name: Last name
            title: Document title
            year: Year
            subject: Subject/theme

        Returns:
            bool: True if successful, False otherwise

        Example:
            success = db.update_document_metadata(
                "abc-123", "Max", "Mustermann", "Projektbericht", "2026", "IT"
            )
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    UPDATE documents
                    SET first_name = ?, last_name = ?, title = ?, year = ?, subject = ?
                    WHERE id = ?
                """,
                    (first_name, last_name, title, year, subject, doc_id),
                )
                return cursor.rowcount > 0
        except Exception:
            return False

    def upsert_annotation(self, doc_id: str, page_number: int, note_text: str) -> None:
        """
        Insert or update annotation for a specific page.

        Uses INSERT OR REPLACE to handle both create and update operations.

        Args:
            doc_id: UUID of document
            page_number: Page number (1-indexed)
            note_text: Content of annotation

        Example:
            db.upsert_annotation("abc-123", 1, "This is a note for page 1")
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            # Check if annotation exists
            cursor.execute(
                """
                SELECT id FROM annotations
                WHERE doc_id = ? AND page_number = ?
            """,
                (doc_id, page_number),
            )
            existing = cursor.fetchone()

            if existing:
                # Update existing annotation
                cursor.execute(
                    """
                    UPDATE annotations
                    SET note_text = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE doc_id = ? AND page_number = ?
                """,
                    (note_text, doc_id, page_number),
                )
            else:
                # Insert new annotation
                cursor.execute(
                    """
                    INSERT INTO annotations (doc_id, page_number, note_text)
                    VALUES (?, ?, ?)
                """,
                    (doc_id, page_number, note_text),
                )

    def get_annotation(self, doc_id: str, page_number: int) -> dict[str, Any] | None:
        """
        Retrieve annotation for a specific page.

        Args:
            doc_id: UUID of document
            page_number: Page number (1-indexed)

        Returns:
            dict with annotation data or None if not found

        Example:
            annotation = db.get_annotation("abc-123", 1)
            if annotation:
                print(annotation["note_text"], annotation["updated_at"])
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT id, doc_id, page_number, note_text, created_at, updated_at
                FROM annotations
                WHERE doc_id = ? AND page_number = ?
            """,
                (doc_id, page_number),
            )
            row = cursor.fetchone()
            if row:
                return dict(row)
        return None

    def get_all_annotations(self, doc_id: str) -> list[dict[str, Any]]:
        """
        Retrieve all annotations for a document, sorted by page number.

        Args:
            doc_id: UUID of document

        Returns:
            List of annotation dicts sorted by page_number

        Example:
            annotations = db.get_all_annotations("abc-123")
            for ann in annotations:
                print(f"Page {ann['page_number']}: {ann['note_text']}")
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT id, doc_id, page_number, note_text, created_at, updated_at
                FROM annotations
                WHERE doc_id = ?
                ORDER BY page_number ASC
            """,
                (doc_id,),
            )
            rows = cursor.fetchall()
            return [dict(row) for row in rows]

    def delete_document(self, doc_id: str) -> bool:
        """
        Delete document and all its annotations (CASCADE).

        Args:
            doc_id: UUID of document

        Returns:
            bool: True if document was deleted, False if not found

        Example:
            if db.delete_document("abc-123"):
                print("Document and annotations deleted")
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM documents WHERE id = ?", (doc_id,))
            return cursor.rowcount > 0

    def get_all_documents(self) -> list[dict[str, Any]]:
        """
        Retrieve all documents, sorted by upload timestamp (newest first).

        Returns:
            List of document dicts

        Example:
            docs = db.get_all_documents()
            for doc in docs:
                print(doc["original_filename"], doc["page_count"])
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT d.id, d.original_filename, d.file_path, d.page_count,
                       d.upload_timestamp, d.first_name, d.last_name, d.title,
                       d.year, d.subject,
                       MAX(a.updated_at) as last_edited
                FROM documents d
                LEFT JOIN annotations a ON d.id = a.doc_id
                GROUP BY d.id
                ORDER BY d.upload_timestamp DESC
            """
            )
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
