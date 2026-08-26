# Database Reference

## Schema

Versioned via `PRAGMA user_version`: `models/migrations.py` holds a `MIGRATIONS` list (`_m001_baseline` = users/documents/annotations + indices + trigger, `_m002_jobs` = jobs table). `init_db()` calls `apply_migrations(conn)`, which runs the pending entries in order and stamps the version after each step. The baseline is idempotent (IF NOT EXISTS / try-ALTER) so pre-versioning databases converge. New schema changes are added as a new function appended to `MIGRATIONS` — never by editing an existing one.

### `users`
```sql
CREATE TABLE users (
    id TEXT PRIMARY KEY,           -- UUID
    username TEXT NOT NULL UNIQUE,
    email TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,   -- werkzeug generate_password_hash
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_active INTEGER DEFAULT 1,
    is_admin INTEGER DEFAULT 0,
    theme TEXT DEFAULT NULL        -- 'dark' | 'light' | NULL
)
```

### `documents`
```sql
CREATE TABLE documents (
    id TEXT PRIMARY KEY,           -- UUID
    user_id TEXT NOT NULL,         -- FK → users.id CASCADE DELETE
    original_filename TEXT NOT NULL,
    file_path TEXT NOT NULL,       -- absolute path to PDF on disk
    page_count INTEGER NOT NULL,
    first_name TEXT DEFAULT '',
    last_name TEXT DEFAULT '',
    title TEXT DEFAULT '',
    year TEXT DEFAULT '',
    subject TEXT DEFAULT '',
    upload_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
```

### `annotations`
```sql
CREATE TABLE annotations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    doc_id TEXT NOT NULL,          -- FK → documents.id CASCADE DELETE
    page_number INTEGER NOT NULL,  -- 1-indexed
    note_text TEXT DEFAULT '',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(doc_id, page_number)
)
```

**Indices:**
- `idx_annotations_doc_id` ON `annotations(doc_id)`
- `idx_annotations_page` ON `annotations(doc_id, page_number)`
- `idx_annotations_updated_at` ON `annotations(updated_at)` — speeds up `MAX(updated_at)` in `get_all_documents()`

**Trigger:** `update_annotation_timestamp` — sets `updated_at = CURRENT_TIMESTAMP` on any annotation UPDATE.

### `jobs`
```sql
CREATE TABLE jobs (
    id TEXT PRIMARY KEY,           -- UUID
    type TEXT NOT NULL,            -- 'ocr' | 'export_pdf'
    doc_id TEXT NOT NULL,          -- FK → documents.id CASCADE DELETE
    user_id TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',  -- pending|running|done|error
    result_path TEXT,              -- artifact on disk (export PDF)
    result_json TEXT,              -- remaining runner result as JSON
    error TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    started_at TIMESTAMP,
    finished_at TIMESTAMP
)
```

**Indices:** `idx_jobs_doc_type_status` ON `jobs(doc_id, type, status)`, `idx_jobs_status` ON `jobs(status)`.

## DatabaseManager

**No longer a singleton.** One instance per application: `create_app()` builds `DatabaseManager(app.config["DATABASE_PATH"])` and stores it in `app.extensions["db"]`. Fetch it with `get_db()` (requires an application context); background job runners receive the instance explicitly in their closure instead of calling `get_db()`. Instances are cheap and thread-safe — every operation opens its own connection, so a background thread may share an instance with request handlers.

Import: `from pdf_annotator.models.database import DatabaseManager, get_db`.

### Connection

```python
with db.get_connection() as conn:
    conn.execute(...)
```

- Opens fresh SQLite connection per call
- Sets `PRAGMA foreign_keys = ON`, `PRAGMA journal_mode=WAL`, `PRAGMA busy_timeout = 10000` (wait instead of "database is locked" when another worker/thread holds the write lock), `PRAGMA synchronous = NORMAL` (safe with WAL, faster than FULL)
- Commits on exit, rollbacks on `sqlite3.Error`, always closes
- WAL mode is persistent in the DB file header after first set

### Timestamps

`detect_types=sqlite3.PARSE_DECLTYPES` is **not** set (removed for Python 3.12 compatibility). All timestamps come back as **plain strings** in `"YYYY-MM-DD HH:MM:SS"` format. Use `[:16]` slicing in templates.

### Methods

#### Documents

| Method | Returns | Notes |
|---|---|---|
| `create_document(user_id, filename, file_path, page_count, ...)` | `str` (doc_id UUID) | Also creates blank annotation rows for all pages |
| `get_document(doc_id)` | `dict \| None` | Includes all metadata fields |
| `update_document_metadata(doc_id, first_name, last_name, title, year, subject)` | `bool` | |
| `update_page_count(doc_id, page_count)` | `bool` | |
| `delete_document(doc_id)` | `bool` | Cascades to annotations via FK |
| `get_all_documents(user_id)` | `list[dict]` | Includes `last_edited` (MAX updated_at) per doc |

#### Annotations

| Method | Returns | Notes |
|---|---|---|
| `upsert_annotation(doc_id, page_number, note_text)` | `None` | Atomic `INSERT ... ON CONFLICT DO UPDATE` |
| `get_annotation(doc_id, page_number)` | `dict \| None` | |
| `get_all_annotations(doc_id)` | `list[dict]` | Ordered by page_number |
| `delete_annotation(doc_id, page_number)` | `bool` | Single annotation |
| `renumber_annotations_after_delete(doc_id, deleted_page)` | `None` | Shifts page_number down + updates page_count (two separate ops) |
| `delete_annotation_and_renumber(doc_id, deleted_page)` | `None` | **Atomic** version: DELETE + renumber + page_count in one transaction |

#### Users

| Method | Returns | Notes |
|---|---|---|
| `create_user(username, email, password_hash)` | `str` (user_id UUID) | |
| `get_user_by_id(user_id)` | `dict \| None` | |
| `get_user_by_username(username)` | `dict \| None` | |
| `get_all_users()` | `list[dict]` | Admin use only |
| `set_user_active(user_id, is_active)` | `bool` | |
| `set_user_admin(user_id, is_admin)` | `bool` | |
| `delete_user(user_id)` | `bool` | Cascades to documents + annotations |
| `count_users()` | `int` | |
| `count_admins()` | `int` | Used to protect last-admin |
| `update_password(user_id, password_hash)` | `bool` | |
| `set_user_theme(user_id, theme)` | `bool` | |

#### Background jobs

| Method | Returns | Notes |
|---|---|---|
| `create_job(job_type, doc_id, user_id)` | `str` (job_id UUID) | Inserts a `pending` row |
| `get_job(job_id)` | `dict \| None` | |
| `get_active_job(doc_id, job_type)` | `dict \| None` | Latest `pending`/`running` job of that type for the document — used for the duplicate-OCR 409 guard |
| `mark_job_running(job_id)` | `None` | Sets status + `started_at` |
| `finish_job(job_id, status, result_path=None, result_json=None, error=None)` | `None` | Terminal status `'done'` or `'error'`, stamps `finished_at` |
| `mark_stale_jobs_failed(older_than_seconds)` | `int` | Flips orphaned `pending`/`running` jobs to `error` (cleanup thread) |
| `delete_finished_jobs(older_than_seconds)` | `list[str]` | Deletes old `done`/`error` rows, returns their `result_path`s so the caller can unlink artifacts |

## Testing Notes

- Tests use `:memory:` DB via `TestingConfig`
- Fixtures inject db via the `app` fixture (`create_app` stores the instance in `app.extensions["db"]`); use `get_db()` inside an app context rather than instantiating `DatabaseManager()` ad hoc
- No nested app contexts in tests
