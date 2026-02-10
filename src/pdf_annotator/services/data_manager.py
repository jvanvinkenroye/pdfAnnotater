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

    def export_data(self, output_path: Path | None = None) -> Path:
        """
        Export all data to a ZIP archive.

        Args:
            output_path: Optional path for output file.
                        If not provided, creates timestamped file.

        Returns:
            Path to created ZIP file

        Example:
            manager = DataManager(upload_folder)
            zip_path = manager.export_data()
        """
        # Generate output path if not provided
        if output_path is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = (
                self.upload_folder.parent / f"pdf_annotator_backup_{timestamp}.zip"
            )

        # Collect all data
        documents = self.db.get_all_documents()
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
        merge: bool = False,
    ) -> dict[str, Any]:
        """
        Import data from a ZIP archive.

        Args:
            zip_path: Path to ZIP file to import
            merge: If True, merge with existing data. If False, skip existing documents.

        Returns:
            dict with import statistics:
                - documents_imported: Number of documents imported
                - documents_skipped: Number of documents skipped (already exist)
                - annotations_imported: Number of annotations imported

        Raises:
            ValueError: If ZIP file is invalid or incompatible

        Example:
            manager = DataManager(upload_folder)
            stats = manager.import_data(Path("backup.zip"))
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
            for doc_data in metadata.get("documents", []):
                doc_id = doc_data["id"]

                # Validate doc_id is a safe UUID (prevents path traversal)
                from pdf_annotator.utils.validators import validate_doc_id

                is_valid, _ = validate_doc_id(doc_id)
                if not is_valid:
                    stats["documents_skipped"] += 1
                    continue

                # Check if document already exists
                existing = self.db.get_document(doc_id)
                if existing and not merge:
                    stats["documents_skipped"] += 1
                    continue

                # Extract PDF file
                pdf_archive_path = f"{self.PDFS_FOLDER}/{doc_id}.pdf"
                try:
                    pdf_content = zf.read(pdf_archive_path)
                    pdf_dest = self.upload_folder / f"{doc_id}.pdf"

                    # Verify destination is within upload folder
                    if not pdf_dest.resolve().is_relative_to(
                        self.upload_folder.resolve()
                    ):
                        stats["documents_skipped"] += 1
                        continue

                    pdf_dest.write_bytes(pdf_content)
                except KeyError:
                    # PDF not in archive, skip this document
                    stats["documents_skipped"] += 1
                    continue

                # Create or update document in database
                if not existing:
                    self.db.create_document(
                        filename=doc_data["original_filename"],
                        file_path=str(pdf_dest),
                        page_count=doc_data["page_count"],
                        first_name=doc_data.get("first_name", ""),
                        last_name=doc_data.get("last_name", ""),
                        title=doc_data.get("title", ""),
                        year=doc_data.get("year", ""),
                        subject=doc_data.get("subject", ""),
                    )
                    # Update with original doc_id
                    self._update_document_id(doc_data, pdf_dest)

                stats["documents_imported"] += 1

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

    def get_export_info(self) -> dict[str, Any]:
        """
        Get information about what would be exported.

        Returns:
            dict with export preview:
                - document_count: Number of documents
                - annotation_count: Total annotations
                - estimated_size_mb: Estimated archive size
        """
        documents = self.db.get_all_documents()
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
