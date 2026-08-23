# 🚀 Produktions-Deployment Checkliste - PDF Annotator

## Vor dem Deployment

### ✅ Sicherheit (KRITISCH)

- [ ] **SECRET_KEY** als Umgebungsvariable gesetzt (32+ Zeichen, kryptographisch sicher)
  ```bash
  export SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))")
  ```
  Mit `PDF_ANNOTATOR_BEHIND_PROXY=1` ist `SECRET_KEY` **zwingend** — die App
  bricht sonst beim Start mit einem Fehler ab. Ohne das Flag wird ein
  fehlender Key automatisch generiert und unter `<data_dir>/secret_key`
  (0600) persistiert (Sessions überleben Neustarts, Worker teilen den Key).

- [ ] **PDF_ANNOTATOR_BEHIND_PROXY=1** gesetzt, wenn die App hinter einem
  TLS-terminierenden Reverse Proxy läuft — aktiviert ProxyFix
  (`X-Forwarded-For/Proto/Host`, 1 Hop), Secure-Session-Cookies, HSTS und
  https-URL-Schema. Niemals setzen, wenn kein vertrauenswürdiger Proxy
  davor steht (Header wären sonst angreifbar).

- [ ] **Registrierung absichern** — nach dem Anlegen der benötigten Accounts
  `PDF_ANNOTATOR_REGISTRATION=0` setzen (der erste Benutzer darf sich immer
  registrieren) und/oder einen `PDF_ANNOTATOR_INVITE_CODE` vergeben

- [ ] **CSRF-Protection** aktiv (Flask-WTF ist integriert; alle POST/DELETE
  Endpoints erfordern einen CSRF-Token — auch `save_annotation`)

- [ ] **HTTPS** konfiguriert (Let's Encrypt/Cloudflare)
  - Alle HTTP Requests zu HTTPS umleiten
  - HSTS Header aktivieren (setzt die App mit `PDF_ANNOTATOR_BEHIND_PROXY=1` selbst)

- [ ] **Firewall** konfiguriert
  - Nur notwendige Ports öffnen (443, 80 für Redirect)
  - Administrativen Zugang beschränken

- [ ] **Rate Limiting** konfiguriert (Flask-Limiter ist integriert;
  Standard-Storage `memory://` ist pro Worker-Prozess — Limits
  multiplizieren sich mit der Worker-Anzahl und werden bei Neustart
  zurückgesetzt. Für harte Limits `RATELIMIT_STORAGE_URI` auf einen
  gemeinsamen Store zeigen lassen, z.B. `redis://host:6379`)

### ✅ Konfiguration

- [ ] **DEBUG = False** in Produktionsumgebung
- [ ] **Database** Backup-Strategie festgelegt
- [ ] **Upload-Ordner** Berechtigungen korrekt (700 oder 755)
- [ ] **Logs** Rotation konfiguriert (logrotate)

### ✅ Code-Qualität

- [ ] **Alle Tests** bestehen
  ```bash
  pytest tests/ -v --cov=src/pdf_annotator
  ```

- [ ] **Linting** erfolgreich
  ```bash
  ruff check src/
  ```

- [ ] **Security Scan** durchgeführt
  ```bash
  bandit -r src/
  safety check
  ```

### ✅ Performance

- [ ] **Gunicorn** oder **uWSGI** statt Flask Development Server
  ```bash
  uv add gunicorn
  gunicorn "pdf_annotator.app:create_app()" --workers 4 --bind 0.0.0.0:8000
  ```

- [ ] **Nginx** als Reverse Proxy konfiguriert
- [ ] **Static Files** über Nginx servieren (nicht Flask)
- [ ] **Database** Connection Pooling (bei hoher Last)

### ✅ Monitoring & Logging

- [ ] **Application Monitoring** (Sentry, Datadog, New Relic)
- [ ] **Log Aggregation** (ELK Stack, Loki)
- [ ] **Uptime Monitoring** (UptimeRobot, Pingdom)
- [ ] **Disk Space Monitoring** (Uploads können viel Platz brauchen!)

### ✅ Backup & Recovery

- [ ] **Automatische Backups** der Datenbank (täglich)
- [ ] **Upload-Dateien** Backup (täglich oder kontinuierlich)
- [ ] **Disaster Recovery Plan** dokumentiert
- [ ] **Backup-Restore getestet** (mindestens 1x)

---

## Deployment-Schritte

### 1. Server-Vorbereitung

```bash
# System aktualisieren
sudo apt update && sudo apt upgrade -y

# Python und Dependencies installieren
sudo apt install python3 python3-pip python3-venv nginx -y

# uv installieren
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### 2. Code deployen

```bash
# Repository clonen
git clone https://github.com/your-repo/pdfAnnotater.git
cd pdfAnnotater

# Virtual Environment erstellen
uv venv --seed
source .venv/bin/activate

# Dependencies installieren
uv sync
```

### 3. Konfiguration

```bash
# Umgebungsvariablen setzen
export FLASK_ENV=production
export SECRET_KEY="YOUR_SECURE_RANDOM_SECRET_KEY"
# Hinter dem Nginx-Reverse-Proxy (siehe Schritt 6): Pflicht!
export PDF_ANNOTATOR_BEHIND_PROXY=1
export DATABASE_PATH="/var/www/pdfAnnotater/data/annotations.db"
export UPLOAD_FOLDER="/var/www/pdfAnnotater/data/uploads"

# Verzeichnisse erstellen
mkdir -p data/uploads data/exports
chmod 700 data/
```

### 4. Datenbank initialisieren

```bash
python3 -c "from pdf_annotator.models.database import DatabaseManager; DatabaseManager().init_db()"
```

### 5. Gunicorn starten

```bash
gunicorn "pdf_annotator.app:create_app()" \
  --workers 4 \
  --bind 127.0.0.1:8000 \
  --access-logfile logs/access.log \
  --error-logfile logs/error.log \
  --daemon
```

### 6. Nginx konfigurieren

```nginx
server {
    listen 80;
    server_name your-domain.com;

    # Redirect HTTP to HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name your-domain.com;

    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;

    # Security Headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;

    client_max_body_size 50M;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /static {
        alias /var/www/pdfAnnotater/src/pdf_annotator/static;
        expires 30d;
    }
}
```

---

## Nach dem Deployment

### ✅ Smoke Tests

- [ ] **Homepage** lädt korrekt
- [ ] **PDF Upload** funktioniert
- [ ] **Annotations** speichern funktioniert
- [ ] **Export** generiert PDFs korrekt
- [ ] **Löschen** funktioniert
- [ ] **Metadaten bearbeiten** funktioniert

### ✅ Security Checks

- [ ] **SSL Labs Test** (A+ Rating anstreben)
  https://www.ssllabs.com/ssltest/

- [ ] **Security Headers** prüfen
  https://securityheaders.com/

- [ ] **XSS Scan** durchführen

- [ ] **Path Traversal Test** durchführen

### ✅ Performance Tests

- [ ] **Load Test** mit 100+ gleichzeitigen Benutzern
  ```bash
  ab -n 1000 -c 100 https://your-domain.com/
  ```

- [ ] **Upload Performance** testen (große PDFs)

- [ ] **Response Time** < 200ms für statische Seiten

---

## Bekannte Sicherheitslücken (TODO)

Behoben (integriert, keine Aktion nötig):

- ✅ **CSRF-Protection** — Flask-WTF ist integriert; alle POST/DELETE
  Endpoints (inkl. `save_annotation`) erfordern einen CSRF-Token
- ✅ **Rate Limiting** — Flask-Limiter ist integriert (Storage via
  `RATELIMIT_STORAGE_URI` konfigurierbar)

Noch offen:

### 🟡 WICHTIG

1. **Session Management** - Keine Session-Timeouts
   - **Fix**: `PERMANENT_SESSION_LIFETIME` setzen

2. **File Type Validation** - Nur Extension-Check
   - **Fix**: Magic Bytes prüfen mit `python-magic`

---

## Support & Wartung

### Regelmäßige Aufgaben

- **Täglich**: Log-Files überprüfen
- **Wöchentlich**: Disk Space überprüfen (alte Exports, abgelaufene
  Hintergrund-Jobs und der Render-Cache werden automatisch vom
  Cleanup-Thread aufgeräumt, der alle 15 Minuten läuft)
- **Monatlich**: Security Updates installieren
- **Quartalsweise**: Backup-Restore testen

### Incident Response

1. **Bei Sicherheitsvorfall**:
   - Server sofort isolieren
   - Logs sichern
   - Forensische Analyse durchführen
   - Benutzer informieren (DSGVO!)

2. **Bei Ausfall**:
   - Status Page aktualisieren
   - Logs analysieren
   - Von Backup wiederherstellen wenn nötig

---

## Kontakt

- **Entwickler**: [Ihr Name]
- **Notfall-Hotline**: [Telefonnummer]
- **GitHub Issues**: [Repository URL]

---

**Last Updated**: 2026-01-09
**Security Score**: 85/100 (nach Security Hardening)
