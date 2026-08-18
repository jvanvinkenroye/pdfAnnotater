"""
OCR service for PDF Annotator.

Adds a searchable text layer to scanned PDFs via ocrmypdf, so the
viewer's selectable text overlay has words to work with. Requires the
tesseract binary (plus language data) at runtime.
"""

import shutil
import subprocess
import sys
from pathlib import Path

from pdf_annotator.utils.logger import get_logger

logger = get_logger(__name__)

OCR_TIMEOUT_SECONDS = 600


class OCRError(Exception):
    """Raised when OCR processing fails."""


def ocr_available() -> bool:
    """Check whether the tesseract binary is available at runtime."""
    return shutil.which("tesseract") is not None


def ocr_pdf(file_path: Path, language: str = "deu+eng") -> None:
    """
    Run OCR on a PDF in place, adding a searchable text layer.

    Uses ocrmypdf's --skip-text mode so pages that already contain text
    are left untouched and only image-only pages get OCRed. The original
    file is only replaced after a successful run (temp file + replace).

    Args:
        file_path: Path to the PDF to OCR
        language: Tesseract language(s), e.g. "deu+eng"

    Raises:
        OCRError: If tesseract is missing or the OCR run fails
    """
    if not ocr_available():
        raise OCRError("Tesseract ist nicht installiert")

    tmp_out = file_path.with_suffix(".ocr.pdf")
    # Run ocrmypdf via its CLI in a subprocess: its Python API is not
    # thread-safe inside a running web worker (it manages its own
    # multiprocessing pool and signal handlers).
    cmd = [
        sys.executable,
        "-m",
        "ocrmypdf",
        "-l",
        language,
        "--skip-text",
        "--output-type",
        "pdf",
        str(file_path),
        str(tmp_out),
    ]
    try:
        result = subprocess.run(  # noqa: S603
            cmd,
            capture_output=True,
            text=True,
            timeout=OCR_TIMEOUT_SECONDS,
            check=False,
        )
        if result.returncode != 0:
            logger.error(
                "ocrmypdf failed (rc=%d): %s", result.returncode, result.stderr[-500:]
            )
            raise OCRError("OCR-Verarbeitung fehlgeschlagen")

        tmp_out.replace(file_path)
        logger.info("OCR completed for %s", file_path.name)
    except subprocess.TimeoutExpired as e:
        logger.error("ocrmypdf timed out after %ds", OCR_TIMEOUT_SECONDS)
        raise OCRError("OCR-Verarbeitung hat zu lange gedauert") from e
    finally:
        if tmp_out.exists():
            tmp_out.unlink()
