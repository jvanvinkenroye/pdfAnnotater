#!/usr/bin/env bash
set -euo pipefail

# Dienst stoppen und deaktivieren (nur wenn systemd läuft)
if [ -d /run/systemd/system ]; then
    if systemctl is-active --quiet pdf-annotator 2>/dev/null; then
        systemctl stop pdf-annotator || true
    fi
    if systemctl is-enabled --quiet pdf-annotator 2>/dev/null; then
        systemctl disable pdf-annotator || true
    fi
fi
