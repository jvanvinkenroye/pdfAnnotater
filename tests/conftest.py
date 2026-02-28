"""
Test fixtures for PDF Annotator.

Provides shared fixtures for Flask app, database, sample PDFs, and more.
"""

import shutil
from pathlib import Path

import fitz
import pytest
from werkzeug.security import generate_password_hash

from pdf_annotator.app import create_app
from pdf_annotator.models.database import DatabaseManager
from pdf_annotator.models.user import User


@pytest.fixture(autouse=True)
def reset_db_singleton():
    """Reset DatabaseManager singleton between tests."""
    yield
    DatabaseManager._instance = None
    DatabaseManager._db_path = None


@pytest.fixture()
def app(tmp_path):
    """Create Flask app configured for testing."""
    upload_folder = tmp_path / "uploads"
    upload_folder.mkdir()
    export_folder = tmp_path / "exports"
    export_folder.mkdir()
    db_path = tmp_path / "test.db"

    # Reset singleton before creating app so it picks up our db_path
    DatabaseManager._instance = None
    DatabaseManager._db_path = None

    app = create_app("testing")
    app.config["UPLOAD_FOLDER"] = upload_folder
    app.config["EXPORT_FOLDER"] = export_folder
    app.config["DATABASE_PATH"] = db_path

    # Re-init DB with the file-based path (create_app used :memory:
    # which doesn't work across connections)
    DatabaseManager._instance = None
    DatabaseManager._db_path = None
    db = DatabaseManager(db_path)
    db.init_db()

    yield app


@pytest.fixture()
def client(app):
    """Flask test client."""
    return app.test_client()


@pytest.fixture()
def db(tmp_path):
    """DatabaseManager with file-based temp database and default test user."""
    db_path = tmp_path / "test.db"
    manager = DatabaseManager(db_path)
    manager.init_db()

    # Create a default test user for tests that don't care about user_id
    test_user_id = manager.create_user(
        username="dbtest",
        email="dbtest@example.com",
        password_hash=generate_password_hash("password"),
    )

    # Store the test user ID on the manager for tests to access
    manager.test_user_id = test_user_id

    return manager


@pytest.fixture()
def user(app, db):
    """Create a test user in the database."""
    with app.app_context():
        user_id = db.create_user(
            username="testuser",
            email="test@example.com",
            password_hash=generate_password_hash("testpassword"),
        )
    return user_id


@pytest.fixture()
def logged_in_client(app, client, user):
    """Flask test client with authenticated user session."""
    with app.app_context():
        with client:
            # Log in the user
            response = client.post(
                "/auth/login",
                data={
                    "username": "testuser",
                    "password": "testpassword",
                },
                follow_redirects=True,
            )
            # Verify login was successful
            assert response.status_code == 200
            yield client


@pytest.fixture()
def sample_pdf(tmp_path):
    """Create a minimal 2-page test PDF and return its path."""
    pdf_path = tmp_path / "test_document.pdf"
    doc = fitz.open()
    for i in range(2):
        page = doc.new_page(width=595, height=842)  # A4
        page.insert_text((72, 72), f"Test Page {i + 1}", fontsize=24)
    doc.save(str(pdf_path))
    doc.close()
    return pdf_path


@pytest.fixture()
def sample_pdf_3pages(tmp_path):
    """Create a 3-page test PDF."""
    pdf_path = tmp_path / "test_3pages.pdf"
    doc = fitz.open()
    for i in range(3):
        page = doc.new_page(width=595, height=842)
        page.insert_text((72, 72), f"Seite {i + 1}", fontsize=24)
    doc.save(str(pdf_path))
    doc.close()
    return pdf_path


@pytest.fixture()
def sample_document(db, sample_pdf, user):
    """Create a document with annotations in the database."""
    doc_id = db.create_document(
        user_id=user,
        filename="test_document.pdf",
        file_path=str(sample_pdf),
        page_count=2,
        first_name="Max",
        last_name="Mustermann",
        title="Testdokument",
        year="2026",
        subject="Testing",
    )
    db.upsert_annotation(doc_id, 1, "Notiz fuer Seite 1")
    db.upsert_annotation(doc_id, 2, "Notiz fuer Seite 2")
    return doc_id


@pytest.fixture()
def upload_folder(tmp_path):
    """Temporary upload directory."""
    folder = tmp_path / "uploads"
    folder.mkdir()
    return folder


@pytest.fixture()
def export_folder(tmp_path):
    """Temporary export directory."""
    folder = tmp_path / "exports"
    folder.mkdir()
    return folder


@pytest.fixture()
def uploaded_pdf(app, client, sample_pdf, user):
    """Create a document with PDF in the upload folder and return doc_id."""
    with app.app_context():
        upload_path = Path(app.config["UPLOAD_FOLDER"]) / "test.pdf"
        shutil.copy2(sample_pdf, upload_path)

        db = DatabaseManager()
        doc_id = db.create_document(
            user_id=user,
            filename="test_document.pdf",
            file_path=str(upload_path),
            page_count=2,
            first_name="Test",
            last_name="User",
        )
        db.upsert_annotation(doc_id, 1, "")
        db.upsert_annotation(doc_id, 2, "")
        return doc_id


@pytest.fixture()
def uploaded_pdf_3pages(app, client, sample_pdf_3pages, user):
    """Create a 3-page document with PDF in upload folder and return doc_id."""
    with app.app_context():
        upload_path = Path(app.config["UPLOAD_FOLDER"]) / "test_3pages.pdf"
        shutil.copy2(sample_pdf_3pages, upload_path)

        db = DatabaseManager()
        doc_id = db.create_document(
            user_id=user,
            filename="test_3pages.pdf",
            file_path=str(upload_path),
            page_count=3,
            first_name="Test",
            last_name="User",
        )
        db.upsert_annotation(doc_id, 1, "Notiz Seite 1")
        db.upsert_annotation(doc_id, 2, "Notiz Seite 2")
        db.upsert_annotation(doc_id, 3, "Notiz Seite 3")
        return doc_id
