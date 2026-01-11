# Changelog - TwinCAT SmartHome Web-HMI

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [4.5.3] - 2026-01-04

### 🎉 Major Features

#### DatabaseLogger - SQLite-basiertes Logging-System
**Ersetzt print() durch strukturiertes, persistentes Logging**

- **Neue Datei**: `modules/core/database_logger.py`
- **Features**:
  - SQLite-Handler für Python `logging` Modul
  - Speichert WARNING, ERROR, CRITICAL persistent in `config/system_logs.db`
  - Auto-Cleanup (max 1000 Einträge, FIFO)
  - Thread-safe Operations
  - Performance-Index auf Timestamp
  - Console-Handler bleibt für INFO/DEBUG

- **Integration**:
  - Automatischer Setup in `start_web_hmi.py` (Zeile 23-42)
  - Logging-Level konfigurierbar
  - Keine Migration erforderlich (backward-compatible)

#### ServiceManager - Hot-Restart ohne Reboot
**Ermöglicht Neustart des Services ohne Shell-Zugriff**

- **Neue Datei**: `modules/core/service_manager.py`
- **Features**:
  - Windows: subprocess mit DETACHED_PROCESS
  - Linux/Docker: os.execv (behält PID)
  - Verzögerter Restart (um HTTP-Response zu senden)
  - Restart-Info (Platform, PID, Args)
  - `--restarted` Flag für Logging

- **API** (web_manager.py:1031-1064):
  - `POST /api/admin/service/restart` - Startet Service neu
  - `GET /api/admin/service/info` - Service-Informationen

#### SerialLink Abstract Base - Plugin-System für serielle Kommunikation
**Vorbereitung für RS485/Modbus/KNX-Plugins**

- **Neue Datei**: `modules/gateway/serial_link.py`
- **Features**:
  - Abstrakte Basisklasse für alle seriellen Protokolle
  - Thread-safe Operations (`_lock`)
  - Statistik-Tracking (reads/writes/errors)
  - Context Manager Support (`with` statement)
  - Beispiel-Implementierung: `ModbusRTULink`

- **Unterstützte Protokolle (zukünftig)**:
  - Modbus RTU/ASCII
  - RS485 Master/Slave
  - KNX TP
  - DMX512

#### Widget Subscription Sync - Behebt UNKNOWN-Variablen
**Synchronisiert Widget-Variablen automatisch mit PLC beim Start**

- **Geändert**: `modules/gateway/data_gateway.py`
- **Neue Methode**: `sync_widget_subscriptions()` (Zeile 321-383)
- **Aufruf**: Automatisch in `initialize()` (Zeile 95)

- **Funktionsweise**:
  - Lädt alle Widget-Konfigurationen beim Start
  - Liest alle gebundenen PLC-Variablen vorab
  - Initialisiert PLC-Cache für sofortige Verfügbarkeit
  - Behebt: UNKNOWN-Variable-Problem

- **Auswirkung**:
  - Widgets zeigen sofort korrekte Werte
  - Keine Verzögerung bei erster Anzeige
  - Reduziert initiale Latenz

#### Admin API - System-Logs & Service-Management
**Backend-API für Logs und Service-Verwaltung**

- **Geändert**: `modules/gateway/web_manager.py` (Zeile 985-1064)

- **Neue Endpoints**:
  - `GET /api/admin/logs?limit=100` - Holt System-Logs aus Datenbank
  - `POST /api/admin/logs/clear` - Löscht alte Log-Einträge
  - `POST /api/admin/service/restart` - Startet Service neu
  - `GET /api/admin/service/info` - Service-Informationen

- **Integration**:
  - Automatischer Import von DatabaseLogger
  - Automatischer Import von ServiceManager
  - Fehlerbehandlung für fehlende Module

### 🔧 Improvements

- **Startup-Meldung**: Zeigt v4.5.3 statt v4.5
- **Restart-Indikator**: Zeigt `✅ Service neu gestartet (Hot-Reload)` bei Restart
- **Logging-Format**: Strukturiert und konsistent

### 🐛 Bug Fixes

- **Widget UNKNOWN-Variablen**: Behoben durch Widget Subscription Sync
- **Logging Print-Spam**: Ersetzt durch DatabaseLogger

### 🗑️ Deprecated

- **print() für Logging**: Sollte durch `logging.getLogger()` ersetzt werden
  - print() funktioniert weiterhin, ist aber nicht mehr empfohlen
  - Neue Module sollten logging verwenden

### ⚠️ Breaking Changes

**KEINE** - Alle Änderungen sind backward-compatible!

### 📦 New Files

```
modules/core/database_logger.py       (240 Zeilen)
modules/core/service_manager.py       (130 Zeilen)
modules/gateway/serial_link.py        (250 Zeilen)
UPGRADE_453_COMPLETE.md               (550 Zeilen)
```

### 📝 Modified Files

```
modules/gateway/data_gateway.py       (+70 Zeilen)
modules/gateway/web_manager.py        (+80 Zeilen)
start_web_hmi.py                      (+18 Zeilen)
CHANGELOG.md                          (dieser Eintrag)
```

### 📊 Code Statistics

- **Neu**: ~620 Zeilen
- **Geändert**: ~170 Zeilen
- **Gesamt**: ~790 Zeilen Code

---

## [4.5.0] - 2026-01-04

### 🎉 Major Features

#### Widget Configuration & Variable Binding System
**Added complete widget management system for dynamic UI configuration**

- **Backend API** (web_manager.py:596-783)
  - `GET /api/widgets` - Retrieve all widget configurations
  - `POST /api/widgets` - Create new widget
  - `PUT /api/widgets/<id>` - Update widget configuration
  - `DELETE /api/widgets/<id>` - Delete widget
  - `POST /api/widgets/<id>/bindings` - Bind Gateway variables to widgets
  - `GET /api/widgets/values` - Get live values of all bound variables

- **Frontend Features**
  - New "Widgets" navigation page
  - Widget Editor Modal with:
    - Widget type selection (Switch/Slider/Gauge/Text)
    - Page assignment (Dashboard/Lighting/Climate/Energy)
    - Variable binding interface
    - PLC type selector (BOOL/INT/REAL/STRING)
    - Symbol browser integration
    - Test connection before saving
  - Persistent storage via Config Manager
  - Dark theme support

- **JavaScript Implementation** (app.js:1716-1979)
  - `loadWidgetsPage()` - Main widget page loader
  - `renderWidgetList()` - Dynamic widget list rendering
  - `saveWidget()` - CREATE/UPDATE widget operations
  - `deleteWidget()` - Delete widget with confirmation
  - `testVariableBinding()` - Test variable connection
  - `browseSymbols()` - Integration with Symbol Browser

#### Gateway Monitor & Analytics Dashboard
**Real-time data flow visualization and performance monitoring**

- **Backend API** (web_manager.py:785-940)
  - `GET /api/monitor/dataflow` - Real-time data flow statistics
  - `GET /api/monitor/latency` - PLC/WebSocket latency measurement
  - `POST /api/monitor/export` - Export monitoring data (JSON/CSV)
  - `GET /api/monitor/trace` - Trace log (foundation for future trace mode)

- **Frontend Features**
  - New "Monitor" navigation page
  - Real-time statistics cards:
    - Active Connections
    - PLC Reads Counter
    - WebSocket Clients
    - Error Rate Calculation
  - Data Flow Visualization (Source → Gateway → Destination)
  - Latency Measurement Tool (without cache for real values)
  - Export Functionality (JSON/CSV download)
  - Auto-Refresh Toggle (2-second interval)
  - Manual Refresh Button

- **JavaScript Implementation** (app.js:1982-2275)
  - `loadMonitorPage()` - Dashboard initialization
  - `updateMonitorStats()` - Live statistics updates
  - `updateDataFlowVisualization()` - Flow diagram updates
  - `measureLatency()` - Round-trip time measurement
  - `exportMonitorData()` - Data export handler
  - `startMonitorAutoRefresh()` / `stopMonitorAutoRefresh()` - Auto-refresh control

#### Multi-PLC Management API
**Support for managing multiple PLC configurations**

- **Backend API** (web_manager.py:447-593)
  - `GET /api/admin/plcs` - Get all PLC configurations
  - `GET /api/admin/plcs/<id>` - Get single PLC configuration
  - `POST /api/admin/plcs` - Create new PLC configuration
  - `PUT /api/admin/plcs/<id>` - Update PLC configuration
  - `DELETE /api/admin/plcs/<id>` - Delete PLC configuration
  - `POST /api/admin/plcs/<id>/set-active` - Set active PLC
  - `POST /api/admin/plcs/<id>/upload-tpy` - Upload TPY file for PLC
  - `POST /api/admin/plcs/cleanup-tpy` - Clean up unused TPY files

- **PLC Config Manager** (modules/gateway/plc_config_manager.py)
  - Persistent JSON-based storage
  - Separate TPY file management per PLC
  - Active PLC selection
  - Statistics (total PLCs, active PLCs, TPY file sizes)

### 🐛 Critical Bug Fixes

#### Security: Removed Hardcoded AMS NetID
**Fixed security vulnerability where any AMS NetID was accepted**

- **Problem**: Hardcoded AMS NetID `192.168.2.162.1.1` in `plc_communication.py:46`
- **Impact**: System accepted connections with incorrect AMS NetIDs
- **Solution**:
  - Changed `ams_net_id: '192.168.2.162.1.1'` → `ams_net_id: None`
  - Added validation in `connect()` method (lines 80-85)
  - Clear error messages directing users to Web-UI or `configure()` method
  - Each instance must now explicitly configure AMS NetID

#### Connection Validation
**Added robust PLC connection state validation**

- Prevents connection attempts without configured AMS NetID
- Provides user-friendly error messages
- Guides users to configuration options (Web-UI or programmatic)

### 🔧 Improvements

#### PLC Communication Module v1.1.0
**Enhanced error handling and reconnection logic**

- Increased `max_errors` from 5 to 20 (prevents reconnect spam)
- Added reconnect cooldown (30 seconds)
- Better error logging (first 3 errors only)
- Reset error counter on successful operations
- Enhanced statistics tracking

#### PLC Symbol Parser v2.0.0
**Two-phase parsing for complete symbol extraction**

- **Phase 1**: Parse DataType definitions (struct members)
- **Phase 2**: Parse Program variables (MAIN.* variables)
- Better category detection (Variable/FunctionBlock/Array/ProgramVariable)
- Hierarchical tree structure building
- Comment extraction from XML
- Symbol path generation

### 📦 New Modules

- **plc_config_manager.py** - Multi-PLC configuration management
- **plc_symbol_parser.py** - TPY file parser for symbol extraction

### 📄 Documentation

- **BUGFIX_REPORT_20260104.md** - Detailed report of critical bug fixes
- **MULTI_PLC_API.md** - Multi-PLC Management API integration guide
- **MONITOR_DASHBOARD_COMPLETE.md** - Monitor Dashboard implementation documentation

### 🔄 Changed

- **web_manager.py**: Added 6 major API endpoint groups (340+ lines)
- **app.js**: Added Widget and Monitor functionality (560+ lines)
- **index.html**: Added Widgets and Monitor navigation pages
- **start_web_hmi.py**: Updated initialization flow

### 🗑️ Deprecated

None

### ⚠️ Breaking Changes

**AMS NetID Configuration**
- No default AMS NetID anymore
- **Migration**: Configure AMS NetID via Web-UI (Setup page) or call `plc.configure(ams_net_id='...')` before connecting
- **Impact**: Existing deployments will fail to connect until AMS NetID is explicitly configured

---

## [4.0.0] - 2025-12-XX

### 🎉 Major Features

#### Modular Plugin Architecture
- BaseModule abstract class
- Module Manager with dependency resolution
- Hot-reload capabilities
- Version compatibility checks

#### Data Gateway Core
- Multi-protocol abstraction (PLC/MQTT/HTTP)
- Real-time data streaming
- Blob storage for binary data (images/video)
- Platform detection (Windows/Linux/Docker)

#### Web-HMI Frontend
- Responsive Tailwind CSS design
- Dark theme support
- Real-time WebSocket updates
- Dynamic page routing

### 🔧 Core Modules

- **config_manager** - JSON-based persistent configuration
- **plc_communication** - TwinCAT ADS integration via pyads
- **mqtt_integration** - MQTT client with topic subscription
- **data_gateway** - Multi-protocol data aggregation
- **web_manager** - Flask + SocketIO web server
- **stream_manager** - Video stream management (RTSP/HTTP)

---

## [3.x.x] - Legacy Versions

Earlier versions were monolithic and not modular. Version 4.0.0 represents a complete architectural rewrite.

---

## Roadmap

### Planned for v4.6.0

#### Serial-Link Abstraction
- Abstract class `SerialLink` for RS485 communication
- Plugin system for serial protocols
- Pyserial integration

#### Admin Restart Functionality
- Windows: `taskkill /PID` + restart logic
- Linux: `systemctl restart` integration
- Docker: Container restart API

#### Enhanced Monitor Dashboard
- Trace mode for detailed packet analysis
- Sankey diagram visualization (D3.js/Chart.js)
- Historical data storage (SQLite integration)
- Alarm system with threshold-based alerts

#### Full-Stack Plugin System
- UI component injection via plugins
- Plugin marketplace/registry
- Sandboxed plugin execution
- Plugin dependency management

### Planned for v5.0.0

#### Container Orchestration
- Docker Compose templates
- Kubernetes deployment
- Multi-instance coordination
- Shared configuration storage

#### Advanced Visualization
- Custom widget library
- Drag-and-drop dashboard builder
- Chart.js integration for historical data
- Floor plan integration

---

## Notes

### Platform Compatibility

**Windows**
- Tested on Windows 11
- Requires `python -X utf8` for UTF-8 encoding
- TwinCAT ADS native support

**Linux**
- Full support via ADS router
- Systemd integration recommended
- GPU acceleration via VAAPI

**Docker**
- Multi-platform images (amd64/arm64)
- Hardware acceleration pass-through
- Volume-based configuration

### Migration Guide

#### v3.x → v4.0.0
1. Refactor code to use BaseModule
2. Update configuration to JSON format
3. Migrate routes to new API structure

#### v4.0.0 → v4.5.0
1. Remove hardcoded AMS NetID from custom code
2. Configure AMS NetID via Web-UI or API
3. Update widget configurations to use new binding system

---

**Contributors**: Claude Sonnet 4.5, TwinCAT Team
**License**: Proprietary
**Repository**: Internal TwinCAT SmartHome Project
