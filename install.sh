#!/bin/bash
# PDF Annotator Installation Script
# Usage: ./install.sh
#
# This script installs PDF Annotator as a command-line tool.
# After installation, run: pdf-annotator

set -euo pipefail

APP_NAME="PDF-Annotator"
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "Installing $APP_NAME..."

# Check for Python 3.10+
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 is required but not found."
    echo "Install via: brew install python@3.12"
    exit 1
fi

PYTHON_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
PYTHON_MAJOR=$(echo "$PYTHON_VERSION" | cut -d. -f1)
PYTHON_MINOR=$(echo "$PYTHON_VERSION" | cut -d. -f2)

if [ "$PYTHON_MAJOR" -lt 3 ] || ([ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -lt 10 ]); then
    echo "Error: Python 3.10+ required, found $PYTHON_VERSION"
    exit 1
fi

echo "Found Python $PYTHON_VERSION"

# Check for uv or pip
if command -v uv &> /dev/null; then
    echo "Using uv for installation..."
    cd "$REPO_DIR"
    uv pip install --system -e .
elif command -v pipx &> /dev/null; then
    echo "Using pipx for installation..."
    pipx install "$REPO_DIR"
else
    echo "Using pip for installation..."
    pip3 install --user -e "$REPO_DIR"
fi

# Verify installation
if command -v pdf-annotator &> /dev/null; then
    echo ""
    echo "Installation successful!"
    echo ""
    echo "Usage:"
    echo "  pdf-annotator    - Start the desktop application"
    echo ""
    echo "Data will be stored in:"
    if [ "$(uname)" = "Darwin" ]; then
        echo "  ~/Library/Application Support/$APP_NAME/"
    else
        echo "  ~/.local/share/pdf-annotator/"
    fi
else
    echo ""
    echo "Installation complete, but 'pdf-annotator' not found in PATH."
    echo "You may need to add ~/.local/bin to your PATH:"
    echo "  export PATH=\"\$HOME/.local/bin:\$PATH\""
    echo ""
    echo "Or run directly:"
    echo "  python3 -m pdf_annotator.desktop"
fi
