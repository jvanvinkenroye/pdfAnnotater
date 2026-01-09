# 🚀 Produktions-Deployment Checkliste - PDF Annotator

## Vor dem Deployment

### ✅ Sicherheit (KRITISCH)

- [ ] **SECRET_KEY** als Umgebungsvariable gesetzt (32+ Zeichen, kryptographisch sicher)
  ```bash
  export SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))")
  ```

- [ ] **CSRF-Protection** aktiviert (Flask-WTF installieren)
  ```bash
  uv add flask-wtf
  ```

- [ ] **HTTPS** konfiguriert (Let's Encrypt/Cloudflare)
  - Alle HTTP Requests zu HTTPS umleiten
  - HSTS Header aktivieren

- [ ] **Firewall** konfiguriert
  - Nur notwendige Ports öffnen (443, 80 für Redirect)
  - Administrativen Zugang beschränken

- [ ] **Rate Limiting** implementieren (Flask-Limiter)
  ```bash
  uv add flask-limiter
  ```

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

Diese müssen VOR Produktions-Deployment behoben werden:

### 🔴 KRITISCH

1. **CSRF-Protection fehlt** - Alle POST/DELETE Endpoints anfällig
   - **Fix**: Flask-WTF integrieren (siehe oben)

2. **Rate Limiting fehlt** - DoS-anfällig
   - **Fix**: Flask-Limiter installieren

### 🟡 WICHTIG

3. **Session Management** - Keine Session-Timeouts
   - **Fix**: `PERMANENT_SESSION_LIFETIME` setzen

4. **File Type Validation** - Nur Extension-Check
   - **Fix**: Magic Bytes prüfen mit `python-magic`

---

## Support & Wartung

### Regelmäßige Aufgaben

- **Täglich**: Log-Files überprüfen
- **Wöchentlich**: Disk Space überprüfen, alte Exports löschen
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
