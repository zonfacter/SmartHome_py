# 📊 Logging & Monitoring Guide

## Übersicht

Das System verwendet ein **Multi-Layer Logging-System**:

1. **Console Logging** - Direkte Ausgabe im Terminal
2. **SQLite Logging** - Persistente lokale Logs (`config/system_logs.db`)
3. **Sentry** - Cloud-basiertes Error Tracking & Performance Monitoring

---

## 🔧 Setup

### 1. Sentry Konfiguration (Optional, aber empfohlen)

#### Option A: Verwende bestehenden Sentry DSN (aus .env)

Die `.env.example` enthält bereits einen konfigurierten Sentry DSN:

```bash
SENTRY_DSN="https://df84f77f4768c3b6ed8224089e930008@o4510659601891328.ingest.de.sentry.io/4510659620831312"
ENVIRONMENT=development
```

Kopiere einfach `.env.example` nach `.env` (falls noch nicht geschehen):

```bash
cp .env.example .env
```

#### Option B: Eigenen Sentry Account erstellen

1. Gehe zu https://sentry.io und erstelle einen kostenlosen Account
2. Erstelle ein neues Projekt (Python/Flask)
3. Kopiere den DSN aus dem Projekt-Setup
4. Setze in `.env`:

```bash
SENTRY_DSN="https://[your-key]@[org].ingest.sentry.io/[project-id]"
ENVIRONMENT=production
```

#### Sentry deaktivieren

Um Sentry zu deaktivieren, entferne einfach den `SENTRY_DSN` aus `.env` oder setze ihn auf einen leeren String:

```bash
SENTRY_DSN=
```

---

## 📝 Logging im Code

### Web Manager Logging

Der `web_manager.py` loggt automatisch:

**Initialisierung:**
```
[OK] Web Manager v5.1.0 Initialisierung START
Pfade initialisiert: root=..., config=..., data=...
PLCConfigManager bereit: config_file=...
[OK] Web Manager v5.1.0 Initialisierung ABGESCHLOSSEN
```

**API-Requests:**
```
API Request: POST /api/plc/config from 127.0.0.1
POST /api/plc/config: Speichere PLC-Konfiguration...
Speichere nach: D:\...\config\plc_connections.json
PLC-Konfiguration erfolgreich gespeichert
```

**Fehler:**
```
[ERROR] CRITICAL: config_file ist None - Race Condition aufgetreten!
Debug: config_dir=...
Debug: plc_data_dir=...
```

---

## 🔍 Logs anzeigen

### 1. Console Logs

Echtzeit-Ausgabe beim Start:

```bash
python start_web_hmi.py
```

### 2. SQLite Logs

Logs werden in `config/system_logs.db` gespeichert. Abfrage mit:

```bash
python -c "from modules.core.database_logger import DatabaseLogger; logs = DatabaseLogger.get_recent_logs('config/system_logs.db', limit=50); import json; print(json.dumps(logs, indent=2))"
```

Oder über das Admin-Dashboard im Web-Interface:
- Gehe zu `/api/admin/logs`

### 3. Sentry Dashboard

Wenn Sentry konfiguriert ist:

1. Öffne https://sentry.io
2. Wähle dein Projekt
3. Siehe alle Fehler, Performance-Daten und Breadcrumbs

**Sentry zeigt automatisch:**
- Stack Traces bei Exceptions
- Request-Kontext (URL, Method, IP)
- Breadcrumbs (Pfad zum Fehler)
- Environment Tags (Platform, Python-Version)
- Performance-Traces (Slow API calls)

---

## 🐛 Debug-Modus

Für detaillierte Logs, setze das Logging-Level auf DEBUG:

### In start_web_hmi.py:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### In .env:

```bash
DEBUG=True
```

---

## 📈 Was wird geloggt?

### ✅ Geloggte Events

| Event | Level | Wo |
|-------|-------|-----|
| Web Manager Initialisierung | INFO | Console, SQLite, Sentry |
| API Requests (/api/plc/config) | INFO | Console, SQLite, Sentry |
| Erfolgreiche Speicheroperationen | INFO | Console, SQLite |
| Fehlerhafte API-Calls | ERROR | Console, SQLite, Sentry |
| Race Conditions (config_file = None) | FATAL | Console, SQLite, Sentry |
| Exceptions | ERROR | Console, SQLite, Sentry (mit Stack Trace) |
| Client Connect/Disconnect | INFO | Console |

### 🔐 Datenschutz

- **Keine persönlichen Daten** werden an Sentry gesendet (`send_default_pii=False`)
- **Sensible Header** (Authorization, Cookie) werden gefiltert
- **Passwörter in URLs** werden maskiert

---

## 🚀 Best Practices

### 1. Verwende Breadcrumbs für Context

Breadcrumbs helfen, den Weg zum Fehler nachzuvollziehen:

```python
if self.sentry:
    self.sentry.add_breadcrumb(
        message="User clicked save button",
        category="ui",
        level="info",
        data={"widget_id": "123"}
    )
```

### 2. Capture Messages für wichtige Events

```python
if self.sentry:
    self.sentry.capture_message(
        "Setup abgeschlossen",
        level="info",
        user_count=10,
        plc_connected=True
    )
```

### 3. Exceptions mit Kontext

```python
try:
    risky_operation()
except Exception as e:
    if self.sentry:
        self.sentry.capture_exception(e,
            component="plc_manager",
            operation="save_config",
            file_path=config_file
        )
```

---

## 🧪 Test-Logging

Teste die Logging-Konfiguration:

```bash
python test_web_manager_fix.py
```

Oder manuell:

```python
from modules.core.sentry_config import get_sentry_manager

sentry = get_sentry_manager()
sentry.initialize(environment="testing")

# Test Message
sentry.capture_message("Test-Nachricht", level="info")

# Test Exception
try:
    raise ValueError("Test-Exception")
except Exception as e:
    sentry.capture_exception(e)

print("Prüfe Sentry Dashboard für Events!")
```

---

## ❓ FAQ

### Frage: Wo finde ich die Logs?

**Antwort:**
- **Console**: Direkt im Terminal
- **SQLite**: `config/system_logs.db`
- **Sentry**: https://sentry.io Dashboard

### Frage: Warum erscheinen Fehler nicht in Sentry?

**Antwort:** Prüfe:
1. Ist `SENTRY_DSN` in `.env` gesetzt?
2. Ist die Internet-Verbindung aktiv?
3. Läuft der Code in einem `try-except` Block ohne Sentry-Capture?

### Frage: Kann ich Sentry lokal testen?

**Antwort:** Ja, setze `ENVIRONMENT=development` in `.env`. Alle Events werden mit "development" Tag versehen.

### Frage: Kostet Sentry Geld?

**Antwort:** Der Free-Plan bietet:
- 5.000 Events/Monat
- 10.000 Performance-Traces/Monat
- 1 Benutzer
- 30 Tage Event-Retention

Für kleine bis mittlere Projekte ausreichend!

---

## 📞 Support

Bei Fragen zum Logging-System:
1. Prüfe `test_web_manager_fix.py` Output
2. Schaue in `config/system_logs.db`
3. Prüfe Sentry Dashboard auf Fehler-Details
