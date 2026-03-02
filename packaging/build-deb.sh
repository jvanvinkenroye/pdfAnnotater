#!/usr/bin/env bash
# Baut ein .deb-Paket lokal via Docker (funktioniert auch auf macOS).
# Voraussetzung: Docker läuft und hat Zugriff auf das Internet.
#
# Verwendung:
#   ./packaging/build-deb.sh [VERSION]
#
# Beispiel:
#   ./packaging/build-deb.sh 0.8.0
#   # → dist/pdf-annotator_0.8.0_amd64.deb
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly PROJECT_DIR="$(dirname "${SCRIPT_DIR}")"

cd "${PROJECT_DIR}"

# Version bestimmen: Argument > pyproject.toml
if [[ ${1:-} ]]; then
    readonly VERSION="${1}"
else
    readonly VERSION=$(python3 -c "
import tomllib
with open('pyproject.toml', 'rb') as f:
    print(tomllib.load(f)['project']['version'])
")
fi

echo "Baue pdf-annotator ${VERSION} .deb-Paket (via Docker, linux/amd64)..."

mkdir -p "${PROJECT_DIR}/dist"

docker run --rm \
    --platform linux/amd64 \
    -v "${PROJECT_DIR}:/workspace" \
    -e "VERSION=${VERSION}" \
    debian:bookworm-slim \
    bash /workspace/packaging/_build-inner.sh

echo ""
echo "Ergebnis: ${PROJECT_DIR}/dist/pdf-annotator_${VERSION}_amd64.deb"
echo ""
echo "Installation auf Ziel-System:"
echo "  sudo dpkg -i dist/pdf-annotator_${VERSION}_amd64.deb"
echo "  echo \"SECRET_KEY=\$(python3 -c 'import secrets; print(secrets.token_hex(32))')\" \\"
echo "    | sudo tee /etc/pdf-annotator/env"
echo "  sudo systemctl enable --now pdf-annotator"
