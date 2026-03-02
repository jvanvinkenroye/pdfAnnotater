#!/usr/bin/env bash
set -euo pipefail

# Systembenutzer anlegen (falls nicht vorhanden)
if ! id -u pdf-annotator >/dev/null 2>&1; then
    adduser \
        --system \
        --group \
        --no-create-home \
        --home /var/lib/pdf-annotator \
        --shell /usr/sbin/nologin \
        pdf-annotator
fi

# Datenverzeichnis anlegen und Berechtigungen setzen
mkdir -p /var/lib/pdf-annotator
chown -R pdf-annotator:pdf-annotator /var/lib/pdf-annotator
chmod 750 /var/lib/pdf-annotator

# /opt-Verzeichnis gehört root
chown -R root:root /opt/pdf-annotator
chmod -R a+rX /opt/pdf-annotator
# Binaries im venv ausführbar halten
find /opt/pdf-annotator/.venv/bin -type f -exec chmod 755 {} +

# Konfigurationsverzeichnis anlegen (falls noch nicht vorhanden)
mkdir -p /etc/pdf-annotator
if [ ! -f /etc/pdf-annotator/env ]; then
    cp /etc/pdf-annotator/env.example /etc/pdf-annotator/env 2>/dev/null || true
    chmod 640 /etc/pdf-annotator/env
    chown root:pdf-annotator /etc/pdf-annotator/env 2>/dev/null || true
fi

# systemd neu laden (nur wenn systemd läuft)
if [ -d /run/systemd/system ]; then
    systemctl daemon-reload || true
fi
