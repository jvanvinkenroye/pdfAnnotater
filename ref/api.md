# API Reference

All endpoints require login (`@login_required`) unless noted. CSRF token required for all POST/DELETE via `X-CSRFToken` header or form field (except `save_annotation` which is CSRF-exempt).

## Auth — `/auth`

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/auth/login` | — | Login page |
| POST | `/auth/login` | — | Submit credentials; rate-limited 5/min |
| GET | `/auth/logout` | ✓ | Logout |
| GET | `/auth/register` | — | Registration page |
| POST | `/auth/register` | — | Create account (first user becomes admin) |
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
| POST | `/viewer/api/annotation/<doc_id>/<page>` | ✓ | Save annotation (CSRF-exempt, sendBeacon) |
| POST | `/viewer/api/metadata/<doc_id>` | ✓ | Update document metadata |
| POST | `/viewer/api/replace/<doc_id>` | ✓ | Replace PDF file (keeps annotations) |
| POST | `/viewer/api/append/<doc_id>` | ✓ | Append pages from another PDF |
| DELETE | `/viewer/api/page/<doc_id>/<page>` | ✓ | Delete a page |

## Export — `/export`

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/export/original/<doc_id>` | ✓ | Download original PDF |
| POST | `/export/pdf/<doc_id>` | ✓ | Generate and download annotated PDF |
| POST | `/export/markdown/<doc_id>` | ✓ | Generate and download Markdown notes |

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

## Helper: `_get_doc_or_error(doc_id)`

Used by all viewer API endpoints. Returns `(doc_info, None)` on success or `(None, error_tuple)` on failure. Validates UUID, checks document exists, checks ownership against `current_user.id`.
