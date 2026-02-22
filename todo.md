# PDF Annotator - Code Analysis TODO

## HIGH Priority

- [x] H-01: CSRF-Schutz fuer alle POST/DELETE Endpoints (Flask-WTF)
- [x] H-02: doc_id UUID-Validierung in allen Routes
- [x] H-03: Security Headers (CSP, X-Frame-Options, HSTS)
- [x] H-04: SQLite Foreign Keys aktivieren (PRAGMA foreign_keys = ON)
- [x] H-05: Export-Dateien nach Download aufraeumen
- [x] H-06: File Handle Leak in suppress_output() fixen
- [x] H-07: Zip Slip Vulnerability im Import fixen
- [x] H-08: Path Traversal Check in replace_pdf ergaenzen
- [x] H-09: Metadata-Felder beim AJAX-Upload mitsenden
- [x] H-10: Race Condition in save-then-navigate (Promise-basiert)
- [x] H-11: Skip Navigation + ARIA Labels ergaenzen
- [x] H-12: innerHTML durch sichere DOM-APIs ersetzen

## MEDIUM Priority

- [x] M-01: DatabaseManager Singleton Thread-Safety
- [x] M-02: LRU Cache nach PDF-Replacement clearen
- [x] M-03: PDF Render DPI reduzieren (150 fuer Browser, 300 fuer Export)
- [x] M-04: Duplicate format_timestamp/filename-Logik extrahieren
- [x] M-05: Schema-Migrationen: spezifische Exceptions statt bare except
- [x] M-06: doc_id Overwrite nach File Storage fixen
- [x] M-07: Spezifische Exception-Typen statt bare except Exception
- [x] M-08: Rate Limiting fuer Upload/Render Endpoints
- [x] M-09: any -> Any Type-Annotations korrigieren
- [x] M-10: Import _update_document_id O(N) Scan optimieren
- [x] M-11: FLASK_ENV durch aktuellen Mechanismus ersetzen
- [x] M-12: fitz.open() mit Context Managern verwenden
- [x] M-13: Metadata-Laengenvalidierung beim Upload
- [x] M-14: ZIP Bomb Mitigation beim Import
- [x] M-15: beforeunload save mit sendBeacon
- [x] M-16: Inline JS aus documents.html in documents.js extrahieren
- [x] M-17: alert()/confirm() durch Modal/Toast-System ersetzen
- [x] M-18: Client-seitiges Image Caching + Cache Headers

## LOW Priority

- [x] L-01: f-strings in Logging durch lazy evaluation ersetzen
- [x] L-02: Doppelte ruff-Config bereinigen
- [x] L-03: get_page_count Typ-Konsistenz (str vs Path)
- [x] L-04: TestingConfig.DATABASE_PATH als Path
- [x] L-05: create_app Parameter-Typ str | None
- [x] L-06: Log-Rotation konfigurieren
- [x] L-07: sys.path Hack in run_desktop.py entfernen
- [x] L-08: Inline styles durch CSS-Klassen ersetzen
- [x] L-09: Color Contrast fuer secondary text pruefen
- [x] L-10: Flash Messages auto-dismiss + Close-Button
- [x] L-11: Year Input pattern/type Validierung
- [x] L-12: Documents Table responsive fuer Mobile
