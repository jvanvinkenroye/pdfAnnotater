#!/usr/bin/env python3
"""
Import DAA Praktikumsberichte aus dem iCloud-Verzeichnis in die lokale
PDF-Annotator-Installation (Production-Datenbank).

Verzeichnisstruktur: Nachname_Vorname/Datei.pdf
"""

import shutil
import sqlite3
import sys
from pathlib import Path
from uuid import uuid4

SOURCE_DIR = Path(
    "/Users/java/Library/Mobile Documents/com~apple~CloudDocs"
    "/111_CloudSync/08_DAA/DAA_BKST_BERICHTE_99_scans"
)

DATA_DIR = Path("/Users/java/Library/Application Support/PDF-Annotator")
UPLOAD_DIR = DATA_DIR / "uploads"
DB_PATH = DATA_DIR / "annotations.db"

SUBJECT = "Praxisbericht"


def parse_name(dir_name: str) -> tuple[str, str]:
    """Parst Verzeichnisname in (Nachname, Vorname).

    Formate:
      Nachname_Vorname        -> ('Nachname', 'Vorname')
      Nachname_Vorname_Zweiter -> ('Nachname', 'Vorname Zweiter')
      Nachname-Vorname        -> ('Nachname', 'Vorname')  (falls kein Unterstrich)
    """
    if "_" in dir_name:
        parts = dir_name.split("_", 1)
        last_name = parts[0]
        first_name = parts[1].replace("_", " ")
    elif "-" in dir_name:
        parts = dir_name.split("-", 1)
        last_name = parts[0]
        first_name = parts[1]
    else:
        last_name = dir_name
        first_name = ""
    return last_name, first_name


def get_page_count(pdf_path: Path) -> int:
    """Ermittelt Seitenanzahl via PyMuPDF."""
    try:
        import fitz  # type: ignore

        doc = fitz.open(str(pdf_path))
        count = doc.page_count
        doc.close()
        return count
    except Exception as e:
        print(f"  Warnung: Seitenanzahl konnte nicht ermittelt werden: {e}")
        return 1


def document_already_imported(conn: sqlite3.Connection, original_filename: str) -> bool:
    """Prueft ob eine Datei mit diesem Namen bereits importiert wurde."""
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id FROM documents WHERE original_filename = ?",
        (original_filename,),
    )
    return cursor.fetchone() is not None


def import_pdf(conn: sqlite3.Connection, pdf_path: Path, dir_name: str) -> str | None:
    """Importiert eine PDF-Datei und gibt die doc_id zurueck."""
    original_filename = pdf_path.name

    if document_already_imported(conn, original_filename):
        print(f"  Uebersprungen (bereits vorhanden): {original_filename}")
        return None

    last_name, first_name = parse_name(dir_name)
    page_count = get_page_count(pdf_path)

    # UUID-Dateiname fuer den Upload-Ordner
    storage_id = str(uuid4())
    storage_filename = f"{storage_id}.pdf"
    storage_path = UPLOAD_DIR / storage_filename

    shutil.copy2(str(pdf_path), str(storage_path))

    doc_id = str(uuid4())
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO documents
            (id, original_filename, file_path, page_count,
             first_name, last_name, title, year, subject)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            doc_id,
            original_filename,
            str(storage_path),
            page_count,
            first_name,
            last_name,
            "",
            "",
            SUBJECT,
        ),
    )

    for page_num in range(1, page_count + 1):
        cursor.execute(
            """
            INSERT INTO annotations (doc_id, page_number, note_text)
            VALUES (?, ?, ?)
            """,
            (doc_id, page_num, ""),
        )

    conn.commit()
    return doc_id


def main() -> None:
    if not SOURCE_DIR.exists():
        print(f"Fehler: Quellverzeichnis nicht gefunden: {SOURCE_DIR}")
        sys.exit(1)

    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(str(DB_PATH))
    conn.execute("PRAGMA foreign_keys = ON")

    imported = 0
    skipped = 0
    errors = 0

    subdirs = sorted(
        d for d in SOURCE_DIR.iterdir() if d.is_dir() and d.name != "venv"
    )

    print(f"Verarbeite {len(subdirs)} Verzeichnisse aus:\n  {SOURCE_DIR}\n")

    for subdir in subdirs:
        pdfs = list(subdir.glob("*.pdf"))
        if not pdfs:
            print(f"[SKIP] {subdir.name}: Keine PDF-Datei gefunden")
            skipped += 1
            continue

        for pdf_path in pdfs:
            last_name, first_name = parse_name(subdir.name)
            print(f"[IMPORT] {subdir.name}/{pdf_path.name}  ({last_name}, {first_name})")
            try:
                doc_id = import_pdf(conn, pdf_path, subdir.name)
                if doc_id:
                    imported += 1
                    print(f"  -> doc_id: {doc_id}")
                else:
                    skipped += 1
            except Exception as e:
                print(f"  FEHLER: {e}")
                errors += 1

    conn.close()

    print(f"\nFertig: {imported} importiert, {skipped} uebersprungen, {errors} Fehler")


if __name__ == "__main__":
    main()
