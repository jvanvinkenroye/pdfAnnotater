# Installation

## Docker (empfohlen)

Die einfachste und empfohlene Methode für den Betrieb auf einem Server oder lokal.

**Voraussetzungen:** Docker 24+ und Docker Compose v2+

```bash
# Repository klonen
git clone https://github.com/jvanvinkenroye/pdfAnnotater.git
cd pdfAnnotater

# Secret Key generieren und .env-Datei anlegen
python3 -c "import secrets; print('SECRET_KEY=' + secrets.token_hex(32))" > .env

# Container starten
docker compose up -d
```

Die App ist unter **http://localhost:8000** erreichbar.

!!! warning "SECRET_KEY ist Pflicht"
    Ohne gesetzten `SECRET_KEY` startet `docker compose up` nicht. Der Key muss mindestens 32 zufällige Bytes enthalten.

---

## uv tool (plattformübergreifend)

Für macOS und Linux ohne Docker. Installiert die App als CLI-Tool.

**Voraussetzung:** [uv](https://docs.astral.sh/uv/) installiert

```bash
uv tool install git+https://github.com/jvanvinkenroye/pdfAnnotater.git
pdf-annotator        # Desktop-App (eigenes Fenster)
pdf-annotator-server # Web-Server-Modus auf Port 8000
```

---

## Homebrew (macOS)

```bash
brew tap jvanvinkenroye/pdf-annotator
brew install pdf-annotator
pdf-annotator
```

!!! note "Nur macOS arm64"
    Die Homebrew-Formel enthält vorkompilierte Wheels für Apple Silicon (arm64). Intel-Macs werden nicht unterstützt.

---

## Aus Source (Entwicklung)

**Voraussetzungen:** Python 3.10+, [uv](https://docs.astral.sh/uv/)

```bash
git clone https://github.com/jvanvinkenroye/pdfAnnotater.git
cd pdfAnnotater
uv sync
```

### Starten

=== "Web-Server (Entwicklung)"

    ```bash
    uv run flask --app src/pdf_annotator/app:create_app run --port 8000
    ```

=== "Desktop-App"

    ```bash
    uv run pdf-annotator
    ```

=== "Produktions-Server (Gunicorn)"

    ```bash
    SECRET_KEY=<dein-key> uv run pdf-annotator-server
    ```

---

## Datenspeicherung

| Plattform | Speicherort |
|---|---|
| **macOS** | `~/Library/Application Support/PDF-Annotator/` |
| **Linux** | `~/.local/share/PDF-Annotator/` |
| **Docker** | `/data/PDF-Annotator/` (Volume `pdf_annotator_data`) |

Gespeichert werden: SQLite-Datenbank, hochgeladene PDFs, generierte Exporte und Logs.

---

## Erster Start

Beim ersten Aufruf der App ist noch kein Benutzer vorhanden.

1. **Registrieren:** `/auth/register` aufrufen und Account anlegen
2. **Admin-Rechte:** Der erste registrierte Benutzer wird automatisch Admin
3. **Einloggen:** Mit den erstellten Zugangsdaten anmelden

!!! tip "Erster Benutzer = Admin"
    Der erste registrierte Benutzer erhält automatisch Admin-Rechte und kann weitere Benutzer verwalten.
