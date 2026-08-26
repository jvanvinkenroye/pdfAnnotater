# API Reference

All endpoints require login (`@login_required`) unless noted. CSRF token required for all POST/DELETE via `X-CSRFToken` header or form field — including `save_annotation` (no longer CSRF-exempt: the unload-save uses `fetch` with `keepalive: true` + `X-CSRFToken` on `pagehide` instead of `sendBeacon`).

## Auth — `/auth`

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/auth/login` | — | Login page |
| POST | `/auth/login` | — | Submit credentials; rate-limited 5/min |
| GET | `/auth/logout` | ✓ | Logout |
| GET | `/auth/register` | — | Registration page; 403 when `PDF_ANNOTATOR_REGISTRATION=0` (unless no user exists yet) |
| POST | `/auth/register` | — | Create account (first user becomes admin; first user may always register even when self-registration is disabled). With `PDF_ANNOTATOR_INVITE_CODE` set, a matching invite code is required. Forms are Flask-WTF (`forms.py`); messages/status codes unchanged |
| GET | `/auth/change-password` | ✓ | Change-password page |
| POST | `/auth/change-password` | ✓ | Verify current password, set new one (min. 8 chars) |
| POST | `/auth/theme` | ✓ | Save dark/light theme; rate-limited 30/min |

## Upload / Documents — `/`

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/` | ✓ | Redirect to documents list |
| GET | `/documents` | ✓ | Documents list page |
| POST | `/upload` | ✓ | Upload PDF; rate-limited 10/min |
| DELETE | `/delete/<doc_id>` | ✓ | Delete document + annotations |
| GET | `/export` | ✓ | Download all data as ZIP |
| GET | `/export/info` | ✓ | Export metadata (counts, size estimate) |
| POST | `/import` | ✓ | Import ZIP; rate-limited 10/min |

## Viewer — `/viewer`

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/viewer/<doc_id>` | ✓ | Viewer page (HTML) |
| GET | `/viewer/api/page/<doc_id>/<page>` | ✓ | Render page as PNG; rate-limited 60/min |
| GET | `/viewer/api/page/<doc_id>/<page>/text` | ✓ | Word bounding boxes for the selectable text overlay |
| GET | `/viewer/api/annotation/<doc_id>/<page>` | ✓ | Get annotation JSON |
| POST | `/viewer/api/annotation/<doc_id>/<page>` | ✓ | Save annotation (CSRF-protected like everything else) |
| POST | `/viewer/api/metadata/<doc_id>` | ✓ | Update document metadata |
| POST | `/viewer/api/replace/<doc_id>` | ✓ | Replace PDF file (keeps annotations) |
| POST | `/viewer/api/append/<doc_id>` | ✓ | Append pages from another PDF |
| POST | `/viewer/api/ocr/<doc_id>` | ✓ | Start OCR as a background job → **202** `{"success": true, "job_id": ...}`; **409** if an OCR job is already pending/running for this document; rate-limited 3/min; 501 if tesseract missing |
| GET | `/viewer/api/jobs/<job_id>` | ✓ | Poll background job status (OCR, PDF export) → `{"status": "pending"\|"running"\|"done"\|"error", "error": str\|null, "result": {...}}`; 404 unknown job, 403 not owner |
| DELETE | `/viewer/api/page/<doc_id>/<page>` | ✓ | Delete a page |

## Export — `/export`

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/export/original/<doc_id>` | ✓ | Download original PDF |
| POST | `/export/pdf/<doc_id>` | ✓ | Start annotated-PDF export as a background job → **202** `{"success": true, "job_id": ...}`; poll via `GET /viewer/api/jobs/<job_id>`, then fetch the file from `/export/download/<job_id>` |
| GET | `/export/download/<job_id>` | ✓ | Download the finished export artifact (Desktop-Mode JSON supported); **409** while the job is still pending/running; 404 unknown job or vanished file; 403 not owner |
| POST | `/export/markdown/<doc_id>` | ✓ | Generate and download Markdown notes (synchronous) |

## AI Assist — `/viewer/api/ai`

Only active when `AI_PROVIDER` is configured (see `ref/services.md`). Stateless — not tied to any document, no ownership check.

| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/viewer/api/ai/text` | ✓ | Edit/generate note text; rate-limited 10/min |

Request body: `{"mode": "edit" \| "generate" \| "context", "instruction": str, "source_text": str}`.
- `edit`: rewrites `source_text` (the note-field selection) per `instruction` — response replaces the selection.
- `generate`: formulates new note text from `instruction` alone (`source_text` ignored) — response is inserted at the cursor, or replaces the field if empty.
- `context`: formulates a note from a read-only `source_text` (e.g. a PDF quote from the viewer's text overlay) plus `instruction` — response is inserted at the cursor, never overwrites the source.

Response: `{"result": str}` on success. Errors: 400 (validation / feature disabled), 503 (provider configured but API key missing), 500 (provider request failed).

## Library Search — `/swb`

Stateless — not tied to any document, no ownership check. Always active, no config required (public SWB endpoint).

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/swb/search` | ✓ | Search library catalogs; renders HTML results page; rate-limited 15/min |

Query param `q`: search text (e.g. selected in the PDF viewer's text overlay). Opened via `window.open()` in a new tab, not fetched via AJAX. Errors render inline on the same page (400 validation, 503 search failure, 500 internal).

## Admin — `/admin`

All admin routes require `@admin_required` (is_admin=1 in DB).

| Method | Path | Description |
|---|---|---|
| GET | `/admin/` | Admin dashboard (user list) |
| POST | `/admin/user/<user_id>/toggle_active` | Activate/deactivate user |
| POST | `/admin/user/<user_id>/toggle_admin` | Grant/revoke admin |
| DELETE | `/admin/user/<user_id>` | Delete user |

## Health — `/`

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/health` | — | `{"status":"ok","db":"ok"}` / 503 on DB error |

## Common Response Patterns

**Success:** `{"success": true, ...}` with HTTP 200  
**Error:** `{"error": "message"}` with HTTP 400/403/404/500  
**Ownership violation:** HTTP 403  
**Not found:** HTTP 404  

## Helper: `get_owned_document(doc_id)` (`routes/_helpers.py`)

Used by all document-bound endpoints. Validates the UUID, fetches the document, and verifies ownership against `current_user.id` — or aborts with 400 (invalid id), 404 (unknown document), or 403 (owned by someone else). The app-level 400/403/404 handlers render the abort as JSON for API paths (see `wants_json()`) or as the HTML error page for browser requests. `handle_errors(...)` (same module) replaces per-route try/except blocks: HTTPExceptions pass through to the app handlers, anything else is logged and answered as 500.
