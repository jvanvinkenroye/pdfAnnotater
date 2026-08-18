# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.3.0] - 2026-08-19

### Added
- In-app OCR for scanned documents: pages without extractable text show a hint banner plus an "OCR" toolbar button that adds a searchable text layer via ocrmypdf/tesseract (`--skip-text`, deu+eng); tesseract + language packs + ghostscript included in the Docker image
- Split-view switcher in the viewer toolbar: PDF focus / balanced / notes focus (3:1, 1:1, 1:3), persisted in localStorage
- Compact theme (fourth theme in the toggle rotation): light colors with minimal chrome — slim header/toolbar, footer and editor hints hidden, viewer stretched to nearly full viewport height
- Styled 403 error page (was werkzeug's bare "Forbidden" page)

### Changed
- Homebrew distribution deprecated: formula was stuck at v0.4.1 and the CI tap-update had been failing silently; `uv tool install` is the recommended install path (tap carries `deprecate!` + migration notes)
- Viewer fit-to-width now actually fits the width: portrait pages fill the panel and scroll vertically instead of shrinking to a strip with dead space
- Documents table no longer overflows the viewport (reduced min-width, action buttons wrap into two rows)
- Nav links "Meine Dokumente" / "Neues PDF" restored in the viewer (previously replaced entirely by the document title)
- Gunicorn timeout configurable via `GUNICORN_TIMEOUT` (default raised to 600s to cover synchronous OCR runs)

### Fixed
- Long/multi-line annotations were silently dropped from the annotated-PDF export: `insert_textbox()` draws nothing on overflow and its return value was never checked — the footer now grows / font shrinks until the text fits (reported as "page 1 always loses its annotation")
- Drag-selection on real PDFs selected wrong text: text-layer spans were emitted in PDF content-stream order (e.g. footer first) but browser selection follows DOM order — lines are now sorted by visual position
- Text overlay was mirrored to the wrong corner on scanned/OCRed pages with a `/Rotate` flag: word boxes are now mapped through the page's rotation matrix into rendered space
- Stale empty text layer shown for up to 5 minutes right after running OCR (browser cache) — post-OCR reload now busts the cache
- Docker build broke with the `swb` local-path dependency: switched to a git dependency and installed git in the builder stage

## [0.2.0] - 2026-07-18

### Added
- Selectable/copyable text overlay on PDF pages (`#pdf-text-layer`), built from PyMuPDF word-level bounding boxes
- Optional AI-assisted note editing ("✨ KI"): edit selected note text with a free-form instruction, or generate note text from bullet points. Supports Anthropic, OpenAI, or any OpenAI-compatible endpoint (`OPENAI_BASE_URL`), disabled unless `AI_PROVIDER` is configured
- "✨ KI aus PDF" button: use text selected in the PDF viewer as context for the AI assistant, result inserted into the note field
- "🔎 SWB-Suche" button: look up text selected in the PDF viewer in German library union catalogs (K10plus) and view results in a new tab
- Self-service "Passwort ändern" page
- `.env` auto-loading via `python-dotenv`, from both the project root and the platform-specific data directory (so the installed `uv tool` picks it up regardless of launch directory)

### Changed
- `requires-python` raised from `>=3.10` to `>=3.12` (required by the new `swb` dependency)

### Fixed
- SWB library search now queries the broader K10plus union catalog instead of the package's regional-only default profile, which was missing books held outside Baden-Württemberg/Saarland/Sachsen
