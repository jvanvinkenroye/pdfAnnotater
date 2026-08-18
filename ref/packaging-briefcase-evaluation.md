# BeeWare Briefcase/Toga — Packaging-Evaluierung (zurückgestellt)

Status: **Evaluiert, aber nicht weiterverfolgt.** Aktueller Desktop-Client bleibt
`flaskwebgui` (`src/pdf_annotator/desktop.py`). Dieses Dokument hält die
Ergebnisse fest, falls die Idee später wieder aufgegriffen wird.

## Ausgangsfrage

Könnte [BeeWare Briefcase](https://github.com/beeware/briefcase) die aktuelle
Desktop-Paketierung (Homebrew-Formel + `.deb`-Skript + `uv tool install`)
durch einen einheitlichen Cross-Platform-Installer ersetzen? Ansatz: Toga-App
mit `toga.WebView`, die die echte Flask-App im Hintergrund-Thread hostet
(gleiches Prinzip wie `flaskwebgui`, nur mit WKWebView statt echtem Chrome).

## Ergebnisse

### Datei-Upload: funktioniert einwandfrei
`<input type="file">` öffnet den nativen macOS-Dateiauswahldialog, `fetch()` +
`FormData` funktioniert unverändert — kein Unterschied zum echten Browser.

### Datei-Download: brauchte einen Workaround
WKWebView (Toga's macOS-Backend) kann `Content-Disposition: attachment`
nicht selbst verarbeiten — dafür bräuchte die Host-App eine eigene
`URLSession`-Download-Delegate-Implementierung, die Toga's `WebView`-Widget
nicht bereitstellt. Symptom: Server-Request kommt an (`200`), Verbindung wird
aber mittendrin abgebrochen (`ResourceWarning: unclosed file`,
`connection_dropped`).

**Gewählte Lösung (umgesetzt, siehe unten):** `DESKTOP_MODE`-Flag — der Server
schreibt Exports direkt nach `~/Downloads` statt sie per HTTP auszuliefern,
und die JS-Seite zeigt nur einen Toast mit dem Pfad. Umgeht das Problem
komplett, statt es im WebView zu reparieren.

### Weitere Toga-Einschränkungen (Stand der Recherche)
- `on_navigation_starting` (Navigation abfangen) auf GTK/Qt **nicht unterstützt**
- `cookies`-Property auf Android/Linux **nicht unterstützt**
- JS→Python-Callback existiert grundsätzlich nicht ([Issue #2268](https://github.com/beeware/toga/issues/2268))
- GTK-Backend nutzt noch die deprecated `run_javascript()`-API ([Issue #2085](https://github.com/beeware/toga/issues/2085))

### Login/Auth: offene Frage, nicht umgesetzt
Für ein lokales Single-User-Desktop-Tool ist der volle Multi-User-Login
(Flask-Login, Registrierung) unnötige Reibung — im Test musste extra ein
Passwort zurückgesetzt werden, nur um die eigene lokale App zu benutzen.

**Idee (nicht umgesetzt):** Im Desktop-Mode automatisch als fester
Local-User einloggen (analog zu `DESKTOP_MODE`), Login-Screen überspringen.
Server-Betrieb (brujah, mehrere Nutzer) bliebe mit echtem Login unverändert.
Falls Briefcase wieder aufgegriffen wird, ist das der erste offene Punkt.

## Bereits umgesetzt und im Hauptzweig (unabhängig von der Migrations-Entscheidung nützlich)

Der `DESKTOP_MODE`-Fix wurde committed, da er generisch für jede
WebView-basierte Desktop-Lösung nötig wäre und den bestehenden
`flaskwebgui`-Client/Server-Betrieb nicht berührt (Flag default `False`):

- `get_downloads_dir()`, `DESKTOP_MODE`, `DESKTOP_EXPORT_DIR` — `src/pdf_annotator/config.py`
- `send_file_response()` Helper — `src/pdf_annotator/utils/downloads.py`
- Verzweigung in allen 4 Export-Routen — `routes/export.py`, `routes/upload.py`
- `window.__desktopMode` Flag + JSON-Toast statt Blob-Download — `templates/base.html`, `static/js/documents.js`

Siehe [`ref/development.md`](development.md) Gotchas-Abschnitt für den
Sicherheitshinweis (`DESKTOP_MODE` niemals auf Server/Docker aktivieren).

## Wiederaufnahme (Branch `feature/toga-desktop`, 2026-08-19)

Der Prototyp lebt jetzt **im Repo** statt im Wegwerf-Scratchpad:

- **`src/pdf_annotator/desktop_toga.py`** — Toga-Entry-Point: Flask im
  Daemon-Thread auf freiem Port, `toga.WebView` als Fenster-Content.
  Start: `uv run pdf-annotator-toga` (Script-Entry in pyproject).
- **Toga als optionale Dependency**: `uv sync --extra toga`
  (`[project.optional-dependencies] toga`).
- **Auto-Login umgesetzt** (der frühere offene Punkt #1):
  `PDF_ANNOTATOR_DESKTOP_AUTO_LOGIN=1` → `DESKTOP_AUTO_LOGIN`-Config-Flag →
  `before_request`-Hook in `app.py` loggt automatisch einen lokalen
  `desktop`-User ein (wird beim ersten Request mit Zufallspasswort +
  Admin-Rechten angelegt). Niemals auf Servern aktivieren. 3 Tests in
  `tests/test_auth.py` (`TestDesktopAutoLogin`).
- Der Entry-Point setzt `DESKTOP_MODE=1` (Export → ~/Downloads) und
  `DESKTOP_AUTO_LOGIN=1` automatisch.

**Verifiziert am 2026-08-19:** App startet, natives Fenster öffnet sich,
`GET /` liefert direkt 200 (kein Login-Redirect), desktop-User wird genau
einmal angelegt, WKWebView lädt statische Assets.

## Was für eine Produktiv-Entscheidung noch fehlt

- Kompletter Annotations-Workflow im WebView testen (Speichern via
  `sendBeacon`, Seiten löschen/anhängen, Keyboard-Shortcuts, Zoom,
  Text-Layer-Selektion, OCR-Button)
- Cookie-/Session-Persistenz über App-Neustarts hinweg (durch Auto-Login
  praktisch entschärft — Session-Verlust heißt nur transparentes Neu-Einloggen)
- Tatsächlicher Briefcase-Build (`briefcase build`/`briefcase package`) —
  Icon, Bundle-Signing, Notarization auf macOS; `[tool.briefcase]`-Konfig
  in pyproject.toml fehlt noch
- Entscheidung: ersetzt das flaskwebgui (`desktop.py`) oder bleibt es
  parallel als Option?
