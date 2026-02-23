# ROADMAP.md

## Projektübersicht
Diese Roadmap beschreibt die Transformation von einer Visualisierungssoftware zu einem vollwertigen **Edge-Betriebssystem für industrielle Hausautomatisierung** nach dem Vorbild von ioBroker, jedoch optimiert für SPS/PLC-Integration und industrielle Datenquellen.

---

## Version 4.x – Aktuelle Basis (✅ Abgeschlossen)
- Logging-Framework zur strukturierten Fehlererfassung
- Stabiler Service-Restart
- Symbol- und Struktur-Browser für TwinCAT/ADS
- Hardware-Monitoring
- MQTT-Integration
- Modbus-Integration
- Web-HMI mit Flask + SocketIO
- DataGateway mit Blob- und Telemetrie-Cache

Diese Basis dient als solides Fundament für die v5-Generation.

---

## Version 5.0 – Universal Data Hub & Multi-Connectivity

### 🎯 Zielarchitektur
**Leitprinzipien:**
- Datenfluss statt Punkt-zu-Punkt-Logik
- Vollständige Entkopplung von Hardware, Logik und UI
- Konfigurierbare, wiederverwendbare Routingregeln
- Erweiterbarkeit durch Plugins
- Plattform-Agnostisch (Windows, Linux, Docker)
- Hardware-Unabhängigkeit

**Vision:**
```
Datenquelle → Normalisierung → Routing-Engine → Ziel(e)
           → UI → Automation → Persistenz → Analytics
```

---

## Phase 1: Router-Engine & Data Routing (🔄 In Planung)

### 1.1 Universal Data Router
**Status:** ❌ Nicht implementiert

**Ziele:**
- Refactoring `data_gateway.py`: Implementierung der Methode `route_data(source_id, tag, value)`
- Einheitliche Normalisierung aller Datenpunkte in den Unified Data Space
- Zentrale Verarbeitung für ADS, MQTT, Bluetooth, Modbus, RS485, CAN
- Routing-Regeln über `routing.json` konfigurierbar

**Features:**
- Datenfluss-Routing: Bluetooth-BMS → PLC-Variable
- Multi-Target: PLC-Alarm → MQTT + Webhook
- Transformationen: MQTT-Messwert → Aggregator → Dashboard
- Bidirektionales Routing

**Beispiel routing.json:**
```json
{
  "routes": [
    {
      "from": "bt.bms_001.voltage",
      "to": "plc.MAIN.fbBattery.fVoltage",
      "transform": "scale(0.001)"
    },
    {
      "from": "plc.MAIN.alarm_active",
      "to": ["mqtt.alarms/critical", "webhook.alert_service"]
    }
  ]
}
```

### 1.2 Routing-Engine Features
- Route-Matching mit Wildcards (`plc.*.temperature`)
- Transformations-Pipeline (Skalierung, Filterung, Aggregation)
- Bedingte Routen (nur bei Schwellenwert)
- Zeitbasierte Routen (nur während bestimmter Zeiten)

---

## Phase 2: Multi-Connection Manager (🔄 In Planung)

### 2.1 Connection Manager
**Status:** ❌ Nicht implementiert

**Ziele:**
- Neues Modul: `modules/core/connection_manager.py`
- Verwaltung beliebig vieler paralleler Verbindungen
- Einheitliches Lifecycle-Management
- Hot-Reload der Verbindungsdefinitionen

**Verwaltete Instanzen:**
```
PLC_1 (Keller)
PLC_2 (Garage)
MQTT_Broker_Local
MQTT_Broker_External (Home Assistant)
BMS_1 (Bluetooth)
BMS_2 (RS485)
Modbus_Inverter_1
Modbus_Inverter_2
```

### 2.2 PLCCommunication Refactoring
**Aktuell:** Unterstützt nur eine PLC-Verbindung
**Ziel:** Multi-Instance-Architektur

**Features:**
- Mehrere AMS-Verbindungen gleichzeitig
- Pro-Verbindung eigene Konfiguration
- Gemeinsames Health-Monitoring
- Automatisches Failover

---

## Phase 3: Bluetooth & BMS Integration (🔄 In Planung)

### 3.1 Bluetooth Manager
**Status:** ❌ Nicht implementiert

**Ziele:**
- Neues Modul: `modules/integrations/bluetooth_manager.py`
- Bibliothek: `bleak` (plattformunabhängig)
- Scan-Modus für MAC-Adressen-Erkennung
- Admin-UI: Live-Anzeige aller verfügbaren BLE-Geräte

### 3.2 BMS Parser Plugin-System
**Ziele:**
- Abstrakte Basisklasse `BMSParser`
- Plugin-Architektur für verschiedene BMS-Typen:
  - Daly BMS
  - JBD BMS
  - Victron SmartShunt
  - ANT BMS
- Geparste Werte → `DataGateway.route_data()`

**BMS-Daten:**
- Spannung, Strom, SOC
- Zellspannungen
- Temperatur
- Alarmzustände

---

## Phase 4: TreeView UI & Data Browser (🔄 In Planung)

### 4.1 PLC-Symbol TreeView
**Status:** Parser existiert, UI fehlt

**Ziele:**
- Frontend (`app.js`): `renderTreeView(data)`
- Hierarchische Darstellung aller TwinCAT-Symbole
- Aufklappbare Strukturen
- Filter und Suche
- Typ-Übersicht

### 4.2 MQTT-Topic-Browser
**Ziele:**
- Automatische Baumstruktur aus Topics
- Live-Updates bei neuen Topics
- Wert-Vorschau

### 4.3 Bluetooth-Device-Browser
**Ziele:**
- Live-Liste aller BLE-Geräte
- RSSI-Signalstärke-Anzeige
- Pairing-Funktionalität
- Geräte-Identifikation

---

## Phase 5: Widget CRUD & Persistierung (🔄 In Planung)

### 5.1 widgets.json System
**Status:** ❌ Nicht implementiert

**Ziele:**
- Automatische Speicherlogik für `config/widgets.json`
- CRUD-Operationen über Web-API
- Widget-Konfiguration persistent speichern
- Versionierung und Backup

**Widget-Struktur:**
```json
{
  "widget_001": {
    "type": "gauge",
    "title": "Batteriespannung",
    "bindings": {
      "value": {
        "source": "bt.bms_001.voltage",
        "type": "REAL"
      }
    },
    "layout": {
      "x": 0,
      "y": 0,
      "w": 2,
      "h": 2
    }
  }
}
```

### 5.2 Widget-Editor
- Drag-and-Drop Layout-Builder
- Datenbindung an beliebige geroutete Datenpunkte
- Live-Vorschau
- Inline-Bearbeitung

---

## Phase 6: Plugin-Manager (ioBroker-Style) (🔄 In Planung)

### 6.1 Plugin-Verwaltungs-UI
**Status:** ❌ Nicht implementiert

**Ziele:**
- Admin-Seite: Plugin-Marketplace
- Karten-Design für jedes Plugin
- Status-Badges: Installiert / Verfügbar / Update bereit
- Info-Button für Dokumentation

### 6.2 Plugin-Dokumentations-Viewer
**Ziele:**
- Automatisches Rendering von `README.md` aus Plugin-Ordnern
- Modal-Anzeige im Browser
- Markdown-Support
- Syntax-Highlighting für Code-Beispiele

### 6.3 Online-Update System
**Ziele:**
- `manifest.json` pro Plugin mit Versionsinformationen
- GitHub-Versions-Prüfung
- Automatische Update-Benachrichtigungen
- Ein-Klick-Update (Git-Pull)

**Beispiel manifest.json:**
```json
{
  "name": "bluetooth_manager",
  "version": "1.0.0",
  "author": "TwinCAT Team",
  "repository": "https://github.com/user/repo",
  "dependencies": ["bleak>=0.20.0"]
}
```

---

## Phase 7: Instanzen-Manager & Ressourcen-Monitoring (🔄 In Planung)

### 7.1 Instanzen-Übersicht (ioBroker-Style)
**Status:** ❌ Nicht implementiert

**Ziele:**
- Admin-Seite: Instanzen-Manager
- Live-Monitoring aller aktiven Module
- Kachel-Design mit Status-Indikatoren

### 7.2 Ressourcen-Tracking
**Ziele:**
- CPU-Last pro Modul/Plugin (via `psutil`)
- RAM-Verbrauch (Cache/Heap)
- HDD/SSD-I/O (Log-Schreiblast)
- Netzwerk-Traffic (Pakete/Sekunde)

**Metriken pro Instanz:**
```
PLC_1 (Keller)
├── CPU: 2.5%
├── RAM: 45 MB
├── Traffic: 120 pps (in/out)
└── Uptime: 3d 12h
```

### 7.3 Web-API Endpunkte
```
GET  /api/admin/instances/stats
POST /api/admin/instances/<id>/start
POST /api/admin/instances/<id>/stop
POST /api/admin/instances/<id>/restart
POST /api/admin/instances/<id>/kill
```

---

## Phase 8: Lifecycle-Management & Panic-Mode (🔄 In Planung)

### 8.1 Modul-Lifecycle
**Status:** ❌ Nicht implementiert

**Ziele:**
- Erweiterung `BaseModule`: `start()`, `stop()`, `restart()`
- Soft-Stop: Sauberes Herunterfahren mit Ressourcen-Freigabe
- Status-Tracking: Running / Stopped / Starting / Error

### 8.2 Force-Kill Funktion
**Ziele:**
- Harte Thread-/Prozess-Beendigung via OS-Signal
- Schutz vor Thread-Locks
- Admin-UI: Totenkopf-Icon für Force-Kill
- Warnung vor kritischen Modulen (z.B. DataGateway)

### 8.3 Global Panic Button
**Ziele:**
- Notfall-Shutdown aller Hardware-Verbindungen
- WebService bleibt aktiv für Remote-Zugriff
- Prominenter roter Button im Admin-Header
- Bestätigungs-Dialog zur Vermeidung versehentlicher Klicks

**Panic-Modus:**
```
1. Trenne alle PLC-Verbindungen (ADS)
2. Stoppe MQTT-Clients
3. Trenne Bluetooth-Verbindungen
4. Beende Modbus/Serial-Kommunikation
5. Deaktiviere Router-Engine
6. Halte WebService am Leben
```

---

## Phase 9: Sentry Error-Tracking & Health-Monitoring (🔄 In Planung)

### 9.1 Sentry Integration
**Status:** ❌ Nicht implementiert

**Ziele:**
- Automatische Exception-Erfassung in `BaseModule`
- Stacktrace-Logging in `config/system_logs.db`
- Optional: Externe Sentry-Server-Integration
- Error-Dashboard im Admin-Bereich

### 9.2 Health-Pulse System
**Ziele:**
- Jedes Plugin sendet alle 5 Sekunden ein "Heartbeat"-Signal
- Watchdog erkennt hängende Module
- Auto-Restart bei ausbleibendem Pulse
- Health-Status in Instanzen-Übersicht

### 9.3 Sandbox-Limits
**Ziele:**
- Maximaler RAM-Verbrauch pro Plugin (z.B. 50 MB)
- Auto-Kill bei Speicherlecks
- Warnung bei Grenzwert-Annäherung (80%)
- Konfigurierbare Limits pro Plugin-Typ

---

## Phase 10: CPU-Throttling & Spam-Protection (🔄 In Planung)

### 10.1 CPU-Limitierung (SPS-Style)
**Status:** ❌ Nicht implementiert

**Ziele:**
- Emulation von TwinCAT-Task-Zyklen
- Plugin bekommt `max_cpu_share` Vorgabe
- Automatisches Throttling bei Überschreitung
- `time.sleep()` Injection zur CPU-Entlastung

**Beispiel:**
```python
# Plugin darf max. 10% CPU nutzen
# Bei Überschreitung: Delay-Injection
if cpu_usage > max_cpu_share:
    time.sleep(0.1)  # Gib CPU frei
```

### 10.2 Prozess-Prioritäten
**Ziele:**
- WebService auf "High Priority" (via `psutil`)
- DataGateway auf "Above Normal"
- Rechenintensive Plugins auf "Below Normal"
- OS-Level Priorisierung für kritische Dienste

### 10.3 Spam-Protection Circuit Breaker
**Ziele:**
- Router zählt Pakete pro Quelle (pps - packets per second)
- Schwellenwert: z.B. 500 pps
- Aktion bei Überschreitung:
  - Status → `SUSPENDED_BY_SPAM`
  - Auto-Disable des Moduls
  - Rote Status-Meldung in UI

**Status-Meldung:**
```
⚠️ Plugin "MQTT_Client_1" deaktiviert
   Grund: Spam-Schutz ausgelöst (650 pps)
   Letzte Aktivität: 14:32:15
   [Manuell reaktivieren] [Logs anzeigen]
```

### 10.4 Administrative Test-Funktion
**Ziele:**
- "Disconnect"-Button pro Verbindung
- Trennt Modul vom Router (ohne zu beenden)
- Nützlich für Fehlerdiagnose
- Reconnect-Button zur Wiederverbindung

---

## Phase 11: Node-RED Integration (🔄 In Planung)

### 11.1 MQTT-Bridge für Node-RED
**Status:** ❌ Nicht implementiert

**Ziele:**
- Spiegelung des gesamten Datenstroms auf lokalen MQTT-Broker
- Node-RED nutzt Standard-MQTT-Nodes
- Topic-Struktur: `smarthome/plc/MAIN/temperature`

**Datenfluss:**
```
DataGateway → route_data() → MQTT-Publish
                           ↓
                      Node-RED Subscribe
                           ↓
                    Logik-Verarbeitung
                           ↓
                      MQTT-Publish
                           ↓
                DataGateway ← route_data()
```

### 11.2 Native Node-RED Nodes (Zukunft)
**Ziele:**
- Custom Node-Palette für Node-RED
- Direkter API-Zugriff ohne MQTT
- Optimierte Performance
- Widget-Integration

### 11.3 Dashboard-Integration
**Ziele:**
- IFrame-Embedding von Node-RED-Dashboards
- Einheitliche Authentifizierung
- Nahtlose UI-Integration

---

## Phase 12: Testing & Dokumentation (🔄 In Planung)

### 12.1 Integration-Tests
**Ziele:**
- Unit-Tests für alle neuen Module
- Integration-Tests für Datenfluss-Szenarien
- Performance-Tests (Spam-Schutz, CPU-Limits)
- Stress-Tests mit Multi-Instance-Betrieb

### 12.2 Dokumentation
**Ziele:**
- README.md aktualisieren
- CHANGELOG.md für v4.6.0 erstellen
- API-Dokumentation (Swagger/OpenAPI)
- Plugin-Entwickler-Guide
- Installations-Anleitung für verschiedene Plattformen

---

## Entwicklungsphasen Übersicht

| Phase | Komponente | Status | Priorität |
|-------|-----------|--------|-----------|
| 1 | Router-Engine | ❌ | 🔴 Hoch |
| 2 | Connection Manager | ❌ | 🔴 Hoch |
| 3 | Bluetooth/BMS | ❌ | 🟡 Mittel |
| 4 | TreeView UI | ❌ | 🟡 Mittel |
| 5 | Widget CRUD | ❌ | 🔴 Hoch |
| 6 | Plugin-Manager | ❌ | 🟡 Mittel |
| 7 | Instanzen-Manager | ❌ | 🔴 Hoch |
| 8 | Lifecycle-Management | ❌ | 🔴 Hoch |
| 9 | Sentry/Health | ❌ | 🟡 Mittel |
| 10 | CPU-Throttling/Spam | ❌ | 🔴 Hoch |
| 11 | Node-RED Integration | ❌ | 🟢 Niedrig |
| 12 | Testing/Docs | ❌ | 🟡 Mittel |

---

## Ergebnis v4.6.0

Durch v4.6.0 entsteht ein **Edge-Betriebssystem für industrielle Hausautomatisierung**:

✅ **Hardware-Unabhängigkeit:**
- Läuft auf Windows, Linux, Docker
- Keine festen Pfade oder Hardware-IDs

✅ **Modular & Erweiterbar:**
- Plugin-System für neue Protokolle
- Einfache Integration zusätzlicher BMS/Wechselrichter

✅ **Industriell & Stabil:**
- CPU-Limitierung wie bei TwinCAT
- Spam-Schutz und Circuit Breaker
- Health-Monitoring und Auto-Recovery

✅ **Benutzerfreundlich:**
- ioBroker-Style Admin-UI
- Drag-and-Drop Widget-Editor
- Keine Programmierung erforderlich

✅ **Produktionsreif:**
- GitHub-Ready
- Umfassende Dokumentation
- Plugin-Marketplace-Vorbereitung

---

## Langfristige Vision (v6.0+)

- **Machine Learning Integration:** Anomalie-Erkennung, Vorhersage-Modelle
- **Cloud-Connector:** Optional Cloud-Backup und Remote-Access
- **Mobile App:** Native iOS/Android App
- **HA-Cluster:** Hochverfügbarkeit mit mehreren Instanzen
- **Edge-AI:** Lokale Bildverarbeitung, Objekterkennung
- **Professional Support:** Community + Enterprise-Support-Optionen

---

**Stand:** 2026-01-04
**Aktuelle Version:** 4.7.x
**Zielversion:** 4.6.0
**Erwartete Fertigstellung:** Q2 2026
