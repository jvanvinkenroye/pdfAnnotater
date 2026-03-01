# Tests & Codequalität

## Tests ausführen

```bash
# Alle Tests
uv run pytest tests/ -v

# Mit Coverage-Report
uv run pytest tests/ --cov=src/pdf_annotator --cov-report=term-missing

# Einzelne Testdatei
uv run pytest tests/test_routes.py -v

# Tests mit bestimmtem Namen
uv run pytest tests/ -k "test_upload" -v
```

## Teststruktur

```
tests/
├── conftest.py              # Fixtures (App, DB, Clients, Test-PDFs)
├── test_admin.py            # 21 Admin-Tests
├── test_database.py         # DatabaseManager-Tests
├── test_markdown_exporter.py
├── test_pdf_generator.py
├── test_pdf_processor.py
├── test_routes.py           # Route- & API-Tests
└── test_validators.py       # Validierungs-Tests
```

Gesamt: **114 Tests**

## Wichtige Fixtures (conftest.py)

| Fixture | Beschreibung |
|---|---|
| `app` | Flask-Test-App mit In-Memory-DB |
| `client` | Nicht-authentifizierter Test-Client |
| `admin_client` | Test-Client als Admin eingeloggt |
| `user_client` | Test-Client als normaler User eingeloggt |
| `db` | DatabaseManager-Instanz |
| `sample_pdf` | Minimale Test-PDF (Path) |
| `uploaded_pdf` | PDF bereits in der DB hochgeladen |

!!! warning "Fixture-Hinweis"
    Fixtures verwenden immer den `db`-Parameter statt `DatabaseManager()` direkt aufzurufen — der Singleton würde sonst eine falsche Instanz zurückgeben.

## Linting

```bash
# Linting prüfen
uv run ruff check src/ tests/

# Auto-Fix (sichere Korrekturen)
uv run ruff check --fix src/ tests/
```

## Formatierung

```bash
# Formatierung prüfen
uv run ruff format --check src/ tests/

# Formatierung anwenden
uv run ruff format src/ tests/
```

## Type Checking

```bash
uv run mypy src/
```

## CI-Checks lokal ausführen

```bash
uv run ruff check src/ tests/ && \
uv run ruff format --check src/ tests/ && \
uv run pytest tests/ -q
```

Alle drei müssen fehlerfrei sein, bevor ein Commit gemacht wird.

## Ruff-Konfiguration

Konfigurationsdatei: `ruff.toml`

Relevante Einstellungen:

```toml
line-length = 88
target-version = "py310"
```

## Test-Konfiguration

In `pyproject.toml`:

```toml
[tool.pytest.ini_options]
filterwarnings = [
    "ignore::DeprecationWarning:importlib._bootstrap",
    "ignore::DeprecationWarning:sqlite3",
]
```
