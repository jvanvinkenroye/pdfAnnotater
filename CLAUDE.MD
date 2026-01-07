# Spezifikation: PDF Side-by-Side Annotator

## 1. Projektübersicht

Eine Web-Applikation auf Flask-Basis, die es Benutzern ermöglicht, PDF-Dokumente hochzuladen, diese seitenweise zu betrachten und pro Seite textuelle Notizen zu erfassen. Die Notizen werden anschließend mit Zeitstempeln in das PDF integriert (grüne Fixed-Width Schrift).

## 2. Technical Stack

* **Backend:** Python 3.x mit **Flask**
* **PDF-Handling:** **PyMuPDF (fitz)** (für Rendering und Injektion von Text)
* **Frontend:** HTML5, CSS3 (Flexbox/Grid), JavaScript (Fetch API für Auto-Save)
* **Code Quality:** * **Ruff** (Linting & Formatting)
* **Black** (optionaler dedizierter Formatter, falls nicht über Ruff abgedeckt)


* **Datenhaltung:** SQLite (temporäre Speicherung der Notizen während der Bearbeitung)

## 3. Funktionale Anforderungen

### 3.1 PDF-Management

* **Upload:** Benutzer lädt eine PDF-Datei hoch.
* **Processing:** Das System zählt die Seiten und bereitet die Ansicht vor.
* **Export:** Generierung einer neuen PDF-Datei, in der die Notizen am Ende jeder Seite oder auf einer dedizierten Fläche eingefügt werden.

### 3.2 View-Modus (Workspace)

* **Split-Screen Layout:**
* **Links (Viewer):** Anzeige der aktuellen PDF-Seite als Bild (für maximale Kompatibilität) oder via `pdf.js`.
* **Rechts (Editor):** Ein großes Textareal für Notizen.


* **Navigation:** Buttons für "Vorherige Seite" und "Nächste Seite". Der Inhalt des Textfelds wechselt synchron zur Seite.
* **Persistence:** Notizen werden beim Verlassen des Textfelds oder beim Seitenwechsel automatisch in der Datenbank gespeichert.

### 3.3 Annotations-Logik (Output)

Beim finalen Speichern/Download gelten folgende Regeln für die Notizen:

* **Schriftart:** Fixed-Width (z.B. Courier).
* **Farbe:** Grün (Hex: `#008000` / RGB: `0, 128, 0`).
* **Metadaten:** Jede Notiz erhält einen Timestamp im Format `[YYYY-MM-DD HH:mm]`.
* **Positionierung:** Die Notizen werden entweder in einem definierten Fußbereich oder auf einer angehängten Notizseite platziert (konfigurierbar).

## 4. Workflow (User Journey)

1. **Start:** User öffnet die App und lädt ein PDF hoch.
2. **Bearbeitung:**
* User sieht Seite 1, schreibt eine Notiz.
* User klickt auf "Weiter", schreibt Notiz für Seite 2.
* Daten werden im Hintergrund via AJAX gespeichert.


3. **Abschluss:** User klickt auf "PDF generieren".
4. **Download:** Das System merged die Original-Seiten mit den formatierten Notizen und bietet das Ergebnis zum Download an. Es soll eine Datei geben, die den Ursprünglichen Dateinamen habe + Anmerkung. Dazu noch die Notitz im Markdown-Format. In der Markdown-Datei soll zu den Anmerkungen notiert werden,
auf welcher Seit die Anmerkung ist. 

## 5. Datenmodell (Beispiel)

```sql
CREATE TABLE annotations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    doc_id TEXT,           -- Eindeutige ID für den Upload
    page_number INTEGER,    -- Seite im PDF
    note_text TEXT,         -- Inhalt der Notiz
    updated_at TIMESTAMP    -- Letzte Änderung für den Export-Zeitstempel
);

```

## 6. Qualitätsanspruch & Entwicklung

* **Linting:** `ruff check .` muss fehlerfrei durchlaufen.
* **Formatting:** `ruff format .` oder `black .` zur Einhaltung der PEP8 Standards.
* **Struktur:** Trennung von Business-Logik (PDF-Generierung) und Routing (Flask-Views).

