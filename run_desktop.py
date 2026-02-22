#!/usr/bin/env python3
"""
Desktop launcher for PDF Annotator.

Usage:
    python run_desktop.py

Or make executable:
    chmod +x run_desktop.py
    ./run_desktop.py
"""

try:
    from pdf_annotator.desktop import main
except ImportError:
    # Fallback for running without package installation (development)
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).parent / "src"))
    from pdf_annotator.desktop import main

if __name__ == "__main__":
    main()
