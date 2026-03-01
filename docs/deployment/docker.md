# Docker Deployment

## Voraussetzungen

- Docker 24+
- Docker Compose v2+

## Schnellstart

```bash
git clone https://github.com/jvanvinkenroye/pdfAnnotater.git
cd pdfAnnotater

# .env mit zufälligem SECRET_KEY anlegen
python3 -c "import secrets; print('SECRET_KEY=' + secrets.token_hex(32))" > .env

docker compose up -d
```

App erreichbar unter: **http://localhost:8000**

## Konfiguration

Umgebungsvariablen in `.env` oder als Shell-Variablen:

| Variable | Pflicht | Standard | Beschreibung |
|---|---|---|---|
| `SECRET_KEY` | **Ja** | — | Flask-Session-Schlüssel (min. 32 zufällige Bytes) |
| `GUNICORN_WORKERS` | Nein | `2` | Anzahl Gunicorn-Worker |

**Empfohlene Worker-Anzahl:** `2 * CPU-Kerne + 1`

```bash
# Beispiel für 4 CPU-Kerne
GUNICORN_WORKERS=9
```

## Datenpersistenz

Alle Daten werden in einem Docker-Volume gespeichert:

```
pdf_annotator_data → /data/PDF-Annotator/ (im Container)
```

Das Volume überlebt Container-Neustarts und `-updates`. Darin enthalten:

- `annotations.db` — SQLite-Datenbank
- `uploads/` — hochgeladene PDFs
- `exports/` — generierte Exporte
- `app.log` — Anwendungslog

## Nützliche Befehle

```bash
# Status prüfen
docker compose ps

# Logs live verfolgen
docker compose logs -f

# Container neu starten
docker compose restart

# Stoppen (Volume bleibt erhalten)
docker compose down

# Stoppen + Volume löschen (alle Daten weg!)
docker compose down -v
```

## Image neu bauen

Nach Code-Änderungen:

```bash
docker compose up --build -d
```

## Daten sichern

```bash
# Volume-Inhalt in lokales Verzeichnis kopieren
docker run --rm \
  -v pdfannotater_pdf_annotator_data:/data \
  -v $(pwd)/backup:/backup \
  alpine tar czf /backup/pdf_annotator_backup.tar.gz -C /data .
```

## Daten wiederherstellen

```bash
docker run --rm \
  -v pdfannotater_pdf_annotator_data:/data \
  -v $(pwd)/backup:/backup \
  alpine tar xzf /backup/pdf_annotator_backup.tar.gz -C /data
```

## Daten zurücksetzen

```bash
docker compose down
docker volume rm pdfannotater_pdf_annotator_data
docker compose up -d
```
