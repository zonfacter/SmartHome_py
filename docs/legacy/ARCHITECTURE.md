# TwinCAT SmartHome Web-HMI - Architecture Documentation

**Version**: 4.5.0
**Date**: 2026-01-04
**Author**: TwinCAT Team, Claude Sonnet 4.5

---

## Table of Contents

1. [System Overview](#system-overview)
2. [Architectural Principles](#architectural-principles)
3. [Core Architecture](#core-architecture)
4. [Module System](#module-system)
5. [Data Flow](#data-flow)
6. [API Architecture](#api-architecture)
7. [Frontend Architecture](#frontend-architecture)
8. [Multi-PLC Support](#multi-plc-support)
9. [Security Architecture](#security-architecture)
10. [Deployment Architecture](#deployment-architecture)
11. [Performance Considerations](#performance-considerations)
12. [Future Architecture](#future-architecture)

---

## System Overview

### Purpose

The TwinCAT SmartHome Web-HMI is a **modular, multi-protocol IoT Gateway** with a web-based Human-Machine Interface designed for industrial and smart home automation.

### Key Characteristics

- **Modular Plugin Architecture**: Hot-swappable modules with dependency management
- **Multi-Protocol**: Unified abstraction layer for PLC (ADS), MQTT, HTTP, Serial
- **Real-Time**: WebSocket-based bidirectional communication
- **Scalable**: Multi-instance support with separate configurations
- **Platform-Agnostic**: Windows, Linux, Docker deployment

### Technology Stack

**Backend**
- Python 3.13+
- Flask (Web Framework)
- Flask-SocketIO (WebSocket)
- pyads (TwinCAT ADS Communication)
- paho-mqtt (MQTT Client)

**Frontend**
- Vanilla JavaScript (ES6+)
- Tailwind CSS (Utility-first CSS)
- Lucide Icons
- Socket.IO Client

**Data Formats**
- JSON (Configuration, API)
- XML (TPY Symbol Files)
- CSV (Export)

---

## Architectural Principles

### 1. Separation of Concerns

Each module has a single, well-defined responsibility:
- **plc_communication**: Hardware protocol layer
- **data_gateway**: Protocol abstraction & aggregation
- **web_manager**: HTTP/WebSocket interface
- **config_manager**: Persistent configuration

### 2. Dependency Injection

Modules receive dependencies via `initialize(app_context)`:
```python
def initialize(self, app_context):
    self.plc = app_context.module_manager.get_module('plc_communication')
    self.config = app_context.module_manager.get_module('config_manager')
```

### 3. Event-Driven Communication

- **SocketIO**: Real-time events from backend to frontend
- **REST API**: Request/response for CRUD operations
- **Module Events**: Internal event bus (future)

### 4. Stateless Design

- Server is stateless (except WebSocket connections)
- Configuration persisted to JSON files
- No session state on server side

### 5. Defense in Depth

- Input validation at API layer
- Type conversion at protocol layer
- Connection validation before operations
- Error isolation per module

---

## Core Architecture

### High-Level Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                         Frontend                             │
│  ┌────────────┐  ┌────────────┐  ┌──────────────────┐      │
│  │  HTML/CSS  │  │  app.js    │  │  socket_handler  │      │
│  └────────────┘  └────────────┘  └──────────────────┘      │
└─────────────────────────────────────────────────────────────┘
                            ▲
                            │ HTTP / WebSocket
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                      Web Manager                             │
│  ┌──────────────┐  ┌──────────────┐  ┌─────────────────┐   │
│  │  Flask REST  │  │  SocketIO    │  │  Route Handlers │   │
│  └──────────────┘  └──────────────┘  └─────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                            ▲
                            │ Module API
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                     Data Gateway                             │
│  ┌────────────┐  ┌────────────┐  ┌──────────────────┐      │
│  │  Protocol  │  │  Blob      │  │  Telemetry       │      │
│  │  Abstraction│  │  Storage   │  │  Aggregation     │      │
│  └────────────┘  └────────────┘  └──────────────────┘      │
└─────────────────────────────────────────────────────────────┘
                            ▲
                ┌───────────┼────────────┐
                ▼           ▼            ▼
       ┌──────────────┐ ┌────────┐ ┌─────────┐
       │     PLC      │ │  MQTT  │ │ Serial  │
       │ Communication│ │ Client │ │ (Future)│
       └──────────────┘ └────────┘ └─────────┘
                ▲           ▲            ▲
                │           │            │
         ┌──────┴─────┬─────┴─────┬──────┴──────┐
         ▼            ▼           ▼             ▼
    ┌────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐
    │TwinCAT │  │  MQTT   │  │  HTTP   │  │ RS485   │
    │  PLC   │  │ Broker  │  │  APIs   │  │ Devices │
    └────────┘  └─────────┘  └─────────┘  └─────────┘
```

---

## Module System

### BaseModule Abstract Class

All modules inherit from `BaseModule`:

```python
class BaseModule(ABC):
    NAME: str          # Unique module identifier
    VERSION: str       # Semantic version
    DESCRIPTION: str   # Human-readable description
    AUTHOR: str        # Author/Team name
    DEPENDENCIES: List[str] = []  # Required modules

    @abstractmethod
    def initialize(self, app_context):
        """Called when module is loaded"""
        pass

    def shutdown(self):
        """Called when module is unloaded"""
        pass
```

### Module Manager

**Responsibilities**:
- Module registration
- Dependency resolution
- Lifecycle management
- Version checking

**Module Loading Flow**:
```
1. Register all modules
2. Resolve dependencies (topological sort)
3. Call initialize() in dependency order
4. Store module references
5. Provide get_module() access
```

### Core Modules

#### 1. Config Manager
**Location**: `modules/core/config_manager.py`
**Purpose**: Persistent JSON configuration storage

```python
# Key Features
- get_config_value(key, default)
- set_config_value(key, value)
- save_config()
- Platform-aware paths (/config or AppData)
```

#### 2. PLC Communication
**Location**: `modules/core/plc_communication.py`
**Purpose**: TwinCAT ADS protocol implementation

```python
# Key Features
- connect() / disconnect()
- read_by_name(variable, plc_type)
- write_by_name(variable, value, plc_type)
- toggle_bool() / pulse()
- Auto-reconnect with cooldown
- Variable caching (100ms)
- Error tracking & statistics
```

**v1.1.0 Improvements**:
- Removed hardcoded AMS NetID
- Increased error tolerance (max_errors: 20)
- Reconnect cooldown (30s)
- Better logging

#### 3. Data Gateway
**Location**: `modules/gateway/data_gateway.py`
**Purpose**: Multi-protocol abstraction layer

```python
# Key Features
- register_source(name, type, get_fn, set_fn)
- get_value(source, key)
- set_value(source, key, value)
- Blob storage for binary data (images, video)
- Platform capabilities detection
- Telemetry aggregation
```

#### 4. Web Manager
**Location**: `modules/gateway/web_manager.py`
**Purpose**: Flask + SocketIO web server

```python
# Key Features
- REST API endpoints
- WebSocket event handling
- Static file serving
- Client connection tracking
- Symbol parser integration
- Widget configuration API
- Monitor dashboard API
- Multi-PLC management API
```

#### 5. MQTT Integration
**Location**: `modules/integration/mqtt_integration.py`
**Purpose**: MQTT client for broker communication

```python
# Key Features
- connect(broker, port, user, pass)
- subscribe(topic, callback)
- publish(topic, payload)
- Automatic reconnection
- Topic value caching
```

#### 6. Stream Manager
**Location**: `modules/gateway/stream_manager.py`
**Purpose**: Video stream management (RTSP, HTTP)

```python
# Key Features
- add_stream(name, url, type)
- get_snapshot(stream_id)
- HLS segment generation
- GPU acceleration (Intel QuickSync, VAAPI)
```

---

## Data Flow

### 1. PLC Data Flow

```
┌──────────────┐
│  TwinCAT PLC │
└───────┬──────┘
        │ ADS Protocol
        ▼
┌──────────────────┐
│ plc_communication│  read_by_name()
│  (100ms cache)   │  write_by_name()
└───────┬──────────┘
        │
        ▼
┌──────────────────┐
│  data_gateway    │  register_source('plc', ...)
│  (protocol       │  get_value('plc', 'MAIN.bLight1')
│   abstraction)   │
└───────┬──────────┘
        │
        ▼
┌──────────────────┐
│  web_manager     │  API: /api/plc/read
│  (REST API)      │  SocketIO: telemetry_update
└───────┬──────────┘
        │ HTTP/WebSocket
        ▼
┌──────────────────┐
│   Frontend       │  app.readPLC()
│   (JavaScript)   │  socket.on('telemetry_update')
└──────────────────┘
```

### 2. Widget Binding Flow

```
┌──────────────────┐
│  User creates    │
│  Widget in UI    │
└───────┬──────────┘
        │ POST /api/widgets
        ▼
┌──────────────────┐
│  web_manager     │  Stores in Config Manager
│  saveWidget()    │  { id, type, bindings: {
└───────┬──────────┘    value: { variable: 'MAIN.bLight1' }
        │               }}
        ▼
┌──────────────────┐
│  config_manager  │  Persists to config.json
│  save_config()   │
└──────────────────┘

# On Page Load:
GET /api/widgets       → Returns widget configs
GET /api/widgets/values → Reads PLC variables
                         → Returns live values
```

### 3. Monitor Dashboard Flow

```
┌──────────────────┐
│  Frontend        │  Auto-refresh every 2s
│  loadMonitorData()│
└───────┬──────────┘
        │ GET /api/monitor/dataflow
        ▼
┌──────────────────┐
│  web_manager     │  Collects from all modules:
│  get_dataflow_   │  - plc.get_connection_status()
│  stats()         │  - mqtt.connected
└───────┬──────────┘  - gateway.blob_cache
        │             - websocket.connected_clients
        │
        ▼
┌─────────────────────────────────────┐
│  Aggregated Stats JSON              │
│  {                                  │
│    protocols: {                     │
│      plc: { reads, writes, errors } │
│      mqtt: { subscriptions }        │
│    },                               │
│    active_connections: 2,           │
│    websocket: { clients: 3 }        │
│  }                                  │
└───────┬─────────────────────────────┘
        │
        ▼
┌──────────────────┐
│  Frontend        │  updateMonitorStats()
│  (Dashboard)     │  updateDataFlowVisualization()
└──────────────────┘
```

---

## API Architecture

### REST API Endpoints

**Status & System**
```
GET  /api/status              - System status
GET  /api/dependencies        - Module dependencies
GET  /api/capabilities        - Platform capabilities
```

**PLC Control**
```
POST /api/plc/connect         - Connect to PLC
POST /api/plc/disconnect      - Disconnect from PLC
GET  /api/plc/status          - PLC connection status
POST /api/plc/read            - Read variable
POST /api/plc/write           - Write variable
POST /api/plc/toggle          - Toggle boolean
POST /api/plc/pulse           - Send pulse
```

**PLC Symbols**
```
GET  /api/plc/symbols         - Get symbol list (with search/filter)
POST /api/plc/symbols/upload  - Upload TPY file
GET  /api/plc/symbols/tree    - Get hierarchical tree
```

**Widget Configuration**
```
GET    /api/widgets           - Get all widgets
POST   /api/widgets           - Create widget
PUT    /api/widgets/<id>      - Update widget
DELETE /api/widgets/<id>      - Delete widget
POST   /api/widgets/<id>/bindings - Bind variable
GET    /api/widgets/values    - Get live values
```

**Monitor Dashboard**
```
GET  /api/monitor/dataflow    - Real-time statistics
GET  /api/monitor/latency     - Measure latency
POST /api/monitor/export      - Export data (JSON/CSV)
GET  /api/monitor/trace       - Trace log (future)
```

**Multi-PLC Management**
```
GET    /api/admin/plcs             - Get all PLCs
GET    /api/admin/plcs/<id>        - Get PLC config
POST   /api/admin/plcs             - Create PLC
PUT    /api/admin/plcs/<id>        - Update PLC
DELETE /api/admin/plcs/<id>        - Delete PLC
POST   /api/admin/plcs/<id>/set-active - Set active PLC
POST   /api/admin/plcs/<id>/upload-tpy - Upload TPY
POST   /api/admin/plcs/cleanup-tpy - Cleanup unused TPY
```

**MQTT Control**
```
GET  /api/mqtt/status         - MQTT status
POST /api/mqtt/connect        - Connect to broker
POST /api/mqtt/disconnect     - Disconnect
POST /api/mqtt/subscribe      - Subscribe to topic
POST /api/mqtt/publish        - Publish message
```

**Gateway Data**
```
GET  /api/gateway/values      - Get all telemetry values
POST /api/gateway/set         - Set source value
GET  /api/blob/<blob_id>      - Get blob data
```

**Streams**
```
GET  /api/streams             - List streams
POST /api/streams             - Add stream
GET  /api/streams/<id>/snapshot - Get snapshot
GET  /api/streams/<id>/hls/playlist.m3u8 - HLS playlist
```

### WebSocket Events

**Client → Server**
```
request_telemetry            - Request telemetry update
ping                          - Keepalive ping
```

**Server → Client**
```
telemetry_update             - { source, data }
system_capabilities          - { platform, gpu, ... }
mqtt_message                 - { topic, payload }
plc_status_changed           - { connected: bool }
error                        - { message: str }
```

---

## Frontend Architecture

### File Structure

```
web/
├── templates/
│   └── index.html          # Single-page application
└── static/
    ├── css/
    │   └── styles.css      # Custom CSS (Tailwind loaded via CDN)
    └── js/
        ├── app.js          # Main application class
        └── socket_handler.js # WebSocket management
```

### SmartHomeApp Class

**Responsibilities**:
- Page routing
- State management
- API communication
- Event handling

**Key Methods**:
```javascript
class SmartHomeApp {
    constructor()
    showPage(pageName)           // Route to page

    // Dashboard
    loadDashboard()
    updateSystemStatus()
    updateDependencies()

    // PLC Control
    connectPLC()
    disconnectPLC()
    readPLC()
    writePLC()
    togglePLC()

    // Symbol Browser
    loadSymbols()
    searchSymbols()
    renderSymbolList()

    // Widget Management
    loadWidgetsPage()
    saveWidget()
    deleteWidget()
    testVariableBinding()

    // Monitor Dashboard
    loadMonitorPage()
    measureLatency()
    exportMonitorData()
    startMonitorAutoRefresh()

    // Setup
    loadSetupPage()
    savePLCConfig()
    saveMQTTConfig()
}
```

### SocketHandler Class

**Responsibilities**:
- WebSocket connection management
- Event subscription
- Automatic reconnection
- Telemetry caching

**Key Methods**:
```javascript
class SocketHandler {
    constructor()
    connect()
    disconnect()
    on(event, callback)        // Subscribe to event
    emit(event, data)          // Send event
    requestTelemetry()         // Request data update
}
```

### State Management

**Approach**: Minimal client-side state
- Server is source of truth
- State fetched on page load
- Real-time updates via WebSocket
- No client-side state persistence

**State Categories**:
1. **System State**: Server status, capabilities (read-only)
2. **Connection State**: PLC/MQTT connection status (mutable)
3. **Telemetry State**: Live sensor values (real-time)
4. **Configuration State**: Widget configs, settings (persistent)

---

## Multi-PLC Support

### Architecture

```
┌────────────────────────────────────────┐
│         PLC Config Manager             │
│  ┌──────────────────────────────────┐  │
│  │  config.json                     │  │
│  │  {                               │  │
│  │    "active_plc": "plc_1",        │  │
│  │    "plcs": {                     │  │
│  │      "plc_1": {                  │  │
│  │        name: "Production PLC",   │  │
│  │        ams_net_id: "...",        │  │
│  │        tpy_file: "plc_1_*.tpy"   │  │
│  │      }                            │  │
│  │    }                             │  │
│  │  }                               │  │
│  └──────────────────────────────────┘  │
└────────────────────────────────────────┘
                  │
        ┌─────────┴─────────┐
        ▼                   ▼
┌───────────────┐   ┌───────────────┐
│   plc_data/   │   │   plc_data/   │
│ plc_1_xyz.tpy │   │ plc_2_abc.tpy │
└───────────────┘   └───────────────┘
```

### TPY File Management

**Naming Convention**: `{plc_id}_{original_filename}.tpy`

**Storage**:
- Directory: `project_root/plc_data/`
- One TPY per PLC configuration
- Cleanup function removes orphaned files

**Symbol Parser Integration**:
```python
# web_manager.py get_plc_symbols()
if self.plc_config_manager:
    active_plc_id = self.plc_config_manager.configs.get('active_plc')
    tpy_file = self.plc_config_manager.get_tpy_path(active_plc_id)
else:
    # Fallback
    tpy_file = 'plc_data/TwinCAT_Project.tpy'
```

### Active PLC Switching

**Flow**:
1. User selects PLC in Admin UI
2. `POST /api/admin/plcs/<id>/set-active`
3. Config Manager updates `active_plc`
4. Symbol parser cache invalidated
5. Next symbol request uses new TPY file

---

## Security Architecture

### Authentication & Authorization

**Current Status**: No authentication (local network only)

**Planned (v4.6.0)**:
- OAuth2/JWT token-based auth
- Role-based access control (Admin/Operator/Viewer)
- API key management for external integrations

### Input Validation

**Layers**:
1. **Frontend**: Basic type checking
2. **API Layer**: Required field validation
3. **Module Layer**: Type conversion, range checks

**Example**:
```python
# web_manager.py create_widget()
required = ['type', 'title']
for field in required:
    if field not in data:
        return jsonify({'error': f'Feld {field} erforderlich'}), 400
```

### Connection Security

**AMS NetID Validation**:
- No hardcoded defaults (v4.5.0)
- Explicit configuration required
- Connection attempt rejected if NetID not set

**Error Isolation**:
- Module failures don't crash server
- Try-catch blocks around external calls
- Graceful degradation

### Data Sanitization

**PLC Variable Names**:
- No SQL injection risk (no SQL database)
- XML escaped in TPY parser
- JSON encoded in API responses

**File Uploads**:
- TPY files: Extension check (`.tpy` only)
- Size limits (future)
- Virus scanning (future)

---

## Deployment Architecture

### Local Development

```
python -X utf8 start_web_hmi.py --port 5001
```

**Requirements**:
- Python 3.13+
- TwinCAT ADS router (for PLC communication)
- MQTT broker (optional)

### Production Deployment

#### Windows Service

```powershell
# NSSM (Non-Sucking Service Manager)
nssm install TwinCATWebHMI "C:\Python313\python.exe"
nssm set TwinCATWebHMI AppParameters "-X utf8 C:\path\to\start_web_hmi.py --port 80"
nssm start TwinCATWebHMI
```

#### Linux Systemd

```ini
# /etc/systemd/system/twincat-webhmi.service
[Unit]
Description=TwinCAT SmartHome Web-HMI
After=network.target

[Service]
Type=simple
User=smarthome
WorkingDirectory=/opt/twincat-webhmi
Environment="PYTHONPATH=/opt/twincat-webhmi"
ExecStart=/usr/bin/python3 start_web_hmi.py --port 80
Restart=always

[Install]
WantedBy=multi-user.target
```

#### Docker Deployment

```dockerfile
FROM python:3.13-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 5000
ENV PYTHONIOENCODING=utf-8

CMD ["python", "-X", "utf8", "start_web_hmi.py", "--host", "0.0.0.0"]
```

**Docker Compose**:
```yaml
version: '3.8'
services:
  webhmi:
    build: .
    ports:
      - "80:5000"
    volumes:
      - ./config:/app/config      # Persistent config
      - ./plc_data:/app/plc_data  # TPY files
    environment:
      - TZ=Europe/Berlin
    restart: unless-stopped
```

### Multi-Instance Architecture

**Scenario**: Multiple instances for different buildings/plants

```
┌────────────────┐   ┌────────────────┐   ┌────────────────┐
│   Instance 1   │   │   Instance 2   │   │   Instance 3   │
│  Building A    │   │  Building B    │   │  Building C    │
│  Port 5001     │   │  Port 5002     │   │  Port 5003     │
│  Config: /cfg1 │   │  Config: /cfg2 │   │  Config: /cfg3 │
└────────┬───────┘   └────────┬───────┘   └────────┬───────┘
         │                    │                    │
         └────────────────────┼────────────────────┘
                              │
                    ┌─────────┴─────────┐
                    │  Reverse Proxy    │
                    │  (nginx/traefik)  │
                    │  https://hmi.com  │
                    └───────────────────┘
```

**nginx Configuration**:
```nginx
upstream webhmi_building_a {
    server localhost:5001;
}
upstream webhmi_building_b {
    server localhost:5002;
}

server {
    listen 80;
    server_name hmi-building-a.company.com;
    location / {
        proxy_pass http://webhmi_building_a;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

---

## Performance Considerations

### Caching Strategy

**PLC Variable Cache**:
- TTL: 100ms
- Strategy: Read-through cache
- Invalidation: On write operations
- Impact: Reduces PLC load for high-frequency reads

**Symbol Parser Cache**:
- Lazy loading: Parse TPY only when requested
- Memory cache: Symbols held in RAM
- Invalidation: On TPY upload or PLC switch

**Frontend Cache**:
- Static assets: Browser cache (future: Cache-Control headers)
- API responses: No caching (real-time data)

### Connection Pooling

**WebSocket Connections**:
- SocketIO manages connection pool
- Heartbeat interval: 25s (default)
- Max connections: Unlimited (future: configurable)

**PLC Connection**:
- Single connection per instance
- Auto-reconnect with exponential backoff
- Connection timeout: 5s

### Scalability Limits

**Current Architecture**:
- Single-threaded Flask (development server)
- WebSocket: 100-500 concurrent clients (estimated)
- PLC polling: ~10 variables at 100ms (10 Hz total)

**Production Recommendations**:
- Use Gunicorn + eventlet workers
- Separate WebSocket server (future)
- Implement rate limiting

---

## Future Architecture

### Planned Improvements

#### 1. Event-Driven Architecture

```
┌────────────────┐
│  Event Bus     │  (Redis Pub/Sub or NATS)
│  ┌──────────┐  │
│  │ plc_value│  │
│  │ changed  │  │
│  └──────────┘  │
└────────┬───────┘
         │
    ┌────┼────┐
    ▼    ▼    ▼
┌─────┐ ┌─────┐ ┌─────┐
│ Mod1│ │ Mod2│ │ WebUI│
└─────┘ └─────┘ └─────┘
```

**Benefits**:
- Loose coupling
- Better scalability
- Plugin hot-reload without restart

#### 2. Microservices Architecture (v4.6.0)

```
┌────────────┐  ┌────────────┐  ┌────────────┐
│  Gateway   │  │  Web UI    │  │  Auth      │
│  Service   │  │  Service   │  │  Service   │
└────┬───────┘  └────┬───────┘  └────┬───────┘
     │               │               │
     └───────────────┼───────────────┘
                     │
           ┌─────────┴─────────┐
           │  Message Broker   │  (RabbitMQ/Kafka)
           └───────────────────┘
```

**Benefits**:
- Independent scaling
- Language-agnostic plugins
- Better fault isolation

#### 3. Time-Series Database

**Current**: No historical data storage
**Future**: InfluxDB/TimescaleDB integration

```
PLC → Gateway → InfluxDB → Grafana
                 ↓
              WebSocket (Real-time)
```

**Use Cases**:
- Trend analysis
- Alarming based on historical patterns
- Energy consumption reports

#### 4. Plugin Marketplace

```
┌────────────────────────────────┐
│  Plugin Registry (NPM-like)    │
│  - plugin-modbus-master        │
│  - plugin-bacnet               │
│  - plugin-knx                  │
└────────────────────────────────┘
         │
         ▼ `pip install ...`
┌────────────────────────────────┐
│  Module Manager                │
│  - Dependency resolution       │
│  - Sandboxed execution         │
│  - Version compatibility       │
└────────────────────────────────┘
```

---

## Diagrams

### Module Dependency Graph (Current)

```
config_manager  (no dependencies)
      ▲
      │
plc_communication
      ▲
      │
data_gateway ◄─── mqtt_integration
      ▲
      │
web_manager ◄─── stream_manager
```

### Data Flow Sequence Diagram

```
Frontend          WebManager        DataGateway      PLCComm         TwinCAT
   │                  │                 │               │              │
   │── POST /api/plc/read ─────────────>│               │              │
   │                  │                 │               │              │
   │                  │──get_value()───>│               │              │
   │                  │                 │               │              │
   │                  │                 │─read_by_name()>│              │
   │                  │                 │               │              │
   │                  │                 │               │─ ADS Read ──>│
   │                  │                 │               │<── Value ────│
   │                  │                 │<── Value ─────│              │
   │                  │<── Value ───────│               │              │
   │<── JSON Response ──────────────────│               │              │
```

---

## Glossary

**ADS**: Automation Device Specification (Beckhoff protocol)
**AMS NetID**: TwinCAT router address (e.g., `192.168.1.100.1.1`)
**TPY**: TwinCAT Symbol Export XML file
**Blob**: Binary Large Object (images, video)
**Telemetry**: Real-time sensor/actuator values
**Symbol**: PLC variable metadata (name, type, path)
**Widget**: UI component bound to Gateway data
**Module**: Self-contained functional unit (plugin)

---

**Document Version**: 1.0.0
**Last Updated**: 2026-01-04
**Maintained by**: TwinCAT Team

