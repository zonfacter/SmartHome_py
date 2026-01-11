# Quick-Start Guide - v4.5.3

**Version**: 4.5.3
**Datum**: 04.01.2026

---

## 🚀 Sofort-Test der neuen Features

### 1. Server starten

```bash
# Windows (UTF-8 Modus erforderlich!)
python -X utf8 start_web_hmi.py --port 5001

# Linux/Docker
python start_web_hmi.py --port 5001
```

**Erwartete Ausgabe**:
```
============================================================
SmartHome OS v4.5.3 - Web-HMI
============================================================

INFO     [database_logger] Database Logger initialisiert: D:\...\config\system_logs.db
  ⚡ config_manager v1.0.0 initialisiert
  ⚡ plc_communication v1.1.0 initialisiert
  ⚡ data_gateway v1.0.0 initialisiert
     🖥️  Platform: windows
     🐳 Docker: False
     🎮 GPU: True
     💾 Blob-Cache: 512 MB
  🔄 Synchronisiere 0 Widgets mit PLC...
  ℹ️  Widget-Sync: Keine Widgets konfiguriert
  ⚡ web_manager v1.0.0 initialisiert
```

**NEU in v4.5.3**:
- ✅ Database Logger initialisiert
- ✅ Widget-Sync läuft automatisch
- ✅ v4.5.3 wird angezeigt

---

## 🧪 Feature-Tests

### Test 1: DatabaseLogger

**Logs erzeugen**:
```python
# In Python-Console oder neuem Terminal
import logging
logger = logging.getLogger("TestModule")
logger.warning("Test-Warning - wird in DB gespeichert")
logger.error("Test-Error - wird in DB gespeichert")
```

**Logs abrufen** (via API):
```bash
# In Browser oder curl
curl http://localhost:5001/api/admin/logs?limit=10
```

**Erwartete Response**:
```json
[
  {
    "id": 1,
    "timestamp": "2026-01-04 14:23:45",
    "level": "WARNING",
    "module": "TestModule",
    "message": "Test-Warning - wird in DB gespeichert"
  },
  {
    "id": 2,
    "timestamp": "2026-01-04 14:23:46",
    "level": "ERROR",
    "module": "TestModule",
    "message": "Test-Error - wird in DB gespeichert"
  }
]
```

**Datenbank direkt öffnen**:
```bash
# Windows
sqlite3 config\system_logs.db "SELECT * FROM system_logs ORDER BY id DESC LIMIT 5;"

# Linux/macOS
sqlite3 config/system_logs.db "SELECT * FROM system_logs ORDER BY id DESC LIMIT 5;"
```

---

### Test 2: ServiceManager

**Service-Info abrufen**:
```bash
curl http://localhost:5001/api/admin/service/info
```

**Erwartete Response**:
```json
{
  "platform": "Windows",
  "python": "C:\\Python313\\python.exe",
  "args": ["start_web_hmi.py", "--port", "5001"],
  "is_restarted": false,
  "pid": 12345
}
```

**Service neustarten** (VORSICHT: Startet Server neu!):
```bash
curl -X POST http://localhost:5001/api/admin/service/restart \
  -H "Content-Type: application/json" \
  -d '{"delay": 3}'
```

**Erwartete Response**:
```json
{
  "status": "ok",
  "message": "Service wird in 3 Sekunden neu gestartet..."
}
```

**Nach Restart**:
- Server sollte automatisch neu starten
- Console zeigt: `✅ Service neu gestartet (Hot-Reload)`
- `/api/admin/service/info` zeigt: `"is_restarted": true`

---

### Test 3: Widget Subscription Sync

**Voraussetzung**: Mindestens 1 Widget konfiguriert

**Widget erstellen** (via API):
```bash
curl -X POST http://localhost:5001/api/widgets \
  -H "Content-Type: application/json" \
  -d '{
    "type": "switch",
    "title": "Test-Licht",
    "page": "dashboard",
    "bindings": {
      "value": {
        "variable": "MAIN.bLight1",
        "plc_type": "BOOL"
      }
    }
  }'
```

**Server neu starten**:
```bash
curl -X POST http://localhost:5001/api/admin/service/restart -d '{}'
```

**Erwartete Console-Ausgabe nach Restart**:
```
  🔄 Synchronisiere 1 Widgets mit PLC...
  ✅ Widget-Sync abgeschlossen: 1 Variablen registriert
```

**Vor v4.5.3**:
- Widget zeigt `UNKNOWN` für `MAIN.bLight1`

**Nach v4.5.3**:
- ✅ Variable wird beim Start vorab gelesen
- ✅ Widget zeigt sofort korrekten Wert

---

### Test 4: SerialLink (Plugin-Entwicklung)

**Beispiel-Plugin erstellen**:
```python
# In neuem File: modules/integration/my_modbus_plugin.py
from modules.gateway.serial_link import SerialLink
import serial

class MyModbusPlugin(SerialLink):
    def connect(self) -> bool:
        try:
            self.serial = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                timeout=self.timeout
            )
            self.is_connected = True
            self.log.info(f"✓ Verbunden mit {self.port}")
            return True
        except Exception as e:
            self.log.error(f"✗ Verbindung fehlgeschlagen: {e}")
            return False

    def disconnect(self) -> bool:
        if hasattr(self, 'serial'):
            self.serial.close()
        self.is_connected = False
        return True

    def read(self, address: int, count: int = 1):
        if not self.is_connected:
            return None
        # Modbus Read Logic hier
        data = self.serial.read(count)
        self.total_reads += 1
        return data

    def write(self, address: int, value) -> bool:
        if not self.is_connected:
            return False
        # Modbus Write Logic hier
        self.serial.write(value)
        self.total_writes += 1
        return True
```

**Plugin testen**:
```python
# In Python-Console
from modules.integration.my_modbus_plugin import MyModbusPlugin

# Context Manager
with MyModbusPlugin(port='COM3', baudrate=9600) as link:
    data = link.read(address=100, count=10)
    link.write(address=200, value=b'\x01\x02\x03')
    print(link.get_status())
```

---

## 🎨 Admin-Frontend (Optional)

**Was fehlt**: UI für Logs und Restart-Button

**Minimale Integration** (in `web/static/js/app.js`):

```javascript
// In loadAdminPage()
async loadAdminPage() {
    console.log('👑 Lade Admin...');

    // Lade Logs
    const logsRes = await fetch('/api/admin/logs?limit=50');
    const logs = await logsRes.json();

    console.log(`📋 ${logs.length} Logs geladen:`, logs);

    // Lade Service-Info
    const infoRes = await fetch('/api/admin/service/info');
    const info = await infoRes.json();

    console.log('ℹ️ Service-Info:', info);
}
```

**Restart-Button hinzufügen** (in `web/templates/index.html`):

```html
<!-- In Admin-Page -->
<button onclick="restartService()"
        class="px-4 py-2 bg-red-500 text-white rounded-lg hover:bg-red-600">
    🔄 Service Neustarten
</button>

<script>
async function restartService() {
    if (!confirm('Service wirklich neu starten?')) return;

    const res = await fetch('/api/admin/service/restart', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ delay: 2 })
    });

    const data = await res.json();
    alert(data.message);

    // Countdown
    let countdown = 2;
    const interval = setInterval(() => {
        countdown--;
        console.log(`Restart in ${countdown}s...`);
        if (countdown === 0) {
            clearInterval(interval);
            location.reload(); // Reload nach Restart
        }
    }, 1000);
}
</script>
```

---

## 🐛 Troubleshooting

### Problem: "Database Logger fehlgeschlagen"

**Lösung**:
```bash
# Verzeichnis erstellen
mkdir -p config

# Permissions prüfen (Linux)
chmod 755 config
```

---

### Problem: "ServiceManager nicht verfügbar"

**Symptom**: `/api/admin/service/restart` gibt Fehler

**Lösung**:
```bash
# Prüfe ob Modul existiert
ls modules/core/service_manager.py

# Import testen
python -c "from modules.core.service_manager import ServiceManager; print('OK')"
```

---

### Problem: "Widget-Sync findet keine Widgets"

**Symptom**: Console zeigt `ℹ️  Widget-Sync: Keine Widgets konfiguriert`

**Lösung**:
1. Widget via API erstellen (siehe Test 3)
2. Server neu starten
3. Sync sollte Widget finden

---

### Problem: "Restart funktioniert nicht unter Windows"

**Symptom**: Server stoppt, startet aber nicht neu

**Lösung**:
```python
# In service_manager.py Test-Modus
python modules/core/service_manager.py --test-restart
```

Wenn Test funktioniert, liegt es am Flask-Context.

**Workaround**:
```bash
# Manuell neu starten
python -X utf8 start_web_hmi.py --port 5001 --restarted
```

---

## 📊 Verifikation

### Checkliste v4.5.3

- [ ] Server startet mit "v4.5.3" Meldung
- [ ] `config/system_logs.db` wird erstellt
- [ ] `/api/admin/logs` liefert Daten
- [ ] `/api/admin/service/info` zeigt korrekten Status
- [ ] `/api/admin/service/restart` funktioniert
- [ ] Widget-Sync läuft beim Start
- [ ] Logging verwendet DatabaseLogger

---

## 🎯 Nächste Schritte

1. **Admin-Frontend-UI implementieren**
   - Log-Tabelle
   - Restart-Button
   - Service-Info-Anzeige

2. **Production-Deployment**
   - Firewall-Regeln für `/api/admin/*`
   - Authentifizierung hinzufügen
   - HTTPS aktivieren

3. **SerialLink-Plugins entwickeln**
   - Modbus RTU Plugin
   - KNX Plugin
   - RS485 Plugin

---

## 📞 Support

**Dokumentation**:
- `UPGRADE_453_COMPLETE.md` - Vollständige Feature-Dokumentation
- `CHANGELOG.md` - Änderungshistorie
- `ARCHITECTURE.md` - System-Architektur

**Logs prüfen**:
```bash
# SQLite-Logs
sqlite3 config/system_logs.db "SELECT * FROM system_logs;"

# Console-Logs
# Siehe Terminal-Output beim Start
```

---

**Version**: 4.5.3
**Autor**: Claude Sonnet 4.5
**Datum**: 04.01.2026
