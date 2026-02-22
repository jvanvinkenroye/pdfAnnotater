# PDF Side-by-Side Annotator

Eine Flask-basierte Web-Applikation zum Annotieren von PDF-Dokumenten mit Side-by-Side-View. Zeigt PDFs seitenweise an und ermöglicht es, pro Seite Notizen zu erfassen, die dann mit Zeitstempeln in grüner Courier-Schrift in das PDF integriert werden.

## Features

- **Split-Screen View:** PDF-Anzeige links, Notizen-Editor rechts
- **Seitenweise Navigation:** Vor/Zurueck-Buttons, Seiteneingabe und Tastatur-Shortcuts
- **Seite loeschen:** Einzelne Seiten aus dem PDF entfernen (z.B. leere Seiten, falsche Scans)
- **PDF ersetzen:** PDF-Datei austauschen, alle Notizen bleiben erhalten
- **Auto-Save:** Notizen werden automatisch gespeichert (debounced, 500ms)
- **Metadaten:** Vorname, Nachname, Titel, Jahr, Thema pro Dokument
- **Export-Funktionen:**
  - **Annotiertes PDF:** Original-PDF mit Notizen in gruener Courier-Schrift + Zeitstempel
  - **Markdown-Export:** Alle Notizen als strukturiertes Markdown-Dokument
- **Zoom:** Stufenweises Zoomen (50%-200%) und Breitenanpassung
- **Dark Mode:** Automatische Erkennung der System-Einstellung
- **Dokument-Verwaltung:** Liste aller Dokumente mit Loeschfunktion
- **Single-User:** Lokale Applikation ohne Session-Management
- **Persistente Speicherung:** Dokumente bleiben bis zur manuellen Loeschung erhalten
- **Max. 50 MB:** Upload-Limit fuer PDF-Dateien

## Screenshots

### Upload-Seite
Drag & Drop oder Datei-Auswahl für PDF-Upload mit Client-seitiger Validierung.

### Viewer
Split-Screen mit PDF-Rendering links und Notizen-Editor rechts. Auto-Save und Keyboard-Navigation.

## Installation

### Voraussetzungen

- Python 3.10 oder höher
- macOS oder Linux

### Homebrew (macOS, empfohlen)

```bash
brew tap jvanvinkenroye/pdf-annotator
brew install pdf-annotator
```

Nach der Installation: `pdf-annotator` im Terminal eingeben.

### uv tool (plattformuebergreifend)

```bash
uv tool install git+https://github.com/jvanvinkenroye/pdfAnnotater.git
```

### Manuelle Installation (Entwickler)

```bash
# Repository klonen
cd /path/to/pdfAnnotater

# Virtual Environment erstellen
uv venv --seed
source .venv/bin/activate

# Dependencies installieren
uv pip install -e .

# Dev-Dependencies installieren (optional)
uv pip install -e ".[dev]"
```

### Manuelle Installation (aus Source)

```bash
git clone https://github.com/jvanvinkenroye/pdfAnnotater.git
cd pdfAnnotater
uv venv --seed && source .venv/bin/activate
uv pip install -e .
```

## Verwendung

### Desktop-App starten

Nach der Installation einfach im Terminal:

```bash
pdf-annotator
```

Die App startet in einem eigenen Fenster (1400x900 Pixel) ohne Browser-Chrome.

### Datenspeicherung

Die App speichert alle Daten platform-konform:

| Plattform | Speicherort |
|-----------|-------------|
| **macOS** | `~/Library/Application Support/PDF-Annotator/` |
| **Linux** | `~/.local/share/pdf-annotator/` |

Unterordner:
- `uploads/` - Hochgeladene PDF-Dateien
- `exports/` - Generierte annotierte PDFs
- `annotations.db` - Datenbank mit Notizen

### Entwicklungsmodus

Für Entwicklung (Daten im Projektordner):

```bash
source .venv/bin/activate
FLASK_ENV=development python run_desktop.py

# Oder als Web-Server:
python src/pdf_annotator/app.py
```

### Workflow

1. **PDF hochladen:** Öffne `http://127.0.0.1:5000` und lade eine PDF-Datei hoch (max. 50 MB)
2. **Notizen hinzufügen:** Navigiere durch die Seiten und füge Notizen im rechten Editor hinzu
3. **Auto-Save:** Notizen werden automatisch gespeichert beim Tippen oder Seitenwechsel
4. **Exportieren:**
   - **PDF generieren:** Erstellt annotiertes PDF mit Notizen in grüner Courier-Schrift + Zeitstempel
   - **Markdown exportieren:** Erstellt Markdown-Datei mit allen Notizen

### Tastatur-Shortcuts

Alle Shortcuts erfordern **Ctrl** (Windows/Linux) bzw. **Cmd** (Mac):

| Shortcut | Funktion |
|---|---|
| Ctrl/Cmd + Links/Hoch | Vorherige Seite |
| Ctrl/Cmd + Rechts/Runter | Naechste Seite |
| Ctrl/Cmd + Home | Erste Seite |
| Ctrl/Cmd + End | Letzte Seite |
| Ctrl/Cmd + G | Zu Seite springen |
| Ctrl/Cmd + Delete/Backspace | Seite loeschen |

## Projektstruktur

```
pdfAnnotater/
├── run_desktop.py              # Desktop-App Launcher
├── src/pdf_annotator/
│   ├── app.py                  # Flask Entry Point
│   ├── desktop.py              # Desktop-App Wrapper (flaskwebgui)
│   ├── config.py               # Konfiguration (Dev/Prod/Test)
│   │
│   ├── models/
│   │   └── database.py         # SQLite Schema & CRUD
│   │
│   ├── services/
│   │   ├── pdf_processor.py    # PDF → PNG Rendering
│   │   ├── pdf_generator.py    # Annotiertes PDF erstellen
│   │   └── markdown_exporter.py # Markdown-Export
│   │
│   ├── routes/
│   │   ├── upload.py           # PDF-Upload
│   │   ├── viewer.py           # Viewer & API
│   │   └── export.py           # PDF/Markdown-Download
│   │
│   ├── utils/
│   │   ├── validators.py       # Input-Validierung
│   │   └── logger.py           # Logging-Setup
│   │
│   ├── static/
│   │   ├── css/styles.css
│   │   └── js/{upload,viewer}.js
│   │
│   └── templates/
│       ├── base.html
│       ├── index.html          # Upload-Seite
│       ├── viewer.html         # Viewer
│       └── error.html
│
├── data/                       # Runtime (nicht in Git)
│   ├── uploads/                # Hochgeladene PDFs
│   ├── exports/                # Generierte PDFs
│   └── annotations.db          # SQLite-DB
│
├── tests/                      # Pytest Tests
├── pyproject.toml              # Projekt-Config
└── ruff.toml                   # Linting-Config
```

## Datenbank-Schema

```sql
-- Dokumente
CREATE TABLE documents (
    id TEXT PRIMARY KEY,                    -- UUID4
    original_filename TEXT NOT NULL,
    file_path TEXT NOT NULL,
    page_count INTEGER NOT NULL,
    first_name TEXT DEFAULT '',
    last_name TEXT DEFAULT '',
    title TEXT DEFAULT '',
    year TEXT DEFAULT '',
    subject TEXT DEFAULT '',
    upload_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Notizen
CREATE TABLE annotations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    doc_id TEXT NOT NULL,
    page_number INTEGER NOT NULL,
    note_text TEXT DEFAULT '',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (doc_id) REFERENCES documents(id) ON DELETE CASCADE,
    UNIQUE(doc_id, page_number)
);
```

## API-Endpunkte

### Upload
- `POST /upload` - PDF-Upload mit Validierung

### Viewer
- `GET /viewer/<doc_id>` - Viewer-Seite laden
- `GET /viewer/api/page/<doc_id>/<page>` - PDF-Seite als PNG
- `DELETE /viewer/api/page/<doc_id>/<page>` - Seite aus PDF loeschen
- `GET /viewer/api/annotation/<doc_id>/<page>` - Notiz laden
- `POST /viewer/api/annotation/<doc_id>/<page>` - Notiz speichern
- `POST /viewer/api/metadata/<doc_id>` - Metadaten aktualisieren
- `POST /viewer/api/replace/<doc_id>` - PDF ersetzen

### Dokumente
- `GET /documents` - Dokumentenliste
- `DELETE /delete/<doc_id>` - Dokument loeschen

### Export
- `POST /export/pdf/<doc_id>` - Annotiertes PDF herunterladen
- `POST /export/markdown/<doc_id>` - Markdown-Datei herunterladen
- `GET /export/original/<doc_id>` - Original-PDF herunterladen

## Entwicklung

### Code-Qualität prüfen

```bash
# Linting
ruff check src/

# Automatische Fixes
ruff check --fix src/

# Formatierung
ruff format src/
```

### Tests ausführen

```bash
pytest tests/
```

### Type-Checking

```bash
mypy src/
```

## Konfiguration

Die Applikation kann über Umgebungsvariablen konfiguriert werden:

- `FLASK_ENV`: `development`, `production`, oder `testing` (Standard: `development`)
- `SECRET_KEY`: Flask Secret Key (in Produktion setzen!)

Weitere Konfigurationsoptionen in `src/pdf_annotator/config.py`:

- `MAX_CONTENT_LENGTH`: Max. Upload-Größe (Standard: 50 MB)
- `PDF_RENDER_DPI`: DPI für PDF-Rendering (Standard: 300)
- `PDF_ANNOTATION_FONTSIZE`: Schriftgröße für Notizen (Standard: 9)
- `PDF_ANNOTATION_COLOR`: Farbe für Notizen (Standard: Grün `(0, 0.5, 0)`)

## Technologie-Stack

- **Backend:** Python 3.10+ mit Flask 3.0+
- **Desktop-Wrapper:** flaskwebgui (natives Fenster ohne Browser-Chrome)
- **PDF-Handling:** PyMuPDF (fitz) 1.23+ für Rendering und Text-Injektion
- **Frontend:** HTML5, CSS3 (Flexbox), Vanilla JavaScript (Fetch API)
- **Datenbank:** SQLite (persistente Speicherung)
- **Code Quality:** Ruff (Linting & Formatting), MyPy (Type Checking)

## Lizenz

Dieses Projekt wurde als Lernprojekt erstellt.

## Bekannte Limitierungen

- **Single-User:** Keine Multi-User-Unterstützung oder Session-Management
- **Lokale Speicherung:** Alle Daten werden lokal gespeichert
- **PDF-Rendering:** Sehr große PDFs (100+ Seiten) können Performance-Einbußen haben
- **Text-Positionierung:** Notizen werden im Footer-Bereich (80px) platziert und können bei sehr langen Notizen überlappen

## Zukuenftige Erweiterungen

- Highlighting direkt im PDF
- Volltext-Suche in Notizen
- Export als DOCX/HTML

## Troubleshooting

### Fehler beim PDF-Upload

- Prüfe, dass die Datei ein gültiges PDF ist (nicht beschädigt)
- Prüfe die Dateigröße (max. 50 MB)
- Prüfe die Logs in `data/app.log`

### Fehler beim Rendering

- PyMuPDF erfordert bestimmte System-Libraries
- Bei macOS: `brew install mupdf`
- Bei Ubuntu: `apt-get install mupdf-tools`

### Datenbank-Fehler

- Prüfe, dass `data/` Ordner existiert und beschreibbar ist
- Lösche `data/annotations.db` für einen Neustart

## Kontakt & Support

Bei Fragen oder Problemen:
- Siehe Logs in `data/app.log`
- Prüfe die [CLAUDE.md](CLAUDE.md) für technische Spezifikationen
