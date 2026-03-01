# Architektur

## Projektstruktur

```
pdfAnnotater/
├── src/pdf_annotator/          # Hauptpaket
│   ├── app.py                  # Flask App Factory (create_app)
│   ├── config.py               # Konfigurationsklassen
│   ├── models/
│   │   ├── database.py         # DatabaseManager (Singleton)
│   │   └── user.py             # User-Modell (Flask-Login)
│   ├── services/
│   │   ├── pdf_processor.py    # PDF → PNG Rendering (LRU-Cache)
│   │   ├── pdf_generator.py    # Annotiertes PDF erstellen
│   │   ├── data_manager.py     # Import/Export ZIP
│   │   └── markdown_exporter.py
│   ├── routes/
│   │   ├── auth.py             # Login, Logout, Registrierung, Theme-API
│   │   ├── admin.py            # Admin Panel
│   │   ├── upload.py           # Upload, Delete, Backup
│   │   ├── viewer.py           # Viewer & Annotations-API
│   │   └── export.py           # Export-Endpunkte
│   ├── utils/
│   │   ├── validators.py       # Input-Validierung
│   │   └── logger.py           # Logging-Setup
│   ├── templates/              # Jinja2-Templates
│   └── static/                 # CSS & JavaScript
├── tests/                      # Pytest-Testsuite
├── Dockerfile                  # Multi-Stage Build
├── docker-compose.yml
├── pyproject.toml
└── wsgi.py                     # Gunicorn-Einstiegspunkt
```

## Schichten

```
HTTP Request
     ↓
routes/        (Flask Blueprints — Request-Handling, Validierung)
     ↓
services/      (Business-Logik — PDF-Verarbeitung, Export, Import)
     ↓
models/        (Datenzugriff — DatabaseManager, User)
     ↓
SQLite DB / Dateisystem
```

## App Factory

Die Flask-App wird über `create_app(config_name)` erstellt:

```python
from pdf_annotator.app import create_app

app = create_app('production')   # oder 'development', 'testing'
```

Blueprints registriert in `app.py`:

| Blueprint | URL-Prefix | Datei |
|---|---|---|
| `auth_bp` | `/auth` | `routes/auth.py` |
| `upload_bp` | `/` | `routes/upload.py` |
| `viewer_bp` | `/viewer` | `routes/viewer.py` |
| `export_bp` | `/export` | `routes/export.py` |
| `admin_bp` | `/admin` | `routes/admin.py` |

## DatabaseManager

Singleton-Klasse mit allen Datenbankoperationen:

```python
db = DatabaseManager()          # Gibt immer dieselbe Instanz zurück
doc = db.get_document(doc_id)   # Gibt dict oder None zurück
db.upsert_annotation(doc_id, page, text)  # Atomar (INSERT OR UPDATE)
```

Wichtige Methoden:

| Methode | Beschreibung |
|---|---|
| `create_document()` | Neues Dokument anlegen |
| `get_document(doc_id)` | Dokument nach ID |
| `upsert_annotation()` | Notiz einfügen oder aktualisieren (atomar) |
| `get_all_annotations(doc_id)` | Alle Notizen eines Dokuments |
| `renumber_annotations_after_delete()` | Seiten-Renummerierung |
| `create_user()` | Benutzer anlegen |
| `count_admins()` | Anzahl aktiver Admins |

## viewer.py Pattern

Alle API-Endpunkte in `viewer.py` nutzen den Helper `_get_doc_or_error(doc_id)`:

```python
def _get_doc_or_error(doc_id):
    """Gibt (doc_info, None) oder (None, error_response) zurück."""
    ...

@viewer_bp.route("/api/annotation/<doc_id>/<int:page_number>", methods=["POST"])
@login_required
def save_annotation(doc_id, page_number):
    doc_info, err = _get_doc_or_error(doc_id)
    if err is not None:
        return err
    # Weiterverarbeitung mit doc_info
```

Dies eliminiert duplizierten Auth/Ownership-Check-Code in jedem Endpunkt.

## PDF-Rendering Cache

PDF-Seiten werden beim Rendern gecacht (LRU-Cache):

```python
# Interner cached Render (wirft Exception bei Fehler, damit None nicht gecacht wird)
@lru_cache(maxsize=50)
def _render_page_cached(file_path, page_number, dpi):
    ...

# Öffentliche Funktion — fängt Exceptions ab
def render_page_to_image(file_path, page_number, dpi):
    try:
        return _render_page_cached(file_path, page_number, dpi)
    except Exception:
        return None
```

Bei Änderungen am PDF (Seite löschen, ersetzen, anhängen) wird der Cache explizit geleert:

```python
clear_render_cache()
```

## Konfiguration

| Klasse | Verwendung |
|---|---|
| `DevelopmentConfig` | Standard, `FLASK_ENV` nicht gesetzt |
| `ProductionConfig` | `APP_ENV=production` — nutzt plattformspezifische Datenpfade |
| `TestingConfig` | In-Memory-DB, CSRF deaktiviert |

`ProductionConfig` ermittelt den Datenpfad über `get_data_dir()`:

- macOS: `~/Library/Application Support/PDF-Annotator/`
- Linux: `~/.local/share/PDF-Annotator/` (respektiert `XDG_DATA_HOME`)
- Docker: `/data/PDF-Annotator/` (via `XDG_DATA_HOME=/data`)

## Datenbank-Schema

```sql
CREATE TABLE users (
    id TEXT PRIMARY KEY,
    username TEXT UNIQUE NOT NULL,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_active INTEGER DEFAULT 1,
    is_admin INTEGER DEFAULT 0,
    theme TEXT DEFAULT NULL
);

CREATE TABLE documents (
    id TEXT PRIMARY KEY,
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
