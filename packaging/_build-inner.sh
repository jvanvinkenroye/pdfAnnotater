#!/usr/bin/env bash
# Läuft INNERHALB des Docker-Containers (debian:bookworm-slim, --platform linux/amd64).
# Wird von packaging/build-deb.sh aufgerufen – nicht direkt ausführen.
set -euo pipefail

cd /workspace

# --- System-Abhängigkeiten ---
apt-get update -qq
apt-get install -y -qq --no-install-recommends \
    curl ca-certificates python3 python3-venv fakeroot dpkg-dev

# --- uv installieren ---
curl -LsSf https://astral.sh/uv/install.sh | INSTALLER_NO_MODIFY_PATH=1 sh
export PATH="/root/.local/bin:${PATH}"

# --- Venv am Ziel-Installationspfad aufbauen ---
# Shebangs in .venv/bin/* zeigen dann auf /opt/pdf-annotator/.venv/bin/python3
mkdir -p /opt/pdf-annotator
uv venv /opt/pdf-annotator/.venv

# Produktions-Abhängigkeiten aus Lockfile exportieren und installieren
uv export --frozen --no-dev --no-hashes --format requirements-txt \
    > /tmp/requirements.txt
/opt/pdf-annotator/.venv/bin/pip install --quiet -r /tmp/requirements.txt

# Projekt selbst als Wheel bauen und installieren (nicht-editable)
uv build --wheel --out-dir /tmp/pdf-wheel/
/opt/pdf-annotator/.venv/bin/pip install --quiet --no-deps /tmp/pdf-wheel/*.whl

echo "Shebang check: $(head -1 /opt/pdf-annotator/.venv/bin/pdf-annotator)"

# --- Staging-Verzeichnis aufbauen ---
rm -rf /workspace/dist/staging
mkdir -p /workspace/dist/staging/opt/pdf-annotator
mkdir -p /workspace/dist/staging/usr/bin

cp -a /opt/pdf-annotator/.venv /workspace/dist/staging/opt/pdf-annotator/.venv
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

# --- DEBIAN-Paketstruktur ---
rm -rf /workspace/dist/deb
mkdir -p /workspace/dist/deb/DEBIAN
mkdir -p /workspace/dist/deb/usr/bin
mkdir -p /workspace/dist/deb/lib/systemd/system
mkdir -p /workspace/dist/deb/etc/pdf-annotator

cp -a /workspace/dist/staging/opt /workspace/dist/deb/
cp /workspace/dist/staging/usr/bin/pdf-annotator       /workspace/dist/deb/usr/bin/
cp /workspace/dist/staging/usr/bin/pdf-annotator-server /workspace/dist/deb/usr/bin/
cp /workspace/packaging/pdf-annotator.service /workspace/dist/deb/lib/systemd/system/
cp /workspace/packaging/env.example           /workspace/dist/deb/etc/pdf-annotator/

# DEBIAN/control (keine führenden Leerzeichen erlaubt!)
echo "Package: pdf-annotator"                                        > /workspace/dist/deb/DEBIAN/control
echo "Version: ${VERSION}"                                           >> /workspace/dist/deb/DEBIAN/control
echo "Architecture: amd64"                                           >> /workspace/dist/deb/DEBIAN/control
echo "Maintainer: jvanvinkenroye <java@local.dev>"                   >> /workspace/dist/deb/DEBIAN/control
echo "Depends: python3 (>= 3.10)"                                   >> /workspace/dist/deb/DEBIAN/control
echo "Homepage: https://github.com/jvanvinkenroye/pdfAnnotater"      >> /workspace/dist/deb/DEBIAN/control
echo "Description: PDF annotation tool with side-by-side view"       >> /workspace/dist/deb/DEBIAN/control
echo " PDF annotator with green Courier timestamps and Gunicorn."    >> /workspace/dist/deb/DEBIAN/control

cp /workspace/packaging/postinstall.sh /workspace/dist/deb/DEBIAN/postinst
cp /workspace/packaging/preremove.sh   /workspace/dist/deb/DEBIAN/prerm
chmod 755 /workspace/dist/deb/DEBIAN/postinst /workspace/dist/deb/DEBIAN/prerm

# --- .deb bauen ---
mkdir -p /workspace/dist
fakeroot dpkg-deb --build /workspace/dist/deb \
    "/workspace/dist/pdf-annotator_${VERSION}_amd64.deb"

echo "Fertig: /workspace/dist/pdf-annotator_${VERSION}_amd64.deb"
dpkg-deb --info "/workspace/dist/pdf-annotator_${VERSION}_amd64.deb"
