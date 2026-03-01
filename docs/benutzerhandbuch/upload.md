# PDF hochladen

## Upload-Dialog

Auf der Dokumentenliste (`/documents`) gibt es den Button **"PDF hochladen"**. Alternativ kann die Datei per **Drag & Drop** auf den Upload-Bereich gezogen werden.

**Anforderungen:**

- Dateiformat: PDF (`.pdf`)
- Maximale Dateigröße: **50 MB**
- Die Datei muss ein gültiges, nicht beschädigtes PDF sein

## Metadaten

Beim Upload können optionale Metadaten zum Dokument eingegeben werden:

| Feld | Beschreibung |
|---|---|
| **Vorname** | Name des Autors / Bearbeiters |
| **Nachname** | Nachname des Autors / Bearbeiters |
| **Titel** | Titel des Dokuments |
| **Jahr** | Erscheinungsjahr |
| **Thema** | Themenbereich oder Kategorie |

Metadaten können jederzeit im Viewer nachträglich bearbeitet werden.

## Dokumentenliste

Nach dem Upload erscheint das Dokument in der Dokumentenliste. Dort sind sichtbar:

- Originaldateiname
- Seitenanzahl
- Upload-Zeitstempel
- Metadaten (Vorname, Nachname, Titel, Jahr, Thema)
- Buttons: Öffnen, Löschen, Export

## PDF ersetzen

Im Viewer kann das PDF-Dokument durch eine neue Version ersetzt werden, **ohne bestehende Annotationen zu verlieren**:

1. Viewer öffnen → Button **"PDF ersetzen"**
2. Neue PDF-Datei auswählen
3. Bestätigen

!!! warning "Seitenanzahl beachten"
    Wenn das neue PDF weniger Seiten hat als das alte, werden Annotationen für die nicht mehr vorhandenen Seiten zwar in der Datenbank behalten, aber nicht mehr angezeigt.

## Seiten anhängen

Zusätzliche Seiten aus einer anderen PDF-Datei können an das bestehende Dokument angehängt werden:

1. Viewer öffnen → Button **"Seiten anhängen"**
2. PDF-Datei mit den anzuhängenden Seiten auswählen
3. Bestätigen

## Dokument löschen

Aus der Dokumentenliste oder dem Viewer heraus. Das Löschen entfernt:

- Die hochgeladene PDF-Datei
- Alle zugehörigen Annotationen
- Den Datenbankeintrag

!!! danger "Unwiderruflich"
    Das Löschen eines Dokuments kann nicht rückgängig gemacht werden. Vorher ein Backup erstellen.
