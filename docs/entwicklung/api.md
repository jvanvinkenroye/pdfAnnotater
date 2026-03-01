# API-Referenz

Alle Endpunkte erfordern eine aktive Login-Session (außer `/auth/login` und `/auth/register`).

## Auth

### POST /auth/login
Benutzer einloggen.

**Body (form):** `username`, `password`, `csrf_token`

**Response:** Redirect auf `/documents` (Erfolg) oder Login-Seite mit Fehler.

---

### POST /auth/register
Neuen Benutzer registrieren.

**Body (form):** `username`, `email`, `password`, `csrf_token`

**Response:** Redirect auf `/auth/login` (Erfolg) oder Fehler.

---

### GET /auth/logout
Benutzer ausloggen. Redirect auf Login-Seite.

---

### POST /auth/theme
Theme-Präferenz serverseitig speichern. Rate Limit: 30/min.

**Body (JSON):** `{"theme": "light" | "dark" | "brutalist"}`

**Response:**
```json
{"success": true, "theme": "dark"}
```

---

## Dokumente

### GET /documents
Dokumentenliste des eingeloggten Benutzers. Gibt HTML-Seite zurück.

---

### POST /upload
PDF hochladen.

**Body (multipart):** `file` (PDF), optional: `first_name`, `last_name`, `title`, `year`, `subject`

**Response (JSON):**
```json
{"success": true, "doc_id": "uuid", "page_count": 42}
```

---

### DELETE /delete/\<doc_id\>
Dokument löschen.

**Response (JSON):**
```json
{"success": true}
```

---

### GET /export/backup
Alle Dokumente des Benutzers als ZIP herunterladen.

**Response:** `application/zip`

---

### POST /import
ZIP-Backup importieren.

**Body (multipart):** `file` (ZIP)

**Response (JSON):**
```json
{"success": true, "message": "5 Dokumente importiert", "imported": 5}
```

---

## Viewer

### GET /viewer/\<doc_id\>
Viewer-Seite für ein Dokument. Gibt HTML-Seite zurück.

---

### GET /viewer/api/page/\<doc_id\>/\<page_number\>
PDF-Seite als PNG-Bild rendern.

**Query-Parameter:** `zoom` (50–200, Standard: 100)

**Response:** `image/png`

---

### GET /viewer/api/annotation/\<doc_id\>/\<page_number\>
Notiz einer Seite laden.

**Response (JSON):**
```json
{
  "note_text": "Notizinhalt",
  "updated_at": "2026-03-01T15:42:00"
}
```

---

### POST /viewer/api/annotation/\<doc_id\>/\<page_number\>
Notiz speichern (kein CSRF — für `sendBeacon` kompatibel).

**Body (JSON):** `{"note_text": "..."}`

**Response (JSON):**
```json
{"success": true}
```

---

### DELETE /viewer/api/page/\<doc_id\>/\<page_number\>
Seite aus dem PDF löschen.

**Response (JSON):**
```json
{"success": true, "page_count": 41}
```

---

### POST /viewer/api/metadata/\<doc_id\>
Dokumentmetadaten aktualisieren.

**Body (JSON):** `{"first_name": "", "last_name": "", "title": "", "year": "", "subject": ""}`

**Response (JSON):**
```json
{"success": true}
```

---

### POST /viewer/api/replace/\<doc_id\>
PDF-Datei ersetzen (Annotationen bleiben erhalten).

**Body (multipart):** `file` (PDF)

**Response (JSON):**
```json
{"success": true, "page_count": 38}
```

---

### POST /viewer/api/append/\<doc_id\>
Seiten aus einer anderen PDF anhängen.

**Body (multipart):** `file` (PDF)

**Response (JSON):**
```json
{"success": true, "page_count": 50, "added_pages": 8}
```

---

## Export

### POST /export/pdf/\<doc_id\>
Annotiertes PDF generieren und herunterladen.

**Response:** `application/pdf`

---

### POST /export/markdown/\<doc_id\>
Notizen als Markdown-Datei exportieren.

**Response:** `text/markdown`

---

### GET /export/original/\<doc_id\>
Original-PDF herunterladen.

**Response:** `application/pdf`

---

## Admin

Alle Admin-Endpunkte erfordern `is_admin = True`.

### GET /admin/
Benutzerverwaltungs-Übersicht (HTML).

---

### POST /admin/user/\<user_id\>/toggle-active
Benutzer aktivieren oder deaktivieren.

**Response (JSON):**
```json
{"success": true, "is_active": false}
```

---

### POST /admin/user/\<user_id\>/toggle-admin
Admin-Rechte vergeben oder entziehen.

**Response (JSON):**
```json
{"success": true, "is_admin": true}
```

---

### DELETE /admin/user/\<user_id\>
Benutzer löschen (inkl. aller Dokumente).

**Response (JSON):**
```json
{"success": true}
```

---

## Fehlercodes

| HTTP-Code | Bedeutung |
|---|---|
| `400` | Ungültige Eingabe (fehlende Datei, falscher Dateityp, ...) |
| `401` | Nicht eingeloggt |
| `403` | Keine Berechtigung (falscher Benutzer oder kein Admin) |
| `404` | Dokument nicht gefunden |
| `413` | Datei zu groß (über 50 MB) |
| `429` | Rate Limit überschritten |
| `500` | Interner Serverfehler |
