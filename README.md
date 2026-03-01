# PDF Side-by-Side Annotator

Eine Flask-basierte Web-Applikation zum Annotieren von PDF-Dokumenten mit Side-by-Side-View. Zeigt PDFs seitenweise an und ermöglicht es, pro Seite Notizen zu erfassen, die dann mit Zeitstempeln in grüner Courier-Schrift in das PDF integriert werden.

## Features

- **Split-Screen View:** PDF-Anzeige links, Notizen-Editor rechts
- **Seitenweise Navigation:** Vor/Zurueck-Buttons, Seiteneingabe und Tastatur-Shortcuts
- **Auto-Save:** Notizen werden automatisch gespeichert (debounced, 500ms)
- **Seite loeschen:** Einzelne Seiten aus dem PDF entfernen
- **PDF ersetzen:** PDF-Datei austauschen, alle Notizen bleiben erhalten
- **Metadaten:** Vorname, Nachname, Titel, Jahr, Thema pro Dokument
- **Export-Funktionen:**
  - **Annotiertes PDF:** Original-PDF mit Notizen in gruener Courier-Schrift + Zeitstempel
  - **Markdown-Export:** Alle Notizen als strukturiertes Markdown-Dokument
- **Zoom:** Stufenweises Zoomen (50%-200%) und Breitenanpassung
- **Themes:** Light, Dark und Brutalist — Einstellung wird pro Account serverseitig gespeichert
- **Multi-User:** Registrierung und Login mit eigenem Dokumenten-Bereich
- **Admin Panel:** Benutzerverwaltung (Aktivieren/Deaktivieren, Admin-Rechte, Loeschen)
- **Persistente Speicherung:** Dokumente bleiben bis zur manuellen Loeschung erhalten
- **Max. 50 MB:** Upload-Limit fuer PDF-Dateien

## Deployment als Web-Dienst (Docker)

Die empfohlene Methode fuer den produktiven Betrieb auf einem Server.

### Voraussetzungen

- Docker 24+ und Docker Compose v2+

### Schnellstart

```bash
# Repository klonen
git clone https://github.com/jvanvinkenroye/pdfAnnotater.git
cd pdfAnnotater

# Secret Key generieren
export SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))")

# Container starten
docker compose up -d
```

Die App ist unter `http://localhost:8000` erreichbar.

### Persistenz

Alle Daten (Datenbank, hochgeladene PDFs, Exporte) werden in einem Docker-Volume gespeichert und ueberleben Container-Neustarts:

```
pdf_annotator_data:/data
```

### Konfiguration

Umgebungsvariablen in einer `.env`-Datei oder direkt in der Shell:

| Variable | Pflicht | Standard | Beschreibung |
|---|---|---|---|
| `SECRET_KEY` | **Ja** | — | Flask Session-Key (min. 32 zufaellige Bytes) |
| `GUNICORN_WORKERS` | Nein | `2` | Anzahl Gunicorn Worker-Prozesse |

Empfohlene Worker-Anzahl: `2 * CPU-Kerne + 1`.

### Mit .env-Datei

```bash
# .env anlegen (nicht committen!)
cat > .env <<EOF
SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))")
GUNICORN_WORKERS=4
EOF

docker compose up -d
```

### Reverse Proxy (nginx)

Fuer HTTPS-Betrieb hinter nginx:

```nginx
server {
    listen 443 ssl;
    server_name annotations.example.com;

    location / {
        proxy_pass         http://localhost:8000;
        proxy_set_header   Host $host;
        proxy_set_header   X-Real-IP $remote_addr;
        proxy_set_header   X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header   X-Forwarded-Proto $scheme;
        client_max_body_size 50M;
    }
}
```

### Nuetzliche Docker-Befehle

```bash
# Status pruefen
docker compose ps

# Logs ansehen
docker compose logs -f

# Container neu starten
docker compose restart

# Stoppen
docker compose down

# Daten-Volume auflisten
docker volume ls | grep pdf_annotator
```

### Image selbst bauen

```bash
docker build -t pdf-annotator:latest .
```

---

## Lokale Installation (Entwickler / Desktop)

### Voraussetzungen

- Python 3.10 oder hoeher
- macOS oder Linux

### Homebrew (macOS)

```bash
brew tap jvanvinkenroye/pdf-annotator
brew install pdf-annotator
pdf-annotator
```

### uv tool (plattformuebergreifend)

```bash
uv tool install git+https://github.com/jvanvinkenroye/pdfAnnotater.git
pdf-annotator
```

### Aus Source (Entwicklung)

```bash
git clone https://github.com/jvanvinkenroye/pdfAnnotater.git
cd pdfAnnotater
uv sync
```

**Als Web-Server starten (Entwicklungsmodus):**

```bash
uv run flask --app src/pdf_annotator/app:create_app run --port 8000
```

**Als Desktop-App starten** (eigenes Fenster via flaskwebgui):

```bash
uv run pdf-annotator
```

**Als Produktions-Server starten** (Gunicorn, ohne Docker):

```bash
SECRET_KEY=<dein-key> uv run pdf-annotator-server
```

### Datenspeicherung (lokal)

| Plattform | Speicherort |
|-----------|-------------|
| **macOS** | `~/Library/Application Support/PDF-Annotator/` |
| **Linux** | `~/.local/share/PDF-Annotator/` |
| **Docker** | `/data/PDF-Annotator/` (Volume `pdf_annotator_data`) |

---

## Workflow

1. **Registrieren / Einloggen:** Ersten Account anlegen (wird automatisch Admin)
2. **PDF hochladen:** Drag & Drop oder Datei-Auswahl (max. 50 MB)
3. **Notizen hinzufuegen:** Durch Seiten navigieren, Notizen im rechten Editor erfassen
4. **Auto-Save:** Speichert automatisch beim Tippen (500 ms Debounce)
5. **Exportieren:**
   - **PDF generieren:** Annotiertes PDF mit Notizen in gruener Courier-Schrift + Zeitstempel
   - **Markdown exportieren:** Alle Notizen als Markdown-Datei (mit Seitenzahlen)

## Tastatur-Shortcuts

| Shortcut | Funktion |
|---|---|
| Ctrl/Cmd + Links/Hoch | Vorherige Seite |
| Ctrl/Cmd + Rechts/Runter | Naechste Seite |
| Ctrl/Cmd + Home | Erste Seite |
| Ctrl/Cmd + End | Letzte Seite |
| Ctrl/Cmd + G | Zu Seite springen |
| Ctrl/Cmd + Delete/Backspace | Seite loeschen |

---

## Projektstruktur

```
pdfAnnotater/
├── Dockerfile
├── docker-compose.yml
├── wsgi.py                     # Gunicorn Entry Point
├── src/pdf_annotator/
│   ├── app.py                  # Flask App Factory
│   ├── config.py               # Konfiguration (Dev/Prod/Test)
│   │
│   ├── models/
│   │   ├── database.py         # SQLite Schema & CRUD
│   │   └── user.py             # User-Modell (Flask-Login)
│   │
│   ├── services/
│   │   ├── pdf_processor.py    # PDF → PNG Rendering
│   │   ├── pdf_generator.py    # Annotiertes PDF erstellen
│   │   ├── data_manager.py     # Import/Export ZIP
│   │   └── markdown_exporter.py
│   │
│   ├── routes/
│   │   ├── auth.py             # Login, Logout, Registrierung, Theme-API
│   │   ├── admin.py            # Admin Panel (Benutzerverwaltung)
│   │   ├── upload.py           # PDF-Upload, Delete, Export, Import
│   │   └── viewer.py           # Viewer & Annotations-API
│   │
│   ├── utils/
│   │   ├── validators.py       # Input-Validierung
│   │   └── logger.py           # Logging-Setup
│   │
│   ├── static/
│   │   ├── css/styles.css
│   │   └── js/{upload,viewer,documents,theme,modal}.js
│   │
│   └── templates/
│       ├── base.html
│       ├── documents.html
│       ├── viewer.html
│       ├── auth/{login,register}.html
│       ├── admin/
│       └── icons.html          # Lucide SVG Icon-Library
│
├── tests/                      # Pytest Tests (114 Tests)
├── pyproject.toml
└── ruff.toml
```

---

## Datenbank-Schema

```sql
CREATE TABLE users (
    id TEXT PRIMARY KEY,            -- UUID4
    username TEXT UNIQUE NOT NULL,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_active INTEGER DEFAULT 1,
    is_admin INTEGER DEFAULT 0,
    theme TEXT DEFAULT NULL         -- 'light' | 'dark' | 'brutalist' | NULL
);

CREATE TABLE documents (
    id TEXT PRIMARY KEY,            -- UUID4
    user_id TEXT NOT NULL,
    original_filename TEXT NOT NULL,
    file_path TEXT NOT NULL,
    page_count INTEGER NOT NULL,
    first_name TEXT DEFAULT '',
    last_name TEXT DEFAULT '',
    title TEXT DEFAULT '',
    year TEXT DEFAULT '',
    subject TEXT DEFAULT '',
    upload_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE annotations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    doc_id TEXT NOT NULL,
    page_number INTEGER NOT NULL,
    note_text TEXT DEFAULT '',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (doc_id) REFERENCES documents(id) ON DELETE CASCADE,
    UNIQUE(doc_id, page_number)
);
```

---

## API-Endpunkte

### Auth
- `GET/POST /auth/login` - Login
- `GET/POST /auth/register` - Registrierung
- `GET /auth/logout` - Logout
- `POST /auth/theme` - Theme serverseitig speichern (Login erforderlich)

### Dokumente
- `GET /documents` - Dokumentenliste
- `POST /upload` - PDF hochladen
- `DELETE /delete/<doc_id>` - Dokument loeschen
- `GET /export/backup` - Backup ZIP herunterladen
- `POST /import` - Backup importieren

### Viewer
- `GET /viewer/<doc_id>` - Viewer-Seite
- `GET /viewer/api/page/<doc_id>/<page>` - Seite als PNG
- `DELETE /viewer/api/page/<doc_id>/<page>` - Seite loeschen
- `GET /viewer/api/annotation/<doc_id>/<page>` - Notiz laden
- `POST /viewer/api/annotation/<doc_id>/<page>` - Notiz speichern
- `POST /viewer/api/metadata/<doc_id>` - Metadaten aktualisieren
- `POST /viewer/api/replace/<doc_id>` - PDF ersetzen

### Export
- `POST /export/pdf/<doc_id>` - Annotiertes PDF
- `POST /export/markdown/<doc_id>` - Markdown-Datei
- `GET /export/original/<doc_id>` - Original-PDF

### Admin
- `GET /admin/` - Benutzeruebersicht (nur Admins)
- `POST /admin/user/<id>/toggle-active` - Benutzer aktivieren/deaktivieren
- `POST /admin/user/<id>/toggle-admin` - Admin-Rechte vergeben/entziehen
- `DELETE /admin/user/<id>` - Benutzer loeschen

---

## Entwicklung

### Tests

```bash
uv run pytest tests/ -v
```

### Code-Qualitaet

```bash
uv run ruff check src/ tests/
uv run ruff format src/ tests/
```

---

## Technologie-Stack

- **Backend:** Python 3.10+ mit Flask 3.0+, Flask-Login, Flask-WTF
- **WSGI:** Gunicorn (Produktion)
- **PDF-Handling:** PyMuPDF (fitz) fuer Rendering und Text-Injektion
- **Frontend:** HTML5, CSS3 (Flexbox), Vanilla JavaScript (Fetch API)
- **Icons:** Lucide (inline SVG)
- **Datenbank:** SQLite
- **Containerisierung:** Docker (Multi-Stage Build), Docker Compose
- **Code Quality:** Ruff (Linting & Formatting)

## Lizenz

Dieses Projekt wurde als Lernprojekt erstellt.

## Troubleshooting

### Fehler beim PDF-Upload

- Prüfe, dass die Datei ein gueltiges PDF ist (nicht beschaedigt)
- Prüfe die Dateigroesse (max. 50 MB)
- Docker: `docker compose logs -f` fuer Fehlermeldungen

### Container startet nicht

- `SECRET_KEY` nicht gesetzt → `docker compose up` bricht mit Fehlermeldung ab
- Port 8000 belegt → `ports` in `docker-compose.yml` anpassen (z.B. `"8080:8000"`)

### Daten zuruecksetzen (Docker)

```bash
docker compose down
docker volume rm pdfannotater_pdf_annotator_data
docker compose up -d
```
