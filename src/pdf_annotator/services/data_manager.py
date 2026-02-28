"""
Data export and import service for PDF Annotator.

Provides functionality to backup and restore all application data
including documents, annotations, and PDF files.
"""

import json
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Any

from pdf_annotator.models.database import DatabaseManager
from pdf_annotator.utils.logger import get_logger

logger = get_logger(__name__)


class DataManager:
    """
    Manages export and import of application data.

    Creates ZIP archives containing:
    - metadata.json: Document and annotation data
    - pdfs/: Original PDF files
    """

    METADATA_FILENAME = "metadata.json"
    PDFS_FOLDER = "pdfs"
    EXPORT_VERSION = "1.0"
    MAX_UNCOMPRESSED_SIZE = 500 * 1024 * 1024  # 500 MB safety limit

    def __init__(self, upload_folder: Path, db: DatabaseManager | None = None):
        """
        Initialize DataManager.

        Args:
            upload_folder: Path to uploads directory
            db: DatabaseManager instance (uses singleton if not provided)
        """
        self.upload_folder = Path(upload_folder)
        self.db = db or DatabaseManager()

    def export_data(
        self, doc_ids: list[str] | None = None, output_path: Path | None = None
    ) -> Path:
        """
        Export data to a ZIP archive.

        Args:
            doc_ids: Optional list of document IDs to export.
                    If not provided, exports all documents.
            output_path: Optional path for output file.
                        If not provided, creates timestamped file.

        Returns:
            Path to created ZIP file

        Example:
            manager = DataManager(upload_folder)
            zip_path = manager.export_data(["doc-id-1", "doc-id-2"])
        """
        # Generate output path if not provided
        if output_path is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = (
                self.upload_folder.parent / f"pdf_annotator_backup_{timestamp}.zip"
            )

        # Collect documents to export
        if doc_ids:
            documents = [self.db.get_document(doc_id) for doc_id in doc_ids]
            documents = [doc for doc in documents if doc is not None]
        else:
            # Note: This is for backward compatibility with single-user mode
            # In production, get_all_documents should not be called without user_id
            documents = []
        export_data: dict[str, Any] = {
            "version": self.EXPORT_VERSION,
            "exported_at": datetime.now().isoformat(),
            "documents": [],
        }

        # Create ZIP archive
        with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for doc in documents:
                doc_id = doc["id"]

                # Get all annotations for this document
                annotations = self.db.get_all_annotations(doc_id)

                # Build document entry
                doc_entry = {
                    "id": doc_id,
                    "original_filename": doc["original_filename"],
                    "page_count": doc["page_count"],
                    "first_name": doc.get("first_name", ""),
                    "last_name": doc.get("last_name", ""),
                    "title": doc.get("title", ""),
                    "year": doc.get("year", ""),
                    "subject": doc.get("subject", ""),
                    "upload_timestamp": str(doc.get("upload_timestamp", "")),
                    "annotations": [
                        {
                            "page_number": ann["page_number"],
                            "note_text": ann["note_text"],
                            "created_at": str(ann.get("created_at", "")),
                            "updated_at": str(ann.get("updated_at", "")),
                        }
                        for ann in annotations
                    ],
                }
                export_data["documents"].append(doc_entry)

                # Add PDF file to archive
                pdf_path = Path(doc["file_path"])
                if pdf_path.exists():
                    # Store with original doc_id as filename
                    archive_name = f"{self.PDFS_FOLDER}/{doc_id}.pdf"
                    zf.write(pdf_path, archive_name)

            # Write metadata JSON
            zf.writestr(
                self.METADATA_FILENAME,
                json.dumps(export_data, indent=2, ensure_ascii=False),
            )

        return output_path

    def import_data(
        self,
        zip_path: Path,
        user_id: str | None = None,
        merge: bool = False,
        debug: bool = False,
    ) -> dict[str, Any]:
        """
        Import data from a ZIP archive.

        Args:
            zip_path: Path to ZIP file to import
            user_id: Optional user ID to assign to imported documents (multi-user mode)
            merge: If True, merge with existing data. If False, skip existing documents.
            debug: If True, print debug information (for testing)

        Returns:
            dict with import statistics:
                - documents_imported: Number of documents imported
                - documents_skipped: Number of documents skipped (already exist)
                - annotations_imported: Number of annotations imported

        Raises:
            ValueError: If ZIP file is invalid or incompatible

        Example:
            manager = DataManager(upload_folder)
            stats = manager.import_data(Path("backup.zip"), user_id="user-123")
            print(f"Imported {stats['documents_imported']} documents")
        """
        stats = {
            "documents_imported": 0,
            "documents_skipped": 0,
            "annotations_imported": 0,
        }

        with zipfile.ZipFile(zip_path, "r") as zf:
            # Check total uncompressed size to prevent ZIP bombs
            total_size = sum(info.file_size for info in zf.infolist())
            if total_size > self.MAX_UNCOMPRESSED_SIZE:
                raise ValueError(
                    f"ZIP-Inhalt zu gross ({total_size / (1024 * 1024):.0f} MB). "
                    f"Maximum: {self.MAX_UNCOMPRESSED_SIZE / (1024 * 1024):.0f} MB"
                )

            # Read and validate metadata
            try:
                metadata_content = zf.read(self.METADATA_FILENAME)
                metadata = json.loads(metadata_content)
            except KeyError as e:
                raise ValueError("Invalid backup file: metadata.json not found") from e
            except json.JSONDecodeError as e:
                raise ValueError(
                    "Invalid backup file: metadata.json is corrupted"
                ) from e

            # Check version compatibility
            version = metadata.get("version", "0.0")
            if not self._is_version_compatible(version):
                raise ValueError(f"Incompatible backup version: {version}")

            # Process each document
            for doc_idx, doc_data in enumerate(metadata.get("documents", []), 1):
                from uuid import uuid4

                # IMPORTANT: Always generate a new UUID for imports.
                # This allows multiple users to import the same backup independently;
                # each user gets their own copy with a unique doc_id.
                original_doc_id = doc_data.get("id")
                doc_id = str(uuid4())

                logger.debug("[Import] Doc #%d: %s → %s", doc_idx, original_doc_id, doc_id)

                # Extract PDF file - try original doc_id first, then new doc_id
                pdf_content = None
                pdf_archive_path = f"{self.PDFS_FOLDER}/{original_doc_id}.pdf"
                try:
                    pdf_content = zf.read(pdf_archive_path)
                except KeyError:
                    pdf_archive_path = f"{self.PDFS_FOLDER}/{doc_id}.pdf"
                    try:
                        pdf_content = zf.read(pdf_archive_path)
                    except KeyError:
                        pdf_content = None

                if pdf_content is None:
                    logger.debug("[Import] Skipped doc %s: PDF not found in archive", original_doc_id)
                    stats["documents_skipped"] += 1
                    continue

                try:
                    pdf_dest = self.upload_folder / f"{doc_id}.pdf"

                    # Ensure destination is safe (no path traversal)
                    if not pdf_dest.resolve().is_relative_to(self.upload_folder.resolve()):
                        logger.warning("[Import] Path traversal blocked for doc %s", original_doc_id)
                        stats["documents_skipped"] += 1
                        continue

                    pdf_dest.write_bytes(pdf_content)
                except OSError as e:
                    logger.warning("[Import] File write error for doc %s: %s", original_doc_id, e)
                    stats["documents_skipped"] += 1
                    continue

                # Create document in database with new UUID
                target_user_id = user_id or "imported"
                self.db.create_document(
                    user_id=target_user_id,
                    filename=doc_data["original_filename"],
                    file_path=str(pdf_dest),
                    page_count=doc_data["page_count"],
                    first_name=doc_data.get("first_name", ""),
                    last_name=doc_data.get("last_name", ""),
                    title=doc_data.get("title", ""),
                    year=doc_data.get("year", ""),
                    subject=doc_data.get("subject", ""),
                    doc_id=doc_id,
                )

                stats["documents_imported"] += 1
                logger.debug("[Import] Imported doc %s successfully", doc_id)

                # Import annotations
                for ann_data in doc_data.get("annotations", []):
                    self.db.upsert_annotation(
                        doc_id=doc_id,
                        page_number=ann_data["page_number"],
                        note_text=ann_data["note_text"],
                    )
                    stats["annotations_imported"] += 1

        return stats

    def _update_document_id(self, doc_data: dict, pdf_dest: Path) -> None:
        """
        Update document to use original ID from backup.

        This ensures document IDs remain consistent across backups.
        """
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id FROM documents WHERE file_path = ?",
                (str(pdf_dest),),
            )
            row = cursor.fetchone()
            if row and row["id"] != doc_data["id"]:
                cursor.execute(
                    "UPDATE documents SET id = ? WHERE id = ?",
                    (doc_data["id"], row["id"]),
                )

    def _is_version_compatible(self, version: str) -> bool:
        """
        Check if backup version is compatible with current version.

        Args:
            version: Version string from backup

        Returns:
            True if compatible, False otherwise
        """
        try:
            major, minor = version.split(".")[:2]
            current_major, current_minor = self.EXPORT_VERSION.split(".")[:2]
            # Compatible if same major version
            return major == current_major
        except (ValueError, AttributeError):
            return False

    def get_export_info(self, doc_ids: list[str] | None = None) -> dict[str, Any]:
        """
        Get information about what would be exported.

        Args:
            doc_ids: Optional list of document IDs to include in info.
                    If not provided, includes all documents.

        Returns:
            dict with export preview:
                - document_count: Number of documents
                - annotation_count: Total annotations
                - estimated_size_mb: Estimated archive size
        """
        if doc_ids:
            documents = [self.db.get_document(doc_id) for doc_id in doc_ids]
            documents = [doc for doc in documents if doc is not None]
        else:
            documents = []

        total_annotations = 0
        total_size = 0

        for doc in documents:
            annotations = self.db.get_all_annotations(doc["id"])
            total_annotations += len(annotations)

            pdf_path = Path(doc["file_path"])
            if pdf_path.exists():
                total_size += pdf_path.stat().st_size

        return {
            "document_count": len(documents),
            "annotation_count": total_annotations,
            "estimated_size_mb": round(total_size / (1024 * 1024), 2),
        }
