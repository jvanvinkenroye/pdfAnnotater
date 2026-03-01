# PDF Annotator

Eine Flask-basierte Web-Applikation zum seitenweisen Annotieren von PDF-Dokumenten. PDFs werden im Split-Screen angezeigt — links die PDF-Seite, rechts der Notiz-Editor. Notizen werden mit Zeitstempel in grüner Courier-Schrift in das PDF integriert.

## Features auf einen Blick

| Feature | Beschreibung |
|---|---|
| **Split-Screen View** | PDF-Anzeige links, Notizen-Editor rechts |
| **Auto-Save** | Notizen werden automatisch gespeichert (500 ms Debounce) |
| **PDF-Export** | Annotiertes PDF mit grüner Courier-Schrift + Zeitstempel |
| **Markdown-Export** | Alle Notizen als strukturiertes Markdown-Dokument |
| **Multi-User** | Registrierung und Login mit eigenem Dokumenten-Bereich |
| **Admin Panel** | Vollständige Benutzerverwaltung |
| **Themes** | Light, Dark und Brutalist — serverseitig pro Account gespeichert |
| **Zoom** | 50 %–200 % + Breitenanpassung |
| **Import / Export** | ZIP-Backup zum Sichern und Wiederherstellen |

## Schnellstart

=== "Docker (empfohlen)"

    ```bash
    git clone https://github.com/jvanvinkenroye/pdfAnnotater.git
    cd pdfAnnotater
    export SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))")
    docker compose up -d
    ```

    App erreichbar unter: **http://localhost:8000**

=== "uv tool"

    ```bash
    uv tool install git+https://github.com/jvanvinkenroye/pdfAnnotater.git
    pdf-annotator
    ```

=== "Aus Source"

    ```bash
    git clone https://github.com/jvanvinkenroye/pdfAnnotater.git
    cd pdfAnnotater
    uv sync
    uv run flask --app src/pdf_annotator/app:create_app run --port 8000
    ```

## Workflow

```
Registrieren / Einloggen
        ↓
PDF hochladen (max. 50 MB)
        ↓
Seiten durchblättern & Notizen schreiben
        ↓
Auto-Save im Hintergrund
        ↓
PDF exportieren (annotiert) oder Markdown exportieren
```

## Technologie-Stack

- **Backend:** Python 3.10+, Flask 3.0+, Flask-Login, Flask-WTF
- **PDF-Verarbeitung:** PyMuPDF (fitz)
- **Frontend:** HTML5, CSS3, Vanilla JavaScript
- **Datenbank:** SQLite
- **WSGI:** Gunicorn (Produktion)
- **Container:** Docker + Docker Compose
