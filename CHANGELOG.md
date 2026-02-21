# CHANGELOG.md

## v4.6.0 – Edge-Betriebssystem für industrielle Hausautomatisierung (🔄 In Entwicklung)

### Übersicht
Version **4.6.0** bringt eine vollständige Transformation des Systems von einer HMI-Visualisierung zu einem **Edge-Betriebssystem für industrielle Hausautomatisierung** nach dem Vorbild von ioBroker.

Das System wird nicht mehr nur eine Anwendung, sondern eine vollständig modulare Middleware-Plattform mit:
- Universal Data Router für alle Datenquellen
- Multi-Connection-Management
- ioBroker-Style Plugin-Manager
- Instanzen-Manager mit Ressourcen-Überwachung
- Industrielle Sicherheitsmechanismen (CPU-Throttling, Spam-Protection)
- Node-RED Integration

**Status:** 🔄 In Planung
**Erwartete Fertigstellung:** Q2 2026

---

## Geplante Hauptfunktionen

### 1. Universal Data Router (Phase 1)
**Status:** ❌ Nicht implementiert

**Neue Features:**
- Zentrale `route_data(source_id, tag, value)` Methode im DataGateway
- Einheitliche Normalisierung aller Datenpunkte in Unified Data Space
- Deklarative Routing-Regeln über `config/routing.json`
- Unterstützung komplexer Szenarien:
  - Bluetooth-BMS → PLC-Variable
  - PLC-Alarm → MQTT + Webhook + Logging
  - MQTT-Messwert → Aggregator → Dashboard
  - Bidirektionale Datenflüsse

**Technische Details:**
```python
# Beispiel: Routing-Engine
def route_data(self, source_id: str, tag: str, value: Any, metadata: dict = None):
    """
    Universal Router für alle Datenquellen

    Args:
        source_id: Quelle (z.B. "plc_001", "bt.bms_001", "mqtt.broker_1")
        tag: Datenpunkt (z.B. "MAIN.temperature", "voltage")
        value: Wert
        metadata: Zusätzliche Metadaten (Timestamp, Quality, etc.)
    """
    # Normalisierung in Unified Data Space
    datapoint = self.normalize(source_id, tag, value, metadata)

    # Route-Matching
    routes = self.routing_engine.match(datapoint)

    # Transformationen anwenden
    for route in routes:
        transformed_value = route.transform(datapoint)
        route.send_to_target(transformed_value)
```

**routing.json Schema:**
```json
{
  "version": "1.0",
  "routes": [
    {
      "id": "bms_to_plc",
      "from": "bt.bms_001.voltage",
      "to": "plc_001.MAIN.fbBattery.fVoltage",
      "transform": "scale(0.001)",
      "enabled": true
    },
    {
      "id": "alarm_multi_target",
      "from": "plc_001.MAIN.bAlarmActive",
      "to": [
        "mqtt.broker_local.alarms/critical",
        "webhook.alert_service",
        "log.system"
      ],
      "condition": "value == true"
    }
  ]
}
```

---

### 2. Multi-Connection Manager (Phase 2)
**Status:** ❌ Nicht implementiert

**Neue Module:**
- `modules/core/connection_manager.py`
  - Verwaltung beliebig vieler paralleler Verbindungen
  - Einheitliches Lifecycle-Management (start/stop/restart)
  - Health-Monitoring pro Verbindung
  - Hot-Reload von Konfigurationsänderungen

**Verwaltete Instanzen (Beispiele):**
```
PLC_1 (Keller) - 192.168.2.162.1.1:801
PLC_2 (Garage) - 192.168.2.163.1.1:801
MQTT_Local - localhost:1883
MQTT_HA - homeassistant.local:1883
BMS_1 (BT) - AA:BB:CC:DD:EE:FF
BMS_2 (RS485) - COM3
Modbus_Inverter_1 - 192.168.2.100:502
Modbus_Inverter_2 - 192.168.2.101:502
```

**PLCCommunication Refactoring:**
- Unterstützung für mehrere parallele AMS-Verbindungen
- Pro-Verbindung eigene Konfiguration und Cache
- Gemeinsames Error-Handling
- Automatisches Failover bei Verbindungsverlust

---

### 3. Bluetooth & BMS Integration (Phase 3)
**Status:** ❌ Nicht implementiert

**Neue Module:**
- `modules/integrations/bluetooth_manager.py`
  - Plattformunabhängig via `bleak` Library
  - BLE-Scanner für Geräte-Erkennung
  - Pairing und Verbindungsmanagement
  - RSSI-Monitoring

**BMS Plugin-System:**
- Abstrakte Basisklasse `modules/plugins/bms_parser_base.py`
- Konkrete Parser für verschiedene BMS-Typen:
  - `bms_daly.py` - Daly BMS
  - `bms_jbd.py` - JBD/Xiaoxiang BMS
  - `bms_victron.py` - Victron SmartShunt
  - `bms_ant.py` - ANT BMS

**Geparste BMS-Daten:**
- Gesamtspannung und Strom
- Einzelzellspannungen (bis 32 Zellen)
- SOC (State of Charge)
- Temperaturen
- Alarmzustände
- Lade-/Entlade-MOS-Status

---

### 4. TreeView UI & Data Browser (Phase 4)
**Status:** ❌ Nicht implementiert

**Frontend-Verbesserungen:**

**4.1 PLC-Symbol TreeView**
- Hierarchische Darstellung aller TwinCAT-Symbole
- Aufklappbare Strukturen (MAIN, GVLs, FBs)
- Filter nach Typ (BOOL, INT, REAL, etc.)
- Suchfunktion
- Symbol-Details (Adresse, Größe, Kommentar)

**4.2 MQTT-Topic-Browser**
- Automatische Baum-Generierung aus Topics
- Live-Updates bei neuen Topics
- Wert-Vorschau und Historie
- Subscribe/Unsubscribe direkt aus UI

**4.3 Bluetooth-Device-Browser**
- Live-Liste aller BLE-Geräte in Reichweite
- RSSI-Signalstärke-Balken
- Automatische Geräte-Identifikation
- Pairing-Funktionalität

---

### 5. Widget CRUD & Persistierung (Phase 5)
**Status:** ❌ Nicht implementiert

**Widget-Management:**
- Persistente Speicherung in `config/widgets.json`
- CRUD-Operationen über Web-API
- Automatische Backup-Erstellung
- Versionierung

**Web-API Endpunkte:**
```
GET    /api/widgets           - Liste aller Widgets
POST   /api/widgets           - Widget erstellen
GET    /api/widgets/<id>      - Widget abrufen
PUT    /api/widgets/<id>      - Widget aktualisieren
DELETE /api/widgets/<id>      - Widget löschen
POST   /api/widgets/import    - Widgets importieren
GET    /api/widgets/export    - Widgets exportieren
```

**Widget-Editor:**
- Drag-and-Drop Layout-Builder
- Grid-basiertes Layout-System
- Datenbindung an beliebige geroutete Datenpunkte
- Live-Vorschau
- Inline-Bearbeitung
- Widget-Templates

---

### 6. Plugin-Manager (ioBroker-Style) (Phase 6)
**Status:** ❌ Nicht implementiert

**Admin-UI: Plugin-Seite**
- Karten-basiertes Design
- Status-Badges:
  - ✅ Installiert & Aktiv
  - 📦 Installiert & Inaktiv
  - 🔄 Update verfügbar
  - 🌐 Verfügbar (nicht installiert)

**Plugin-Dokumentations-Viewer:**
- Automatisches Rendering von `README.md` aus Plugin-Ordnern
- Modal-Anzeige im Browser
- Markdown-Support mit Syntax-Highlighting
- Verlinkung zu externen Ressourcen

**Online-Update System:**
- `manifest.json` pro Plugin mit Metadaten
- Versionsprüfung gegen GitHub-Repository
- Automatische Update-Benachrichtigungen
- Ein-Klick-Update (Git-Pull + Dependency-Install)

**Plugin-Manifest Schema:**
```json
{
  "name": "bluetooth_manager",
  "version": "1.0.0",
  "author": "TwinCAT Team",
  "description": "Bluetooth BLE Manager für BMS-Integration",
  "repository": "https://github.com/user/repo",
  "dependencies": {
    "python": ">=3.8",
    "packages": ["bleak>=0.20.0"]
  },
  "config_schema": {
    "scan_interval": 5,
    "auto_connect": true
  }
}
```

---

### 7. Instanzen-Manager & Ressourcen-Monitoring (Phase 7)
**Status:** ❌ Nicht implementiert

**Admin-UI: Instanzen-Seite (ioBroker-Style)**
- Live-Übersicht aller aktiven Module/Plugins
- Kachel-Design mit Echtzeit-Metriken
- Status-Indikatoren (Running/Stopped/Error/Starting)

**Ressourcen-Tracking (via psutil):**
```python
# Pro Modul/Instanz:
{
  "module_id": "plc_001",
  "name": "PLC Keller",
  "status": "running",
  "cpu_percent": 2.5,          # CPU-Last in %
  "memory_mb": 45.2,            # RAM-Verbrauch in MB
  "memory_percent": 1.8,        # RAM in % vom System
  "disk_io_read_mb": 125.5,     # Gelesene Daten seit Start
  "disk_io_write_mb": 45.2,     # Geschriebene Daten seit Start
  "network_packets_sent": 12450,
  "network_packets_recv": 13200,
  "uptime_seconds": 302400,     # 3 Tage 12 Stunden
  "error_count": 0,
  "last_error": null
}
```

**UI-Features:**
- Sortierung nach CPU/RAM/Traffic
- Grafische Balken für Ressourcennutzung
- Warnung bei Grenzwert-Überschreitung
- Direkter Zugriff auf Logs

---

### 8. Lifecycle-Management & Panic-Mode (Phase 8)
**Status:** ❌ Nicht implementiert

**BaseModule Erweiterungen:**
```python
class BaseModule:
    def start(self):
        """Startet Modul (Thread/Prozess)"""

    def stop(self):
        """Soft-Stop: Sauberes Herunterfahren"""

    def restart(self):
        """Neustart des Moduls"""

    def force_kill(self):
        """Hard-Kill bei Thread-Lock"""
```

**Instanz-Steuerung (Web-API):**
```
POST /api/admin/instances/<id>/start   - Instanz starten
POST /api/admin/instances/<id>/stop    - Instanz stoppen (soft)
POST /api/admin/instances/<id>/restart - Instanz neu starten
POST /api/admin/instances/<id>/kill    - Instanz beenden (hard)
POST /api/admin/panic                  - Global Panic Mode
```

**Global Panic Button:**
- Prominenter roter Button im Admin-Header
- Bestätigungs-Dialog mit Countdown (5 Sekunden)
- Aktion:
  1. Trenne alle Hardware-Verbindungen (PLC, MQTT, BT, Modbus)
  2. Stoppe Router-Engine
  3. Deaktiviere alle Plugins
  4. Halte WebService am Leben für Remote-Zugriff
  5. Logge Panic-Event
- Wiederherstellung nur manuell durch Admin

---

### 9. Sentry Error-Tracking & Health-Monitoring (Phase 9)
**Status:** ❌ Nicht implementiert

**Sentry Integration:**
- Automatische Exception-Erfassung in `BaseModule.safe_run()`
- Stacktrace-Logging in `config/system_logs.db`
- Optional: Externe Sentry-Server-Integration
- Error-Dashboard im Admin-Bereich

**Error-Handling Wrapper:**
```python
def safe_run(self):
    """Wrapper mit automatischer Fehlererfassung"""
    try:
        self.execute()
    except Exception as e:
        self.error_count += 1
        self.last_error = str(e)
        self.status = "error"
        self.log_to_sentry(e)

        if self.error_count > 5:
            self.handle_crash()
```

**Health-Pulse System:**
- Jedes Plugin sendet alle 5 Sekunden Heartbeat
- Watchdog-Thread überwacht Pulse-Timeouts
- Auto-Restart bei fehlendem Pulse (konfigurierbar)
- Health-Status in Instanzen-Übersicht

**Sandbox-Limits:**
- Konfigurierbare RAM-Limits pro Plugin
- Auto-Kill bei Speicherlecks
- Warnung bei 80% Grenzwert
- Eskalations-Strategie: Warnung → Throttling → Kill

---

### 10. CPU-Throttling & Spam-Protection (Phase 10)
**Status:** ❌ Nicht implementiert

**CPU-Limitierung (SPS-Style):**
- Emulation von TwinCAT-Task-Zyklen
- Plugin bekommt `max_cpu_share` Vorgabe (z.B. 10%)
- Automatisches Throttling bei Überschreitung
- `time.sleep()` Injection zur CPU-Entlastung

**Prozess-Prioritäten (via psutil):**
```python
# System-kritische Dienste
webservice.set_priority(PRIORITY_HIGH)
data_gateway.set_priority(PRIORITY_ABOVE_NORMAL)

# Standard-Plugins
mqtt_client.set_priority(PRIORITY_NORMAL)

# Rechenintensive Plugins
video_stream.set_priority(PRIORITY_BELOW_NORMAL)
```

**Spam-Protection Circuit Breaker:**
- Router zählt Pakete pro Quelle (pps)
- Konfigurierbare Schwellenwerte (z.B. 500 pps)
- Aktion bei Überschreitung:
  - Status → `SUSPENDED_BY_SPAM`
  - Auto-Disable des Moduls
  - Rote Warnmeldung in UI
  - Log-Eintrag mit Details

**Status-Meldung in UI:**
```
⚠️ Plugin "MQTT_Client_1" automatisch deaktiviert
   Grund: Spam-Schutz ausgelöst (650 pps überschritten)
   Schwellenwert: 500 pps
   Letzte Aktivität: 2026-01-04 14:32:15

   [Manuell reaktivieren] [Logs anzeigen] [Schwellenwert anpassen]
```

**Administrative Test-Funktion:**
- "Disconnect"-Button pro Verbindung in UI
- Trennt Modul vom Router (ohne Prozess zu beenden)
- Nützlich für Debugging und Fehlerdiagnose
- "Reconnect"-Button zur Wiederverbindung

---

### 11. Node-RED Integration (Phase 11)
**Status:** ❌ Nicht implementiert

**MQTT-Bridge:**
- Automatische Spiegelung aller Datenflüsse auf lokalen MQTT-Broker
- Topic-Schema: `smarthome/{source}/{path}/{tag}`
- Beispiel: `smarthome/plc_001/MAIN/temperature`

**Datenfluss:**
```
Datenquelle → DataGateway.route_data()
                    ↓
              Routing-Engine
                    ↓
         ┌──────────┴──────────┐
         ↓                     ↓
   Internal Targets      MQTT-Publish
   (Widgets, DB)              ↓
                         MQTT-Broker
                              ↓
                          Node-RED
                              ↓
                       Logik-Flows
                              ↓
                         MQTT-Publish
                              ↓
         DataGateway ← route_data()
```

**Optimierte WebSocket/REST-API:**
- Dedizierter `/api/nodered/stream` Endpunkt
- Effizientes JSON-Streaming
- Authentifizierung via Token
- Rate-Limiting

**Dashboard-Integration (Zukunft):**
- IFrame-Embedding von Node-RED-Dashboards
- Single-Sign-On (SSO)
- Einheitliches Theme

---

## Breaking Changes

### DataGateway
- **Entfernt:** Direkte Hardware-UI-Bindings
- **Neu:** Alle Datenpunkte müssen über Routing-Engine
- **Migration:** Widgets müssen auf neue Datenpunkt-Notation umgestellt werden

### PLCCommunication
- **Geändert:** Von Single-Instance zu Multi-Instance-Architektur
- **Migration:** `plc_ams_net_id` Config → `plc_configs.json` mit mehreren Einträgen

### Konfigurationsdateien
- **Neu:** `config/routing.json` (zwingend erforderlich)
- **Neu:** `config/widgets.json` (ersetzt alte Widget-Konfiguration)
- **Neu:** `config/connections.json` (Multi-Connection-Definitionen)

### Web-API
- **Geändert:** Viele Endpunkte umbenannt/verschoben
- **Neu:** `/api/admin/*` für Admin-Funktionen
- **Neu:** `/api/router/*` für Routing-Operationen

---

## Migration von v4.x zu v4.6.0

### Schritt 1: Backup erstellen
```bash
# Backup aller Configs
cp -r config config_backup_v4
cp -r TwinCAT_SmartHome TwinCAT_SmartHome_backup_v4
```

### Schritt 2: Neue Config-Dateien erstellen
```bash
# routing.json erstellen (Beispiel-Template wird bereitgestellt)
# widgets.json wird bei erstem Start automatisch generiert
# connections.json aus alter Config migrieren
```

### Schritt 3: Dependencies aktualisieren
```bash
pip install -r requirements.txt
# Neu: bleak, psutil (erweitert)
```

### Schritt 4: Widgets neu konfigurieren
- Alte Widget-Konfiguration über neuen Widget-Editor neu erstellen
- Datenpunkt-Notation an neue Routing-Engine anpassen
- Schema: `{source_id}.{path}.{tag}` statt direkter PLC-Symbole

### Schritt 5: Testing
- Alle Verbindungen im Connection-Manager testen
- Routing-Regeln validieren
- Widget-Funktionalität überprüfen

---

## Abhängigkeiten

### Neu hinzugefügt
- `bleak>=0.20.0` - Bluetooth Low Energy (plattformunabhängig)
- `psutil>=5.9.0` - Prozess- und System-Monitoring (erweiterte Features)
- `jsonschema>=4.0.0` - Validierung von routing.json/manifest.json

### Aktualisiert
- `flask>=2.3.0` - Web-Framework
- `flask-socketio>=5.3.0` - WebSocket-Support

---

## Performance-Verbesserungen

- Routing-Engine mit O(1) Lookup für direkte Routen
- Multi-Threading für parallele Verbindungen
- Optimiertes Caching im DataGateway
- Reduzierter Memory-Footprint durch Lazy-Loading von Plugins

---

## Sicherheitsverbesserungen

- CPU-Throttling verhindert DoS durch fehlerhafte Plugins
- Spam-Protection schützt vor Daten-Flooding
- Sandbox-Limits verhindern Memory-Leaks
- Health-Monitoring erkennt hängende Module
- Panic-Mode für Notfall-Shutdown

---

## Bekannte Einschränkungen

- Node-RED Integration erfordert separaten MQTT-Broker
- Bluetooth-BMS auf Windows erfordert Bluetooth-Adapter mit BLE-Support
- Force-Kill kann in seltenen Fällen zu inkonsistentem State führen
- Online-Update erfordert Git-Installation auf dem System

---

## Zusammenfassung

Version **v4.6.0** transformiert das Projekt zu einem vollwertigen **Edge-Betriebssystem für industrielle Hausautomatisierung**. Die neue Architektur ermöglicht:

✅ **Flexible Datenflüsse** durch Universal Data Router
✅ **Beliebig viele Verbindungen** durch Connection Manager
✅ **Erweiterbarkeit** durch Plugin-System
✅ **Übersichtlichkeit** durch ioBroker-Style Admin-UI
✅ **Stabilität** durch Health-Monitoring und Throttling
✅ **Integration** mit Node-RED für komplexe Logiken

---

**Entwicklungsstand:** 2026-01-04
**Status:** In Planung (0% Implementation)
**Zielversion:** 4.6.0
**Erwartete Fertigstellung:** Q2 2026

---

## v4.7.x – Aktuelle Version (Stabil)

### Features
- ✅ Web-HMI mit Flask + SocketIO
- ✅ TwinCAT ADS Integration (einzelne PLC)
- ✅ MQTT Integration
- ✅ Modbus Integration
- ✅ DataGateway mit Blob- und Telemetrie-Cache
- ✅ Symbol-Browser für TwinCAT
- ✅ Logging-Framework
- ✅ Service-Management
- ✅ Hardware-Monitoring
- ✅ Responsive Web-UI

### Bekannte Limitierungen (werden in v4.6.0 behoben)
- Nur eine PLC-Verbindung gleichzeitig
- Kein Bluetooth-Support
- Keine flexible Routing-Engine
- Widgets nicht persistent gespeichert
- Keine Ressourcen-Überwachung pro Modul
- Keine Plugin-Verwaltung

---

**Letzte Aktualisierung:** 2026-01-04
