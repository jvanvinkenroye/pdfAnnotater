#!/bin/bash
# PDF Annotator Installation Script
#
# Usage: ./install.sh
#
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

# Install using available tool (prefer uv > pipx > pip)
if command -v uv &> /dev/null; then
    echo "Using uv tool for installation..."
    uv tool install "$REPO_DIR"
elif command -v pipx &> /dev/null; then
    echo "Using pipx for installation..."
    pipx install "$REPO_DIR"
else
    echo "Using pip for installation..."
    pip3 install --user "$REPO_DIR"
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
    echo ""
    echo "Uninstall:"
    if command -v uv &> /dev/null; then
        echo "  uv tool uninstall pdf-annotator"
    elif command -v pipx &> /dev/null; then
        echo "  pipx uninstall pdf-annotator"
    else
        echo "  pip3 uninstall pdf-annotator"
    fi
else
    echo ""
    echo "Installation complete, but 'pdf-annotator' not found in PATH."
    echo ""
    echo "Add to PATH:"
    if command -v uv &> /dev/null; then
        echo "  source \$(uv tool dir)/bin/activate"
    else
        echo "  export PATH=\"\$HOME/.local/bin:\$PATH\""
    fi
fi
