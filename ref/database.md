# Database Reference

## Schema

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

## DatabaseManager

Singleton (`__new__` + threading.Lock). Import: `from pdf_annotator.models.database import DatabaseManager`.

**Instantiation:** `DatabaseManager(db_path)` — only the first call sets `_db_path`. All subsequent calls ignore `db_path`.

### Connection

```python
with db.get_connection() as conn:
    conn.execute(...)
```

- Opens fresh SQLite connection per call
- Sets `PRAGMA foreign_keys = ON` and `PRAGMA journal_mode=WAL`
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
| `set_user_theme(user_id, theme)` | `bool` | |

## Testing Notes

- Tests use `:memory:` DB via `TestingConfig`
- Fixtures inject db via `app` fixture parameter — never instantiate `DatabaseManager()` directly in tests (singleton issue)
- No nested app contexts in tests
