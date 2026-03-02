#!/usr/bin/env bash
# Läuft INNERHALB des Docker-Containers (debian:bookworm-slim, --platform linux/amd64).
# Wird von packaging/build-deb.sh aufgerufen – nicht direkt ausführen.
set -euo pipefail

cd /workspace

# --- System-Abhängigkeiten ---
apt-get update -qq
apt-get install -y -qq --no-install-recommends \
    curl ca-certificates python3 python3-venv

# --- uv installieren ---
curl -LsSf https://astral.sh/uv/install.sh | INSTALLER_NO_MODIFY_PATH=1 sh
export PATH="/root/.local/bin:${PATH}"

# --- Venv am Ziel-Installationspfad aufbauen ---
# Shebangs in .venv/bin/* zeigen dann auf /opt/pdf-annotator/.venv/bin/python3
mkdir -p /opt/pdf-annotator

UV_PROJECT_ENVIRONMENT=/opt/pdf-annotator/.venv \
    uv sync --frozen --no-dev --no-editable

# --- Staging-Verzeichnis aufbauen ---
rm -rf /workspace/dist/staging
mkdir -p /workspace/dist/staging/opt/pdf-annotator
mkdir -p /workspace/dist/staging/usr/bin

# Venv in Staging kopieren
cp -a /opt/pdf-annotator/.venv /workspace/dist/staging/opt/pdf-annotator/.venv

# wsgi.py für Gunicorn
cp /workspace/wsgi.py /workspace/dist/staging/opt/pdf-annotator/wsgi.py

# --- Wrapper-Script: Desktop-Launcher (flaskwebgui) ---
cat > /workspace/dist/staging/usr/bin/pdf-annotator << 'EOF'
#!/usr/bin/env bash
exec /opt/pdf-annotator/.venv/bin/pdf-annotator "$@"
EOF
chmod 755 /workspace/dist/staging/usr/bin/pdf-annotator

# --- Wrapper-Script: Production-Server (Gunicorn) ---
cat > /workspace/dist/staging/usr/bin/pdf-annotator-server << 'EOF'
#!/usr/bin/env bash
exec /opt/pdf-annotator/.venv/bin/gunicorn \
    --workers "${WORKERS:-4}" \
    --bind "${BIND:-0.0.0.0:8000}" \
    --chdir /opt/pdf-annotator \
    wsgi:app
EOF
chmod 755 /workspace/dist/staging/usr/bin/pdf-annotator-server

# --- nfpm installieren (via goreleaser apt-Repository) ---
echo 'deb [trusted=yes] https://repo.goreleaser.com/apt/ /' \
    > /etc/apt/sources.list.d/goreleaser.list
apt-get update -qq
apt-get install -y -qq nfpm

# --- .deb bauen ---
mkdir -p /workspace/dist
VERSION="${VERSION}" nfpm package \
    -f /workspace/packaging/nfpm.yml \
    -p deb \
    -t /workspace/dist/

echo "Fertig: /workspace/dist/pdf-annotator_${VERSION}_amd64.deb"
