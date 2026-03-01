# Produktionskonfiguration

## SECRET_KEY

Der `SECRET_KEY` muss für den Produktionsbetrieb als Umgebungsvariable gesetzt werden. Ohne ihn sind Sessions nach jedem Neustart ungültig (Benutzer werden ausgeloggt).

```bash
# Zufälligen Key generieren
python3 -c "import secrets; print(secrets.token_hex(32))"
```

!!! danger "Niemals committen"
    Den `SECRET_KEY` niemals in `.env`-Dateien committen oder in Logs ausgeben. Die `.env`-Datei ist in `.gitignore` eingetragen.

## Reverse Proxy mit nginx

Für HTTPS-Betrieb sollte ein Reverse Proxy vorgeschaltet werden.

```nginx
server {
    listen 443 ssl;
    server_name annotations.example.com;

    ssl_certificate     /etc/letsencrypt/live/annotations.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/annotations.example.com/privkey.pem;

    location / {
        proxy_pass         http://localhost:8000;
        proxy_set_header   Host              $host;
        proxy_set_header   X-Real-IP         $remote_addr;
        proxy_set_header   X-Forwarded-For   $proxy_add_x_forwarded_for;
        proxy_set_header   X-Forwarded-Proto $scheme;
        client_max_body_size 50M;
    }
}

server {
    listen 80;
    server_name annotations.example.com;
    return 301 https://$host$request_uri;
}
```

## Security Headers

Die App setzt folgende Security-Header automatisch:

| Header | Wert |
|---|---|
| `X-Content-Type-Options` | `nosniff` |
| `X-Frame-Options` | `DENY` |
| `X-XSS-Protection` | `1; mode=block` |
| `Referrer-Policy` | `strict-origin-when-cross-origin` |
| `Content-Security-Policy` | `default-src 'self'; script-src 'self' 'unsafe-inline'; ...` |

## Rate Limiting

| Endpunkt | Limit |
|---|---|
| `POST /auth/login` | 5 / Minute (Brute-Force-Schutz) |
| `POST /upload` | 10 / Minute |
| `GET /viewer/api/page/...` | 60 / Minute |
| `POST /import` | 10 / Minute |
| `POST /auth/theme` | 30 / Minute |
| Alle anderen | 200 / Minute |

## CSRF-Schutz

Alle `POST`- und `DELETE`-Endpunkte sind durch CSRF-Tokens geschützt (Flask-WTF). Ausnahme: `POST /viewer/api/annotation/<doc_id>/<page>` — dieser Endpunkt wird via `sendBeacon` beim Schließen des Browsers aufgerufen und kann keine CSRF-Header senden. Er ist durch UUID-Validierung gesichert.

## Gunicorn Workers

```bash
# Empfehlung: 2 * CPU-Kerne + 1
GUNICORN_WORKERS=5  # Für 2 CPU-Kerne
```

Bei Worker-Abstürzen startet Gunicorn automatisch neue Worker. Timeout: 120 Sekunden (für große PDF-Exporte).

## Logs

Logs werden sowohl in die Datei als auch nach stdout geschrieben:

```bash
# Docker
docker compose logs -f

# Direkter Dateizugriff (macOS)
tail -f ~/Library/Application\ Support/PDF-Annotator/app.log
```

Log-Level: `INFO` (Produktion), `DEBUG` (Entwicklung)
