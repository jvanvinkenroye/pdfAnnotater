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
Public API. Calls `_render_page_cached` internally; catches exceptions and returns `None` instead of propagating (so `None` is never stored in cache).

**`_render_page_cached(file_path: str, page_num: int, dpi: int) -> bytes`** *(internal, LRU-cached)*  
Raises exception on failure — ensures only successful renders are cached.

**`clear_render_cache() -> None`**  
Clears LRU cache. Called after PDF replace/append/delete-page operations.

**`get_cache_info() -> dict`**  
Returns `functools.lru_cache` stats for `_render_page_cached`.

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
