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

## Was für eine erneute Evaluierung noch fehlt

- Auto-Login für Desktop-Mode (siehe oben)
- Kompletter Annotations-Workflow im WebView testen (Speichern via
  `sendBeacon`, Seiten löschen/anhängen, Keyboard-Shortcuts, Zoom)
- Cookie-/Session-Persistenz über App-Neustarts hinweg
- Tatsächlicher Briefcase-Build (`briefcase build`/`briefcase package`) statt
  nur `briefcase dev` — Icon, Bundle-Signing, Notarization auf macOS
- Vergleich des tatsächlichen Aufwands (Toga-App-Wrapper + Build-Konfiguration)
  gegenüber dem Ertrag (ein Build-Tool statt Homebrew-Formel + `.deb`-Skript)

## Prototyp

Der Test-Prototyp lag unter einem Session-Scratchpad-Verzeichnis (temporär,
nicht Teil des Repos). Bei Bedarf neu aufsetzen mit:
```bash
uvx briefcase new --no-input -Q formal_name="..." -Q app_name=... -Q bundle=... \
  -Q gui_framework=Toga -Q license=BSD-3-Clause ...
```
Danach `app.py` so anpassen, dass `pdf_annotator.app.create_app("production")`
in einem Hintergrund-Thread läuft und `toga.WebView` auf `127.0.0.1:<port>`
zeigt (siehe Commit-Historie für den vollständigen Code-Stand, falls dieser
Prototyp erneut gebraucht wird).
