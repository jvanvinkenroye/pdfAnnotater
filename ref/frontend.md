# Frontend Reference

## Templates

All templates extend `base.html`. Jinja2 with `{{ icons.icon(...) }}` macro from `icons.html`.

| Template | Route | Description |
|---|---|---|
| `base.html` | — | Layout, nav, dark mode, CSRF meta tag, `window.__userTheme`, `window.__userAuthenticated`, `window.__desktopMode`, `window.__aiEnabled` |
| `documents.html` | `/documents` | Document table with sorting, export/import buttons |
| `viewer.html` | `/viewer/<doc_id>` | Split-screen PDF viewer + annotation textarea; selectable text overlay (`#pdf-text-layer`); AI-assist button + panel |
| `index.html` | `/` | Landing/redirect |
| `error.html` | error handlers | Generic error page |
| `icons.html` | — | Lucide SVG icon macro library: `icons.icon(name, size, stroke_width)` |
| `auth/login.html` | `/auth/login` | Login form |
| `auth/register.html` | `/auth/register` | Registration form |
| `auth/change_password.html` | `/auth/change-password` | Change-password form |
| `swb_results.html` | `/swb/search` | Library catalog search results (title/author/year/isbn + catalog link) |
| `admin/index.html` | `/admin/` | User management table |

## JavaScript

| File | Used on | Responsibilities |
|---|---|---|
| `documents.js` | Documents page | Table sorting, export/import buttons with loading state, PDF replacement, document deletion |
| `viewer.js` | Viewer page | Page navigation, annotation auto-save (sendBeacon on page change/unload), image loading with error handling, keyboard shortcuts, selectable text overlay (`buildTextLayer`/`syncTextLayerGeometry`), AI-assist panel (edit/generate/context modes), SWB library search button (`window.open()` with the PDF selection) |
| `modal.js` | Global | `showConfirm()`, `showAlert()`, `showToast()` — custom modal dialogs |
| `theme.js` | Global (via base.html) | Dark/light mode toggle, AJAX save to `/auth/theme`, priority: server DB > localStorage > system preference |
| `upload.js` | Upload page | Drag-and-drop upload, form submission, progress feedback |

## Key JS Patterns

### Export button loading state (`documents.js`)
```js
downloadFile(url, 'POST', this)
// btn.disabled = true, btn.textContent = '...' during fetch
// restored in .finally()
```

### Annotation auto-save (`viewer.js`)
```js
// sendBeacon on page change — CSRF-exempt endpoint
navigator.sendBeacon(`/viewer/api/annotation/${docId}/${pageNumber}`, formData)
```

### AI-assist panel modes (`viewer.js`)
Two toolbar buttons open the same inline panel (`#ai-panel`), gated by `window.__aiEnabled`:
- **"✨ KI"** (`ai-assist-btn`): mode decided by note-field selection at open time — `edit` (selection non-empty, replaces it via `setRangeText`) or `generate` (no selection, inserts/replaces at cursor).
- **"✨ KI aus PDF"** (`ai-pdf-btn`): reads `window.getSelection().toString()` (the PDF text overlay) as read-only context — mode `context`, result is always inserted into the note field, never overwrites the PDF quote.

All three POST to `/viewer/api/ai/text`, then call the existing `saveNote(true)` to persist through the normal autosave path.

### Theme priority (`theme.js`)
```
window.__userTheme (set in base.html from DB)
  → localStorage.getItem('theme')
    → window.matchMedia('prefers-color-scheme: dark')
```

## CSS

Single stylesheet: `static/css/styles.css`  
Uses CSS custom properties for theming (dark/light via `[data-theme="dark"]` on `<html>`).

## Icon Library (`icons.html`)

Lucide SVG icons as Jinja2 macros. Usage:
```jinja2
{% import "icons.html" as icons %}
{{ icons.icon('download', 16) }}         {# name, size #}
{{ icons.icon('file', 80, 1.5) }}        {# name, size, stroke_width #}
```

## Keyboard Shortcuts (viewer)

| Shortcut | Action |
|---|---|
| `Ctrl+→` / `Ctrl+↓` | Next page |
| `Ctrl+←` / `Ctrl+↑` | Previous page |
| `Ctrl+Home` | First page |
| `Ctrl+End` | Last page |
| `Ctrl+G` | Go to page (prompt) |
| `Ctrl+Del` | Delete current page |
