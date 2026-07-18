# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
