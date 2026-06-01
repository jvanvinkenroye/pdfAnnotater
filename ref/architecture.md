# Architecture

## Overview

Flask-based web application for uploading PDFs, annotating them page-by-page, and exporting annotated PDFs or Markdown notes. Supports multi-user authentication, SQLite persistence, and runs as both a desktop app (flaskwebgui) and a production server (Gunicorn).

## Entry Points

| Command | Module | Description |
|---|---|---|
| `pdf-annotator` | `pdf_annotator.desktop:main` | Desktop app via flaskwebgui (Chrome window) |
| `pdf-annotator-server` | `pdf_annotator.app:run_server` | Gunicorn production server |
| `uv run flask run` | `pdf_annotator.app:create_app` | Dev server |

## Application Factory

`src/pdf_annotator/app.py` — `create_app(config_name)`:
1. Loads config from `config.py` (development / production / testing)
2. Sets up Flask-Login, CSRF protection (Flask-WTF), rate limiter (Flask-Limiter)
3. Initializes DatabaseManager singleton + `init_db()`
4. Registers all blueprints
5. Adds `/health` endpoint (no auth, rate-limit exempt)
6. Attaches security headers via `@after_request`

## Blueprint Layout

| Blueprint | Prefix | File |
|---|---|---|
| `auth_bp` | `/auth` | `routes/auth.py` |
| `upload_bp` | `/` | `routes/upload.py` |
| `viewer_bp` | `/viewer` | `routes/viewer.py` |
| `export_bp` | `/export` | `routes/export.py` |
| `admin_bp` | `/admin` | `routes/admin.py` |

## Layer Diagram

```
Browser / CLI
    │
Flask Routes (routes/)
    ├── auth.py        login, register, logout, theme
    ├── upload.py      upload, delete, export-zip, import-zip
    ├── viewer.py      view, page-image, annotation CRUD, replace, append, delete-page
    ├── export.py      download original PDF, export annotated PDF, export MD
    └── admin.py       user management (admin-only)
    │
Services (services/)
    ├── pdf_processor.py    PyMuPDF rendering, page count, LRU cache
    ├── pdf_generator.py    annotated PDF creation (green Courier footer)
    ├── markdown_exporter.py Markdown note export
    └── data_manager.py     ZIP export/import of all user data
    │
Models (models/)
    ├── database.py    SQLite DatabaseManager singleton
    └── user.py        Flask-Login User model
    │
Utils (utils/)
    ├── validators.py  input validation (doc_id, filename, note, page number, file size)
    └── logger.py      setup_logger / get_logger
```

## Configuration

`src/pdf_annotator/config.py` — three configs inherit from `Config`:

| Name | Used when | DB path | Data dir |
|---|---|---|---|
| `DevelopmentConfig` | `APP_ENV=development` (default) | `./data/annotations.db` | `./data/` |
| `ProductionConfig` | `APP_ENV=production` | platform-specific (see below) | platform-specific |
| `TestingConfig` | pytest | `:memory:` | — |

Platform data dirs (production):
- macOS: `~/Library/Application Support/PDF-Annotator/`
- Linux: `~/.local/share/pdf-annotator/`
- Windows: `%APPDATA%/PDF-Annotator/`

## Key Design Decisions

- **DatabaseManager is a singleton** — `__new__` with thread lock; pass `db_path` only on first instantiation (done in `create_app`). Tests inject `:memory:` via conftest fixture.
- **CSRF exempt for `save_annotation`** — sendBeacon cannot send custom headers; endpoint validates UUID doc_id instead.
- **WAL mode** — enabled per-connection in `get_connection()`; persistent in DB header after first set; no-op on `:memory:`.
- **Render cache** — `_render_page_cached` is an LRU-cached internal function; `render_page_to_image` is the public wrapper that converts None returns to exceptions so cached None values are never stored.
- **Atomic operations** — `append_pdf` and `delete_page` use single `get_connection()` transactions to prevent partial-failure inconsistencies.
