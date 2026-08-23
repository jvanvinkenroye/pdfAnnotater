# Services Reference

## pdf_processor.py

PDF rendering and metadata via PyMuPDF (fitz).

### Functions

**`validate_pdf(file_path: Path) -> bool`**  
Opens file with fitz, returns False on exception.

**`get_page_count(file_path: Path) -> int`**  
Returns number of pages. Used by `replace_pdf` (append_pdf uses `doc_info["page_count"] + added_pages` instead).

**`get_page_dimensions(file_path: Path, page_num: int) -> tuple[float, float]`**  
Returns `(width, height)` in points for the given page (1-indexed).

**`render_page_to_image(file_path: str, page_num: int, dpi: int = 300) -> bytes | None`**  
Public API. Serves from the shared disk cache (`render_cache.get_or_render_page`) when an app context provides `RENDER_CACHE_FOLDER`; renders via the internal `_render_page` on miss. Catches exceptions and returns `None` instead of propagating (errors are never cached).

**`get_page_text_layout(file_path: str, page_num: int) -> dict`**  
Word-level text with bounding boxes for the selectable text overlay. Served from the shared disk cache (`render_cache.get_or_load_layout`); extraction (`_extract_text_layout`) raises on invalid pages so errors are never cached.

**`_render_page(file_path: str, page_num: int, dpi: int) -> bytes`** *(internal)*  
Raises exception on failure — ensures only successful renders are cached.

Note: the old per-process `functools.lru_cache` and its helpers (`clear_render_cache`, `clear_text_layout_cache`, `get_cache_info`) are gone — the disk cache is keyed by file identity (path + mtime + size), so PDF mutations (replace/append/OCR/delete-page) invalidate automatically in every worker; no explicit cache clearing exists or is needed.

---

## render_cache.py

Disk-based cache for rendered page PNGs and text layouts, shared by all Gunicorn workers. Lives under `RENDER_CACHE_FOLDER` (prod: `<data_dir>/cache`); size budget `RENDER_CACHE_MAX_BYTES` (default 512 MB).

Entries are keyed by the PDF's content identity — sha1 of `resolved path | mtime_ns | size` — so every file mutation changes the key and stale entries are simply never hit again (no cross-process invalidation signal). Reads refresh the entry's mtime; `prune()` (called by the cleanup thread) evicts least-recently-used entries until the cache fits the budget, removes leftover temp files, and drops empty directories. Writes are atomic (unique temp name + `os.replace`), so concurrent workers may render the same page twice (harmless) but never serve a torn file.

**`get_or_render_page(cache_dir, file_path, page_num, dpi, render) -> bytes`**  
**`get_or_load_layout(cache_dir, file_path, page_num, extract) -> dict`**  
**`prune(cache_dir, max_bytes) -> int`** — returns bytes freed.

---

## jobs.py

In-process background jobs for long-running work (OCR, annotated-PDF export). One worker thread per process (`ThreadPoolExecutor(max_workers=1)`) runs jobs off the request path; status lives in the shared SQLite `jobs` table and artifacts on the shared filesystem, so with multiple Gunicorn workers any worker can answer a poll for a job another worker is running. No broker or external queue; the same code path serves the single-process desktop app.

**`submit_job(db, job_type, doc_id, user_id, runner) -> str`**  
Inserts a `pending` job row and executes `runner` on the background thread. Returns the job_id (polled via `GET /viewer/api/jobs/<job_id>`). The runner must not touch `current_app`/`request`/`current_user` — everything it needs (db instance, file paths, config values) is captured in the closure at submit time. The runner returns a result dict; `"result_path"` is persisted to `jobs.result_path`, the rest to `result_json`. Exceptions mark the job `error` with the message.

Constants: `JOB_STALE_SECONDS = 900` (pending/running older than this is considered orphaned and flipped to error by cleanup; exceeds the OCR timeout with margin), `FINISHED_JOB_RETENTION_SECONDS = 24 * 3600` (terminal rows + artifacts removed after this age).

---

## cleanup.py

Periodic maintenance, moved off the request path. `start_cleanup_thread(app)` (called from `create_app`, skipped in tests) starts one daemon thread per process that wakes every 15 minutes (`CLEANUP_INTERVAL_SECONDS`, plus jitter; first round ~10 s after startup so jobs orphaned by a crash/deploy are recovered promptly) and:

- deletes export artifacts older than 1 h (`EXPORT_MAX_AGE_SECONDS`)
- flips orphaned background jobs to `error` (`mark_stale_jobs_failed`)
- deletes finished job rows older than 24 h and unlinks their artifacts
- prunes the render cache to `RENDER_CACHE_MAX_BYTES`

Every task is idempotent; with multiple Gunicorn workers a non-blocking `flock` on `<data_dir>/cleanup.lock` merely skips redundant rounds (on platforms without `fcntl` the lock is skipped entirely).

---

## pdf_generator.py

Creates annotated PDFs with green Courier text injected into page footers.

### Functions

**`calculate_footer_rect(page_rect: fitz.Rect, footer_height: float = 80) -> fitz.Rect`**  
Returns the footer rectangle at the bottom of a page.

**`add_annotation_to_page(page, note_text, timestamp, config) -> None`**  
Draws a white background rect in the footer, then inserts text with:
- Font: `courier` (configurable via `PDF_ANNOTATION_FONT`)
- Color: `(0, 0.5, 0)` green (configurable via `PDF_ANNOTATION_COLOR`)
- Font size: 9pt (configurable via `PDF_ANNOTATION_FONTSIZE`)
- Prepends timestamp: `[YYYY-MM-DD HH:MM]`

**`create_annotated_pdf(file_path, annotations, output_path, config) -> Path`**  
Opens original PDF, iterates pages, calls `add_annotation_to_page` for pages with non-empty notes, saves to `output_path`.

**`generate_annotated_filename(doc_info, last_edited) -> str`**  
Builds filename: `{last_name}_{first_name}_{year}_{base}_annotiert_{timestamp}.pdf` (falls back gracefully for missing fields).

---

## markdown_exporter.py

Generates Markdown files from annotations.

Produces a document with metadata header (name, title, year, subject) followed by per-page sections showing note text. Only pages with non-empty notes are included. Page numbers are noted inline.

---

## data_manager.py

ZIP-based full data export/import.

### `DataManager(upload_folder, db=None)`

**`export_data(user_id, doc_ids=None) -> Path`**  
Creates a ZIP at `EXPORT_FOLDER` containing:
- `data.json` — all document metadata + annotations
- `pdfs/` — PDF files

**`import_data(zip_path, user_id) -> dict`**  
Reads ZIP, always generates **new UUIDs** for all imported documents (prevents conflicts when multiple users import the same backup). Returns `{"imported": N, "errors": [...]}`.

**`get_export_info(doc_ids=None) -> dict`**  
Returns `{document_count, annotation_count, estimated_size_mb}` without creating a file.

**`_update_document_id(doc_data, pdf_dest)`** *(internal)*  
Rewrites `doc_id` references when importing.

**`_is_version_compatible(version) -> bool`** *(internal)*  
Checks ZIP `data.json` version field.

---

## ai_client.py

Optional AI-assisted note editing (edit selected note text, generate note text from bullet points, or formulate a note from a read-only PDF-quote context). Disabled by default.

**`generate_text(mode, instruction, source_text) -> str`**  
`mode` is `"edit"` (rewrite `source_text` per `instruction`), `"generate"` (formulate from `instruction` alone, `source_text` ignored), or `"context"` (formulate a note from a read-only context excerpt — e.g. a PDF quote — plus `instruction`). Dispatches to the provider configured via `AI_PROVIDER` (`"anthropic"` | `"openai"` | unset). Raises `AIFeatureDisabledError` if unset, `AIConfigError` if the provider's API key is missing, `AIProviderError` on request failure.

**Env vars:** `AI_PROVIDER`, `AI_MODEL` (optional override; defaults `claude-haiku-4-5` / `gpt-4o-mini`), `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `OPENAI_BASE_URL` (optional — points the OpenAI SDK at any OpenAI-compatible endpoint instead of `api.openai.com`, e.g. a university-hosted gateway; combine with `AI_MODEL` set to that endpoint's model name).

Route: `POST /viewer/api/ai/text` (`routes/ai.py`) — stateless, not tied to a document, only `@login_required` + rate limit (10/min). Frontend gated by `window.__aiEnabled` (`config.AI_PROVIDER` truthy).

## ocr.py

OCR for scanned documents (in-app "OCR" button in the viewer).

**`ocr_pdf(file_path, language="deu+eng") -> None`**  
Runs `ocrmypdf --skip-text` in a subprocess (its Python API isn't thread-safe in a web worker) to add a searchable text layer in place; temp file + replace, 600s subprocess timeout. Raises `OCRError` on failure. Invoked as a **background job** (see `jobs.py`): `POST /viewer/api/ocr/<doc_id>` returns 202 + `job_id` (409 if an OCR job is already active for the document), the frontend polls `GET /viewer/api/jobs/<job_id>` — the request no longer blocks a Gunicorn worker for the duration of the OCR run. **`ocr_available()`** checks for the tesseract binary — exposed to templates as `ocr_available` (context processor) and to JS as `window.__ocrAvailable`; the route returns 501 when missing. Docker image installs `tesseract-ocr` + `deu`/`eng` language packs + ghostscript; on macOS use `brew install tesseract ocrmypdf`.

Note: pages with a `/Rotate` flag (typical for scans) are handled in `pdf_processor.get_page_text_layout()` — word boxes are mapped through `page.rotation_matrix` into rendered space, since `get_text("words")` reports unrotated coordinates while `get_pixmap()` renders rotated.

## swb_client.py

Library catalog search for the "🔎 SWB-Suche" button (PDF-viewer text selection). Always active, no config/API key required.

**`search_books(query, max_results=20) -> list[dict]`**  
Wraps the `swb` package's Python API (`swb.api.SWBClient`, sibling project at `/Users/java/src_own/swb`, added as a local path dependency) — not its CLI, since the CLI has no machine-readable output format. Uses `SearchIndex.ALL` for a forgiving free-text search, against the **K10plus** profile (`swb.profiles.get_profile("k10plus")`) rather than the package's own default "swb" profile — the default only covers the regional SWB network (Baden-Württemberg/Saarland/Sachsen), which was missing books held elsewhere; K10plus is the broader union catalog. Maps `SearchResponse.results` (`SearchResult` dataclasses) to plain dicts: `title`, `author`, `year`, `isbn`, `link`. Raises `SWBSearchError` on request failure (network error or malformed response from the underlying API).

Route: `GET /swb/search` (`routes/swb.py`) — stateless, `@login_required`, rate-limited 15/min. Renders `templates/swb_results.html` directly (no JSON endpoint) — the button does `window.open()` to this URL in a new tab rather than a fetch/AJAX round-trip.
