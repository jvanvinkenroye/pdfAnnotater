# Development Reference

## Setup

```bash
uv sync                          # install all deps including dev
uv run flask run --port 8000     # dev server (port 5000 blocked by macOS ControlCenter)
uv run pdf-annotator --verbose   # desktop app (port 5123)
```

## Testing

```bash
uv run pytest                    # all 114 tests
uv run pytest tests/test_routes.py -x -q   # specific file, fail-fast
uv run pytest --cov=src          # with coverage
```

### Test Files

| File | Tests | What it covers |
|---|---|---|
| `tests/test_routes.py` | — | Upload, viewer API, export, import endpoints |
| `tests/test_database.py` | — | DatabaseManager CRUD, WAL mode, indices |
| `tests/test_admin.py` | 21 | Admin panel, user management, protection logic |
| `tests/test_pdf_processor.py` | — | Rendering, page count, cache |
| `tests/test_pdf_generator.py` | — | Annotated PDF creation |
| `tests/test_markdown_exporter.py` | — | Markdown output format |
| `tests/test_validators.py` | — | All validator functions |

### conftest.py Fixtures

Key fixtures (always use these, never instantiate DB directly):

| Fixture | Returns | Notes |
|---|---|---|
| `app` | Flask app | `TestingConfig`, `:memory:` DB |
| `client` | test client | anonymous |
| `admin_client` | test client | logged in as admin user |
| `user_client` | test client | logged in as regular user |
| `sample_pdf` | `Path` | minimal valid PDF |
| `uploaded_doc_id` | `str` | doc already in DB with PDF on disk |

## Linting & Formatting

```bash
uv run ruff check .              # lint
uv run ruff format .             # format (max line 88)
uv run mypy src/                 # type check (ignore_missing_imports = true)
```

Config: `ruff.toml`, `pyproject.toml [tool.mypy]`

## Important Gotchas

- **Port 5000 blocked on macOS** — use `--port 8000` for dev server
- **uv tool install caching** — `--force` reuses cached wheel; use `--no-cache` to pick up template/static changes
- **Timestamps are strings** — `detect_types=PARSE_DECLTYPES` removed; all `updated_at`/`upload_timestamp` fields are `str`. Use `[:16]` slicing in templates, never `.strftime()`
- **Singleton DB in tests** — always use `app` fixture; nested app contexts break singleton state
- **sendBeacon + CSRF** — `save_annotation` is CSRF-exempt because sendBeacon can't send custom headers
- **PyMuPDF save()** — cannot save in-place; always use temp file + `replace()`
- **sanitize_filename** — preserves Unicode (Umlaute) intentionally; werkzeug would strip them
- **WAL mode** — persistent after first connection; silent no-op on `:memory:`
- **DESKTOP_MODE** — never set `PDF_ANNOTATOR_DESKTOP_MODE=1` on server/Docker deployments; it makes export routes write files directly into `DESKTOP_EXPORT_DIR` on the server's disk instead of streaming them to the client. Only meant for WebView-based desktop shells (e.g. a future Toga/Briefcase packaging) that cannot handle `Content-Disposition: attachment` responses. `flaskwebgui` (current desktop app) is unaffected — it uses a real Chrome process with a working native download manager.
- **AI Assist (optional)** — note-editor "✨ KI" button is disabled unless `AI_PROVIDER` (`anthropic`|`openai`) plus the matching `ANTHROPIC_API_KEY`/`OPENAI_API_KEY` are set. Privacy: when enabled, the note text and the user's instruction are sent to that third-party API — self-hosters should be aware before setting `AI_PROVIDER`. See `ref/services.md` (`ai_client.py`) for details.

## Packaging

### Desktop (macOS, via Homebrew or uv tool)
```bash
uv tool install .                # installs pdf-annotator to ~/.local/bin
uv tool install --no-cache .     # force rebuild (picks up template changes)
```

### .deb (Linux amd64)
```bash
# Requires Docker
bash packaging/build-deb.sh
# Output: dist/pdf-annotator_<VERSION>_amd64.deb
```

### GitHub Release
Push tag `v*` → CI builds .deb + updates Homebrew tap automatically.

### Production server (Gunicorn)
```bash
gunicorn --workers 4 --bind 0.0.0.0:8000 wsgi:app
# or via systemd: pdf-annotator-server (installed by .deb)
```

Required env var for production:
```bash
SECRET_KEY=<random-hex>   # otherwise sessions invalidate on restart
```

### Environment variables / `.env`

A `.env` file at the project root is loaded automatically via `python-dotenv` (`config.py`, `load_dotenv()`) — existing shell-exported variables always take precedence. Use it for local secrets (`SECRET_KEY`, `AI_PROVIDER`, `ANTHROPIC_API_KEY`/`OPENAI_API_KEY`, ...). Never commit `.env` with real secrets.
