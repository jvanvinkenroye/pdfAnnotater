#!/usr/bin/env python3
"""
Desktop launcher for PDF Annotator.

Usage:
    python run_desktop.py

Or make executable:
    chmod +x run_desktop.py
    ./run_desktop.py
"""

import sys
from pathlib import Path

# Add src to path if running directly
src_path = Path(__file__).parent / "src"
if src_path.exists():
    sys.path.insert(0, str(src_path))

from pdf_annotator.desktop import main  # noqa: E402

if __name__ == "__main__":
    main()
