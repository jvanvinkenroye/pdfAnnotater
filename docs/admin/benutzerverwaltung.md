# Benutzerverwaltung

Das Admin Panel ist unter `/admin/` erreichbar und nur für Benutzer mit Admin-Rechten zugänglich.

## Zugang

Nur Benutzer mit dem Flag `is_admin = 1` können das Admin Panel aufrufen. Der erste registrierte Benutzer erhält automatisch Admin-Rechte.

## Übersicht

Das Admin Panel zeigt alle registrierten Benutzer mit:

- Benutzername
- E-Mail-Adresse
- Registrierungsdatum
- Status (Aktiv / Inaktiv)
- Admin-Rechte (Ja / Nein)
- Anzahl der Dokumente

## Aktionen

### Benutzer aktivieren / deaktivieren

Inaktive Benutzer können sich nicht einloggen. Ihre Dokumente und Annotationen bleiben erhalten.

`POST /admin/user/<id>/toggle-active`

### Admin-Rechte vergeben / entziehen

Gibt einem Benutzer Admin-Rechte oder entzieht sie.

`POST /admin/user/<id>/toggle-admin`

### Benutzer löschen

Löscht den Benutzer und alle zugehörigen Dokumente und Annotationen.

`DELETE /admin/user/<id>`

## Schutzmechanismen

Das System verhindert folgende Aktionen:

| Aktion | Gesperrt |
|---|---|
| Admin deaktiviert sich selbst | Ja |
| Admin entzieht sich selbst Admin-Rechte | Ja |
| Admin löscht sich selbst | Ja |
| Letzter Admin wird deaktiviert | Ja |
| Letzter Admin verliert Admin-Rechte | Ja |
| Letzter Admin wird gelöscht | Ja |

!!! warning "Mindestens ein Admin"
    Das System stellt sicher, dass immer mindestens ein aktiver Admin-Benutzer vorhanden ist. Die entsprechenden Buttons werden in diesen Fällen deaktiviert oder der Request wird mit einem Fehler abgelehnt.

## Rate Limiting

Alle Admin-Aktionen unterliegen dem allgemeinen Rate Limit von 200 Requests pro Minute.
