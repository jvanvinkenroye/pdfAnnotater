# Viewer & Navigation

## Layout

Der Viewer ist in zwei Bereiche aufgeteilt:

```
┌─────────────────────────┬──────────────────────────┐
│                         │                          │
│      PDF-Anzeige        │     Notiz-Editor         │
│         (links)         │      (rechts)            │
│                         │                          │
│    Seite X von Y        │  [ Notiztext eingeben ]  │
│                         │                          │
└─────────────────────────┴──────────────────────────┘
│  ← Zurück   Seite: [__]   Weiter →   Zoom: [___]  │
└───────────────────────────────────────────────────┘
```

## Seitennavigation

### Buttons

| Button | Funktion |
|---|---|
| **← Zurück** | Vorherige Seite |
| **Weiter →** | Nächste Seite |
| **Seite: [N]** | Direkte Eingabe der Seitennummer + Enter |

### Tastatur-Shortcuts

| Shortcut | Funktion |
|---|---|
| `Ctrl` / `Cmd` + `←` oder `↑` | Vorherige Seite |
| `Ctrl` / `Cmd` + `→` oder `↓` | Nächste Seite |
| `Ctrl` / `Cmd` + `Home` | Erste Seite |
| `Ctrl` / `Cmd` + `End` | Letzte Seite |
| `Ctrl` / `Cmd` + `G` | Zu Seite springen (Eingabedialog) |
| `Ctrl` / `Cmd` + `Del` / `Backspace` | Aktuelle Seite löschen |

!!! tip "Shortcuts im Textfeld"
    Die Shortcuts funktionieren auch während der Texteingabe im Notiz-Editor — außer wenn der Cursor im Seitennummer-Eingabefeld steht.

## Zoom

Der Zoom-Schieberegler in der Toolbar erlaubt Werte von **50 % bis 200 %**.

Zusätzlich gibt es den Button **"Breite anpassen"**, der die PDF-Seite auf die verfügbare Fensterbreite skaliert.

## Seite löschen

Eine einzelne Seite kann aus dem PDF entfernt werden:

1. Zur gewünschten Seite navigieren
2. Button **"Seite löschen"** klicken (oder `Ctrl+Del`)
3. Bestätigung im Dialog

Nach dem Löschen werden die Annotationen aller folgenden Seiten automatisch neu nummeriert.

!!! warning "Letzte Seite"
    Die letzte verbleibende Seite eines Dokuments kann nicht gelöscht werden.

## Metadaten bearbeiten

Im Viewer gibt es einen Bereich zum Bearbeiten der Dokumentmetadaten (Vorname, Nachname, Titel, Jahr, Thema). Änderungen werden beim Verlassen des Feldes automatisch gespeichert.
