# Export

## Annotiertes PDF

Erstellt eine neue PDF-Datei, in der die Notizen direkt in das Original-PDF integriert sind.

**Dateiname:** `<Originaldateiname>_annotiert.pdf`

**Format der Notizen:**

- Schriftart: Courier (Fixed-Width)
- Farbe: Grün
- Zeitstempel: `[YYYY-MM-DD HH:mm]`
- Position: Am Ende jeder annotierten Seite

**Starten:** Im Viewer → Button **"PDF generieren"** → Download startet automatisch.

!!! note "Nur annotierte Seiten"
    Seiten ohne Notizen bleiben im exportierten PDF unverändert.

---

## Markdown-Export

Exportiert alle Notizen des Dokuments als strukturierte Markdown-Datei.

**Dateiname:** `<Originaldateiname>_notizen.md`

**Struktur:**

```markdown
# Notizen: Dokumenttitel

**Autor:** Vorname Nachname
**Jahr:** 2026
**Thema:** Kategorie

---

## Seite 1

[2026-03-01 15:30] Text der Notiz auf Seite 1.

## Seite 5

[2026-03-01 15:45] Text der Notiz auf Seite 5.
```

**Starten:** Im Viewer → Button **"Markdown exportieren"** → Download startet automatisch.

---

## Original-PDF herunterladen

Das ursprünglich hochgeladene PDF ohne Annotationen kann jederzeit heruntergeladen werden.

**Starten:** Dokumentenliste → Button **"Original herunterladen"**.

---

## Backup (ZIP)

Exportiert alle eigenen Dokumente inklusive Annotationen als ZIP-Archiv. Dient zur Datensicherung und zum Übertragen auf eine andere Instanz.

**Inhalt des ZIP:**

```
backup.zip
├── documents.json      # Metadaten aller Dokumente
├── annotations.json    # Alle Annotationen
└── files/
    ├── uuid1.pdf
    └── uuid2.pdf
```

**Exportieren:** Dokumentenliste → Button **"Backup exportieren"**

**Importieren:** Dokumentenliste → Button **"Backup importieren"** → ZIP-Datei auswählen

!!! tip "Mehrfach-Import möglich"
    Beim Import werden neue UUIDs generiert — das gleiche Backup kann von mehreren Benutzern unabhängig importiert werden.
