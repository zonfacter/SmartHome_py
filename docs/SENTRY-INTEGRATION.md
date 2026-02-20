# Sentry Error-Tracking Integration

**Version:** v5.0.0
**Status:** Implementiert (Phase 9)

---

## Übersicht

Sentry Error-Tracking ist jetzt in allen Modulen über BaseModule verfügbar. Fehler und Ereignisse werden automatisch zu Sentry gesendet, wenn konfiguriert.

---

## Setup

### 1. Sentry SDK installieren

```bash
pip install sentry-sdk==1.40.0
```

### 2. Environment-Variablen setzen

Kopiere `.env.example` zu `.env` und konfiguriere:

```env
# Sentry DSN (von sentry.io)
SENTRY_DSN=https://[your-key]@[org].ingest.sentry.io/[project-id]

# Environment (production, staging, development)
ENVIRONMENT=production
```

Sicherheitsregel: Verwende nur Platzhalter in Dokumentation und niemals reale Secrets im Repository.

### 3. Automatische Initialisierung

BaseModule initialisiert Sentry automatisch beim `__init__()`:

```python
class MyModule(BaseModule):
    def __init__(self):
        super().__init__()  # ← Initialisiert Sentry
        # ... rest of init
```

---

## Nutzung in Modulen

### Error Logging mit Context

```python
class MyModule(BaseModule):
    def critical_operation(self):
        try:
            # ... operation
            result = self.do_something_risky()
        except Exception as e:
            # Loggt zu Sentry MIT Context
            self.log_error(e, context={
                'operation': 'critical_operation',
                'user_id': 123,
                'data': some_data
            })
            # Re-raise für normale Error-Behandlung
            raise
```

### Message Logging

```python
# Info-Message
self.log_message(
    "System gestartet",
    level='info',
    context={'uptime': uptime_seconds}
)

# Warning
self.log_message(
    "Hohe CPU-Last",
    level='warning',
    context={'cpu_percent': 95}
)
```

### Levels

- `'fatal'` - Kritischer Fehler
- `'error'` - Fehler (Default)
- `'warning'` - Warnung
- `'info'` - Information

---

## Beispiele

### Connection Manager mit Sentry

```python
class ConnectionManager(BaseModule):
    def connect(self, connection_id):
        try:
            conn = self.connections[connection_id]
            conn.connect()

        except Exception as e:
            self.log_error(e, context={
                'connection_id': connection_id,
                'type': conn.connection_type,
                'attempt': self.reconnect_attempts
            }, level='error')

            # Auto-Reconnect Logic
            self._schedule_reconnect(connection_id)
```

### Data Gateway mit Performance Tracking

```python
class DataGateway(BaseModule):
    def route_data(self, source_id, tag, value):
        try:
            # Performance Critical Code
            if self.is_spam(source_id):
                self.log_message(
                    f"Spam detected from {source_id}",
                    level='warning',
                    context={
                        'source_id': source_id,
                        'rate': self.get_rate(source_id)
                    }
                )
                return

            # ... routing logic

        except Exception as e:
            self.log_error(e, context={
                'source_id': source_id,
                'tag': tag,
                'value_type': type(value).__name__
            })
```

---

## Sentry Features

### Automatisch erfasst:

1. **Exception Stack Traces**
2. **Module Context:**
   - Name
   - Version
   - Description
   - Author

3. **Environment:**
   - production / staging / development

4. **Release:**
   - `module_name@version`

5. **Tags:**
   - `module` - Modul-Name
   - `environment` - Environment

6. **Custom Context:**
   - Beliebige zusätzliche Daten

---

## Best Practices

### 1. Kritische Operationen wrappen

```python
def critical_operation(self):
    try:
        # ... operation
    except Exception as e:
        self.log_error(e, context={
            'operation': 'critical_operation',
            'state': self.get_state()
        })
        raise  # Re-raise für normale Behandlung
```

### 2. Performance-Probleme tracken

```python
if cpu_percent > 90:
    self.log_message(
        "High CPU usage detected",
        level='warning',
        context={'cpu_percent': cpu_percent}
    )
```

### 3. Wichtige Events loggen

```python
self.log_message(
    "Connection established",
    level='info',
    context={
        'connection_id': conn_id,
        'type': conn_type,
        'uptime': uptime
    }
)
```

### 4. Keine sensitiven Daten loggen

```python
# ❌ NICHT:
self.log_error(e, context={'password': user_password})

# ✅ STATTDESSEN:
self.log_error(e, context={'user_id': user_id})
```

---

## Sentry Dashboard

Auf https://sentry.io:

### Issues
- Fehler gruppiert nach Typ
- Stack Traces mit Source Code
- Breadcrumbs (Event-History)
- User Context

### Performance
- Transaction Traces
- Slow Operations
- N+1 Queries

### Releases
- Fehler pro Release
- Neue Fehler nach Deployment
- Regression Detection

---

## Deaktivierung

Sentry ist automatisch deaktiviert wenn:

1. `sentry-sdk` nicht installiert
2. `SENTRY_DSN` nicht gesetzt
3. `SENTRY_DSN` leer

Lokales Logging funktioniert weiterhin via `print()`.

---

## Testing

### Test mit Mock-Error:

```python
from modules.core.config_manager import ConfigManager

config_mgr = ConfigManager()

try:
    raise ValueError("Test Error for Sentry")
except Exception as e:
    config_mgr.log_error(e, context={
        'test': True,
        'source': 'manual_test'
    })

# Check Sentry Dashboard für neuen Issue
```

---

## Performance Impact

- **Overhead:** ~1-2ms pro log_error()
- **Async:** Sentry sendet asynchron (kein Blocking)
- **Sampling:** 100% Errors, 10% Performance Traces
- **Empfehlung:** Production-ready

---

## Troubleshooting

### "sentry-sdk nicht installiert"

```bash
pip install sentry-sdk==1.40.0
```

### "Sentry-Initialisierung fehlgeschlagen"

- Prüfe `SENTRY_DSN` Format
- Teste Connection: `https://sentry.io/settings/...`

### Keine Events in Sentry

1. Prüfe `.env` File existiert
2. Prüfe `SENTRY_DSN` korrekt
3. Prüfe Internet-Verbindung
4. Prüfe Sentry-Project aktiv

---

## Weiterführende Links

- [Sentry Python SDK Docs](https://docs.sentry.io/platforms/python/)
- [Sentry Performance Monitoring](https://docs.sentry.io/product/performance/)
- [Sentry Best Practices](https://docs.sentry.io/product/best-practices/)

---

**Implementiert:** 2026-01-05
**Phase:** 9 - Sentry Error-Tracking
**Autor:** SmartHome Edge OS Team
