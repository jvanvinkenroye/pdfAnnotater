# Frontend Reference

## Templates

All templates extend `base.html`. Jinja2 with `{{ icons.icon(...) }}` macro from `icons.html`.

| Template | Route | Description |
|---|---|---|
| `base.html` | — | Layout, nav, dark mode, CSRF meta tag, `window.__userTheme`, `window.__userAuthenticated` |
| `documents.html` | `/documents` | Document table with sorting, export/import buttons |
| `viewer.html` | `/viewer/<doc_id>` | Split-screen PDF viewer + annotation textarea |
| `index.html` | `/` | Landing/redirect |
| `error.html` | error handlers | Generic error page |
| `icons.html` | — | Lucide SVG icon macro library: `icons.icon(name, size, stroke_width)` |
| `auth/login.html` | `/auth/login` | Login form |
| `auth/register.html` | `/auth/register` | Registration form |
| `admin/index.html` | `/admin/` | User management table |

## JavaScript

| File | Used on | Responsibilities |
|---|---|---|
| `documents.js` | Documents page | Table sorting, export/import buttons with loading state, PDF replacement, document deletion |
| `viewer.js` | Viewer page | Page navigation, annotation auto-save (sendBeacon on page change/unload), image loading with error handling, keyboard shortcuts |
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
