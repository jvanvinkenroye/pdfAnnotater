# Annotationen

## Notizen erfassen

Im rechten Bereich des Viewers befindet sich ein Textfeld für Notizen. Jede Seite hat ihr eigenes Notizfeld — beim Navigieren wechselt der Inhalt automatisch zur Notiz der aktuellen Seite.

**Notizen können enthalten:**

- Freitext in beliebiger Länge (max. 5.000 Zeichen pro Seite)
- Zeilenumbrüche
- Sonderzeichen und Umlaute

## Auto-Save

Notizen werden **automatisch im Hintergrund gespeichert** — kein manuelles Speichern notwendig.

Auslöser für das Speichern:

- Verlassen des Textfelds (Blur-Event)
- Seitenwechsel
- Schließen des Browsers (via `sendBeacon`)
- Debounced nach 500 ms Inaktivität beim Tippen

Ein kleines Status-Icon zeigt an, ob die letzte Speicherung erfolgreich war.

## Im exportierten PDF

Notizen erscheinen im exportierten PDF:

- **Schriftart:** Courier (Fixed-Width)
- **Farbe:** Grün (`#008000`)
- **Format:** `[YYYY-MM-DD HH:mm] Notiztext`
- **Position:** Unterhalb des Seiteninhalts (als neuer Textblock)

**Beispiel:**

```
[2026-03-01 15:42] Dies ist eine Beispiel-Notiz für Seite 3.
Die Notiz kann mehrere Zeilen umfassen.
```

## Im Markdown-Export

Im Markdown-Export werden alle Notizen mit Seitenreferenz aufgelistet:

```markdown
## Seite 1

[2026-03-01 15:30] Erste Seite enthält die Einleitung.

## Seite 3

[2026-03-01 15:42] Dies ist eine Beispiel-Notiz für Seite 3.
```

Seiten ohne Notiz werden im Markdown-Export nicht aufgeführt.

## Notizen löschen

Eine Notiz löschen: Textfeld leeren und Seite wechseln oder Textfeld verlassen. Der leere Inhalt wird automatisch gespeichert.
