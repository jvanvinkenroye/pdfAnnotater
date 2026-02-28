"""
Unit tests for DatabaseManager.

Tests CRUD operations, annotations, cascade delete, metadata, and edge cases.
"""


class TestCreateDocument:
    """Test document creation."""

    def test_create_document_returns_uuid(self, db):
        doc_id = db.create_document(
            user_id=db.test_user_id,
            filename="test.pdf",
            file_path="/path/test.pdf",
            page_count=5,
        )
        assert doc_id is not None
        assert len(doc_id) == 36  # UUID format

    def test_create_document_with_metadata(self, db):
        doc_id = db.create_document(
            user_id=db.test_user_id,
            filename="report.pdf",
            file_path="/path/report.pdf",
            page_count=10,
            first_name="Max",
            last_name="Mustermann",
            title="Bericht",
            year="2026",
            subject="Informatik",
        )
        doc = db.get_document(doc_id)
        assert doc["original_filename"] == "report.pdf"
        assert doc["page_count"] == 10
        assert doc["first_name"] == "Max"
        assert doc["last_name"] == "Mustermann"
        assert doc["title"] == "Bericht"
        assert doc["year"] == "2026"
        assert doc["subject"] == "Informatik"

    def test_create_multiple_documents(self, db):
        id1 = db.create_document(
            user_id=db.test_user_id, filename="a.pdf", file_path="/a.pdf", page_count=1
        )
        id2 = db.create_document(
            user_id=db.test_user_id, filename="b.pdf", file_path="/b.pdf", page_count=2
        )
        assert id1 != id2
        docs = db.get_all_documents(user_id=db.test_user_id)
        assert len(docs) == 2


class TestGetDocument:
    """Test document retrieval."""

    def test_get_existing_document(self, db):
        doc_id = db.create_document(
            user_id=db.test_user_id,
            filename="test.pdf",
            file_path="/path/test.pdf",
            page_count=3,
        )
        doc = db.get_document(doc_id)
        assert doc is not None
        assert doc["id"] == doc_id
        assert doc["original_filename"] == "test.pdf"

    def test_get_nonexistent_document_returns_none(self, db):
        doc = db.get_document("nonexistent-uuid")
        assert doc is None


class TestDeleteDocument:
    """Test document deletion."""

    def test_delete_existing_document(self, db):
        doc_id = db.create_document(
            user_id=db.test_user_id,
            filename="test.pdf",
            file_path="/path/test.pdf",
            page_count=2,
        )
        result = db.delete_document(doc_id)
        assert result is True
        assert db.get_document(doc_id) is None

    def test_delete_nonexistent_document_returns_false(self, db):
        result = db.delete_document("nonexistent-uuid")
        assert result is False

    def test_cascade_delete_removes_annotations(self, db):
        doc_id = db.create_document(
            user_id=db.test_user_id,
            filename="test.pdf",
            file_path="/path/test.pdf",
            page_count=2,
        )
        db.upsert_annotation(doc_id, 1, "Note page 1")
        db.upsert_annotation(doc_id, 2, "Note page 2")

        db.delete_document(doc_id)

        # Annotations should be gone
        assert db.get_annotation(doc_id, 1) is None
        assert db.get_annotation(doc_id, 2) is None


class TestAnnotations:
    """Test annotation CRUD."""

    def test_upsert_creates_new_annotation(self, db):
        doc_id = db.create_document(
            user_id=db.test_user_id,
            filename="test.pdf",
            file_path="/path/test.pdf",
            page_count=2,
        )
        db.upsert_annotation(doc_id, 1, "Hello")
        ann = db.get_annotation(doc_id, 1)
        assert ann is not None
        assert ann["note_text"] == "Hello"
        assert ann["page_number"] == 1

    def test_upsert_updates_existing_annotation(self, db):
        doc_id = db.create_document(
            user_id=db.test_user_id,
            filename="test.pdf",
            file_path="/path/test.pdf",
            page_count=2,
        )
        db.upsert_annotation(doc_id, 1, "First version")
        db.upsert_annotation(doc_id, 1, "Updated version")
        ann = db.get_annotation(doc_id, 1)
        assert ann["note_text"] == "Updated version"

    def test_get_annotation_nonexistent_returns_none(self, db):
        doc_id = db.create_document(
            user_id=db.test_user_id,
            filename="test.pdf",
            file_path="/path/test.pdf",
            page_count=2,
        )
        ann = db.get_annotation(doc_id, 99)
        assert ann is None

    def test_get_all_annotations_sorted_by_page(self, db):
        doc_id = db.create_document(
            user_id=db.test_user_id,
            filename="test.pdf",
            file_path="/path/test.pdf",
            page_count=3,
        )
        db.upsert_annotation(doc_id, 3, "Page 3")
        db.upsert_annotation(doc_id, 1, "Page 1")
        db.upsert_annotation(doc_id, 2, "Page 2")

        annotations = db.get_all_annotations(doc_id)
        assert len(annotations) == 3
        assert annotations[0]["page_number"] == 1
        assert annotations[1]["page_number"] == 2
        assert annotations[2]["page_number"] == 3

    def test_get_all_annotations_empty_doc(self, db):
        doc_id = db.create_document(
            user_id=db.test_user_id,
            filename="test.pdf",
            file_path="/path/test.pdf",
            page_count=1,
        )
        annotations = db.get_all_annotations(doc_id)
        assert annotations == []


class TestUpdateMetadata:
    """Test metadata updates."""

    def test_update_metadata_success(self, db):
        doc_id = db.create_document(
            user_id=db.test_user_id,
            filename="test.pdf",
            file_path="/path/test.pdf",
            page_count=1,
        )
        result = db.update_document_metadata(
            doc_id, "Max", "Mustermann", "Titel", "2026", "Thema"
        )
        assert result is True
        doc = db.get_document(doc_id)
        assert doc["first_name"] == "Max"
        assert doc["last_name"] == "Mustermann"

    def test_update_metadata_nonexistent_returns_false(self, db):
        result = db.update_document_metadata("nonexistent", "A", "B", "C", "D", "E")
        assert result is False


class TestDeleteAnnotation:
    """Test single annotation deletion."""

    def test_delete_existing_annotation(self, db):
        doc_id = db.create_document(
            user_id=db.test_user_id,
            filename="test.pdf",
            file_path="/path/test.pdf",
            page_count=3,
        )
        db.upsert_annotation(doc_id, 1, "Page 1")
        db.upsert_annotation(doc_id, 2, "Page 2")

        result = db.delete_annotation(doc_id, 1)
        assert result is True
        assert db.get_annotation(doc_id, 1) is None
        # Other annotations unaffected
        assert db.get_annotation(doc_id, 2) is not None

    def test_delete_nonexistent_annotation_returns_false(self, db):
        doc_id = db.create_document(
            user_id=db.test_user_id,
            filename="test.pdf",
            file_path="/path/test.pdf",
            page_count=2,
        )
        result = db.delete_annotation(doc_id, 99)
        assert result is False


class TestRenumberAnnotations:
    """Test annotation renumbering after page deletion."""

    def test_renumber_shifts_pages_down(self, db):
        doc_id = db.create_document(
            user_id=db.test_user_id,
            filename="test.pdf",
            file_path="/path/test.pdf",
            page_count=3,
        )
        db.upsert_annotation(doc_id, 1, "Page 1")
        db.upsert_annotation(doc_id, 2, "Page 2")
        db.upsert_annotation(doc_id, 3, "Page 3")

        # Simulate deletion of page 2
        db.delete_annotation(doc_id, 2)
        db.renumber_annotations_after_delete(doc_id, 2)

        # Page 1 unchanged
        ann1 = db.get_annotation(doc_id, 1)
        assert ann1["note_text"] == "Page 1"

        # Page 3 is now page 2
        ann2 = db.get_annotation(doc_id, 2)
        assert ann2["note_text"] == "Page 3"

        # Page count updated
        doc = db.get_document(doc_id)
        assert doc["page_count"] == 2


class TestGetAllDocuments:
    """Test listing all documents."""

    def test_get_all_documents_empty(self, db):
        docs = db.get_all_documents(user_id=db.test_user_id)
        assert docs == []

    def test_get_all_documents_includes_last_edited(self, db):
        doc_id = db.create_document(
            user_id=db.test_user_id,
            filename="test.pdf",
            file_path="/path/test.pdf",
            page_count=1,
        )
        db.upsert_annotation(doc_id, 1, "Note")
        docs = db.get_all_documents(user_id=db.test_user_id)
        assert len(docs) == 1
        assert docs[0]["last_edited"] is not None
