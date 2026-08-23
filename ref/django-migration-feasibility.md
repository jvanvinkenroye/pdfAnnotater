# Django Migration Feasibility

## Question

Would the app be improved by migrating from Flask to Django?

## Verdict

**Possible, but not recommended right now.** Roughly half of the codebase's real pain points map directly onto machinery Django ships out of the box (ORM + migrations, forms, admin, auth flows, security settings). The other half — including the worst operational issues — are framework-independent and would survive a migration untouched. The cost is a near-total rewrite: ~5.6k LOC of application Python, 35 endpoints across 7 blueprints, 11 templates, and 178 tests, plus repackaging the desktop/`.deb` distribution.

Recommendation: stay on Flask and fix the specific gaps incrementally (see [Cheaper alternative](#cheaper-alternative-recommended)). Revisit Django only if the roadmap is a hosted multi-user service, where the admin/auth/permissions machinery pays rent continuously.

## What Django would genuinely improve

| Pain point today | Where | Django equivalent |
|---|---|---|
| Raw SQLite behind a `DatabaseManager` singleton; migrations are try/except `ALTER TABLE` loops with no version table or rollback; entities are `sqlite3.Row` dicts (key typos become runtime `KeyError`s); singleton ignores app config after first init, forcing tests to reset `DatabaseManager._instance` manually | `models/database.py` (839 lines), `tests/conftest.py` | ORM models + `makemigrations`/`migrate`; Postgres becomes a settings change |
| Hand-rolled validation layer plus ~85 lines of procedural form checks in registration; Flask-WTF is installed but used only for CSRF | `utils/validators.py` (337 lines), `routes/auth.py:91-176` | Forms / ModelForms with declarative validation |
| Custom admin panel, including two near-identical 40-line toggle functions (the pyscn clone group) | `routes/admin.py` + `templates/admin/index.html` (320 lines) | `django.contrib.admin`, nearly free |
| No password reset, no email verification, no account lockout, password policy is only `len >= 8` | `routes/auth.py` | `django.contrib.auth` password-reset flows and pluggable password validators |
| No `SESSION_COOKIE_SECURE/HTTPONLY/SAMESITE`, no `ProxyFix` despite the documented TLS-reverse-proxy deployment, ephemeral fallback `SECRET_KEY` in production (restart or a second Gunicorn worker breaks sessions) | `config.py` | Conventional settings + `manage.py check --deploy` catches these |
| Repeated "validate doc_id → fetch → check ownership" blocks and ~15 near-identical try/except-with-error-message wrappers per route | `routes/viewer.py`, `routes/upload.py`, `routes/export.py` | `get_object_or_404`, queryset filtering by owner, exception middleware |

## What Django would NOT fix

These are the most serious operational issues, and they are framework-independent:

- **Synchronous OCR and PDF export inside requests.** `OCR_TIMEOUT_SECONDS = 600` is why the Gunicorn timeout is 600 s; one OCR request blocks a worker for up to 10 minutes. The fix is a task queue (Celery/RQ or Django 6's tasks framework) — plumbing work on either framework.
- **SQLite under multiple Gunicorn workers** hits `database is locked` under concurrent writes. The fix is Postgres, available to Flask via SQLAlchemy just as well.
- **Per-process `lru_cache` for rendered page images** (`services/pdf_processor.py`): `clear_render_cache()` only clears the calling worker's cache, so other workers can serve stale pages after a PDF replace or OCR — the reason the cache-buster workaround exists. The fix is a shared cache (Redis); Django's cache framework helps slightly but doesn't remove the work.
- **Cleanup piggybacked on requests** (`cleanup_old_exports()` in `routes/export.py`) needs a scheduler either way.
- The ~1.9k LOC vanilla-JS frontend, 2.3k lines of CSS, and the PDF/OCR/AI service layer (`services/`) are framework-neutral and would port as-is — i.e., they gain nothing.

## Migration cost

- Rewrite all 35 endpoints, the Flask-Login integration, and most of the 178 tests; convert or adapt 11 Jinja2 templates (Django can run Jinja2, but URL reversing, CSRF tags, and auth context differ).
- The desktop distribution (flaskwebgui + bundled-venv `.deb` + systemd unit + platform data dirs in `desktop.py`/`packaging/`) is built around an embedded single-process Flask app. flaskwebgui supports Django, but `manage.py`-style startup, `STATIC_ROOT`/`collectstatic`, and the settings module layout all require rework.
- Realistic effort: several weeks with meaningful regression risk, for little user-visible gain.

## Cheaper alternative (recommended)

Incremental hardening within Flask, ordered by impact:

1. **Security config**: set `SESSION_COOKIE_SECURE/HTTPONLY/SAMESITE` in `config.py`, add `werkzeug.middleware.proxy_fix.ProxyFix` for the documented reverse-proxy deployment, and make production fail hard when `SECRET_KEY` is unset instead of generating an ephemeral one.
2. **Background jobs**: move OCR and 300-DPI export into a task queue (RQ is the lightest fit alongside a Redis cache); drop the 600 s Gunicorn timeout.
3. **Database**: adopt Alembic for versioned migrations (keeping raw SQLite or moving to SQLAlchemy Core), set `busy_timeout`, and offer a Postgres option for multi-worker deployments. Refactor `DatabaseManager` to read config per-app instead of process-global state.
4. **Forms**: use Flask-WTF form classes (already a dependency) for register/login/metadata, retiring most of `utils/validators.py`.
5. **Shared render cache**: replace the per-process `lru_cache` with Redis (or accept single-worker deployments and document it).
6. **Deduplicate**: extend the `_get_doc_or_error()` pattern from `routes/viewer.py` across `upload.py`/`export.py`, and collapse the per-route try/except blocks into Flask error handlers.

Each step is independently shippable and testable against the existing suite, whereas a Django migration is all-or-nothing.
