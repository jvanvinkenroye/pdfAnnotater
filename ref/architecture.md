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

`src/pdf_annotator/app.py` — `create_app(config_name, config_overrides=None)`:
1. Loads config from `config.py` (development / production / testing); `config_overrides` dict is applied on top before anything uses it (mainly for tests)
2. If `PDF_ANNOTATOR_BEHIND_PROXY=1`: wraps the WSGI app in ProxyFix (`x_for=1, x_proto=1, x_host=1`), sets `PREFERRED_URL_SCHEME=https` and Secure session/remember cookies (HSTS is added in `@after_request`)
3. Sets up Flask-Login, CSRF protection (Flask-WTF), rate limiter (Flask-Limiter, storage from `RATELIMIT_STORAGE_URI`, default `memory://`)
4. Creates a `DatabaseManager` instance, stores it in `app.extensions["db"]` (fetched via `get_db()`), calls `init_db()` (runs versioned migrations)
5. Starts the periodic cleanup thread (`services/cleanup.py`) — skipped in tests and in the Werkzeug reloader parent
6. Registers all blueprints
7. Adds `/health` endpoint (no auth, rate-limit exempt)
8. Attaches security headers via `@after_request`
9. Registers app-level 400/403/404 handlers that content-negotiate JSON vs the HTML error page (see `routes/_helpers.py: wants_json`)

## Blueprint Layout

| Blueprint | Prefix | File | Notes |
|---|---|---|---|
| `auth_bp` | `/auth` | `routes/auth.py` | |
| `upload_bp` | `/` | `routes/upload.py` | |
| `viewer_bp` | `/viewer` | `routes/viewer.py` | incl. job-status polling: `GET /viewer/api/jobs/<job_id>` |
| `export_bp` | `/export` | `routes/export.py` | incl. job-artifact download: `GET /export/download/<job_id>` |
| `admin_bp` | `/admin` | `routes/admin.py` | |
| `ai_bp` | `/viewer/api/ai` | `routes/ai.py` | |
| `swb_bp` | `/swb` | `routes/swb.py` | |

## Layer Diagram

```
Browser / CLI
    │
Flask Routes (routes/)
    ├── _helpers.py    shared route helpers (get_owned_document, wants_json, handle_errors)
    ├── auth.py        login, register, logout, theme (Flask-WTF forms in forms.py)
    ├── upload.py      upload, delete, export-zip, import-zip
    ├── viewer.py      view, page-image, annotation CRUD, replace, append, delete-page,
    │                  OCR job (202), job-status polling
    ├── export.py      download original PDF, annotated-PDF export job (202),
    │                  job-artifact download, export MD (sync)
    └── admin.py       user management (admin-only)
    │
Services (services/)
    ├── pdf_processor.py    PyMuPDF rendering, page count, text layout
    ├── render_cache.py     shared disk cache for page PNGs + text layouts
    ├── jobs.py             in-process background jobs (OCR, PDF export)
    ├── cleanup.py          periodic maintenance thread (exports, jobs, cache prune)
    ├── pdf_generator.py    annotated PDF creation (green Courier footer)
    ├── markdown_exporter.py Markdown note export
    └── data_manager.py     ZIP export/import of all user data
    │
Models (models/)
    ├── database.py    SQLite DatabaseManager (one per app, in app.extensions["db"])
    ├── migrations.py  versioned schema migrations (PRAGMA user_version)
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

- **DatabaseManager is NOT a singleton** — one instance per app, created in `create_app()` and stored in `app.extensions["db"]`; routes and services fetch it via `get_db()`. Instances are cheap and thread-safe (every operation opens its own connection). Tests inject `:memory:` via `config_overrides`.
- **Schema migrations** — versioned via `PRAGMA user_version` with a `MIGRATIONS` list in `models/migrations.py` (baseline + `_m002_jobs`); `init_db()` applies pending migrations.
- **CSRF everywhere, including `save_annotation`** — the frontend sends `X-CSRFToken` on all mutating requests; the final save on page unload uses `fetch` with `keepalive: true` (which can carry headers) instead of `sendBeacon`, so the former CSRF exemption is gone.
- **SQLite pragmas** — per-connection in `get_connection()`: `foreign_keys=ON`, `journal_mode=WAL` (persistent in DB header after first set; no-op on `:memory:`), `busy_timeout=10000`, `synchronous=NORMAL`.
- **Render cache on disk** — page PNGs and text layouts are cached under `RENDER_CACHE_FOLDER` (`services/render_cache.py`), keyed by resolved path + mtime + size, so file mutations auto-invalidate across all workers; pruned LRU to `RENDER_CACHE_MAX_BYTES` by the cleanup thread. Replaces the old per-process `lru_cache`.
- **Background jobs, no broker** — OCR and annotated-PDF export run on a one-thread `ThreadPoolExecutor` per process (`services/jobs.py`); status lives in the shared SQLite `jobs` table, artifacts on the shared filesystem, so any Gunicorn worker can answer polls.
- **Cleanup thread** — `services/cleanup.py` runs every 15 min per process (flock dedupes across workers): deletes exports > 1 h, flips orphaned jobs to error, deletes finished jobs > 24 h with artifacts, prunes the render cache.
- **Atomic operations** — `append_pdf` and `delete_page` use single `get_connection()` transactions to prevent partial-failure inconsistencies.
