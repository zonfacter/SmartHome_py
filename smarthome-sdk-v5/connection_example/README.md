# Custom Connection Example

Zeigt wie man **eigene Verbindungstypen** für Hardware/Protokolle erstellt und in den **Connection Manager** integriert.

## Was macht dieses Beispiel?

Demonstriert die Implementierung einer benutzerdefinierten Verbindung (`BaseConnection`):
- TCP-Socket Verbindung als Beispiel
- Health-Monitoring
- Auto-Reconnect Integration
- Statistik-Tracking
- Event-Callbacks

## Use Cases

Dieses Pattern nutzt man für:
- **Proprietäre Hardware** (eigene Sensoren/Aktoren)
- **Custom Protokolle** (nicht-standard TCP/UDP/Serial)
- **Spezielle Geräte** (Messgeräte, Laborequipment)
- **Legacy-Systeme** (alte SPS, spezielle Feldbusse)

---

## BaseConnection Interface

Jede Verbindung muss 4 abstrakte Methoden implementieren:

```python
class MyConnection(BaseConnection):
    def connect(self) -> bool:
        """Stellt Verbindung her"""
        pass

    def disconnect(self) -> bool:
        """Trennt Verbindung"""
        pass

    def is_connected(self) -> bool:
        """Prüft Verbindungsstatus"""
        pass

    def health_check(self) -> bool:
        """Health-Check für Auto-Reconnect"""
        pass
```

---

## Beispiel-Implementierung

### 1. TCP-Socket Connection

```python
class CustomTCPConnection(BaseConnection):
    def __init__(self, connection_id: str, config: Dict, app_context: Any):
        super().__init__(connection_id, config, app_context)

        self.host = config.get('host', 'localhost')
        self.port = config.get('port', 5000)
        self.socket = None

    def connect(self) -> bool:
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((self.host, self.port))

            self.status = ConnectionStatus.CONNECTED
            self.connected_at = time.time()

            return True
        except Exception as e:
            self.status = ConnectionStatus.ERROR
            self.last_error = str(e)
            return False
```

### 2. Health-Check

```python
def health_check(self) -> bool:
    """Sendet PING, erwartet PONG"""
    if not self.is_connected():
        return False

    try:
        self.socket.send(b"PING\n")
        response = self.socket.recv(1024)

        return b"PONG" in response
    except:
        return False
```

---

## Integration in Connection Manager

### 1. Verbindungstyp registrieren

```python
# In initialize() oder startup:
conn_mgr = app_context.module_manager.get_module('connection_manager')

conn_mgr.register_connection_type(
    'custom_tcp',           # Type-Name
    CustomTCPConnection     # Class
)
```

### 2. In connections.json konfigurieren

```json
{
  "connections": {
    "my_tcp_device": {
      "type": "custom_tcp",
      "name": "Mein TCP-Gerät",
      "enabled": true,
      "config": {
        "host": "192.168.1.100",
        "port": 5000,
        "timeout": 5.0,
        "auto_reconnect": true
      }
    }
  }
}
```

### 3. Verbindung nutzen

```python
# Hole Verbindung
connection = conn_mgr.get_connection("my_tcp_device")

if connection and connection.is_connected():
    # Nutze custom methods
    connection.send_data(b"COMMAND\n")
    response = connection.receive_data()
```

---

## Verfügbare Features

### Status-Tracking

```python
status = connection.get_status()
# Returns:
{
    'connection_id': 'my_tcp_device',
    'type': 'CustomTCPConnection',
    'status': 'connected',          # connected/disconnected/error
    'connected_at': 1735926000.123,
    'last_error': None,
    'reconnect_attempts': 0,
    'stats': {
        'packets_sent': 42,
        'packets_received': 38,
        'bytes_sent': 1024,
        'bytes_received': 2048,
        'errors': 0,
        'last_activity': 1735926100.456
    }
}
```

### Statistik aktualisieren

```python
# In send/receive methods:
self.update_stats(
    packets_sent=1,
    bytes_sent=len(data)
)
```

### Status setzen

```python
# Bei Connect:
self.status = ConnectionStatus.CONNECTED
self.connected_at = time.time()
self.reconnect_attempts = 0

# Bei Fehler:
self.status = ConnectionStatus.ERROR
self.last_error = str(exception)
self.stats['errors'] += 1
```

---

## Event-System

### Events registrieren

```python
def on_connected(connection: BaseConnection):
    print(f"Verbunden: {connection.connection_id}")

def on_error(connection: BaseConnection):
    print(f"Fehler: {connection.last_error}")

conn_mgr.on_event('connected', on_connected)
conn_mgr.on_event('error', on_error)
```

### Verfügbare Events

- `connected`: Verbindung hergestellt
- `disconnected`: Verbindung getrennt
- `error`: Fehler aufgetreten
- `health_check_failed`: Health-Check fehlgeschlagen

---

## Auto-Reconnect

Der Connection Manager übernimmt automatisch Reconnect bei:
- Health-Check Failures
- Verbindungsabbrüchen
- Timeout-Fehlern

### Konfiguration

```json
{
  "config": {
    "auto_reconnect": true
  },
  "settings": {
    "health_check_interval": 30,
    "reconnect_max_attempts": 10
  }
}
```

### Reconnect-Strategie

- **Exponential Backoff**: 5s, 7.5s, 11.25s, ...
- **Max Attempts**: 10 Versuche (konfigurierbar)
- **Suspension**: Nach max attempts → Status: SUSPENDED

---

## Real-World Beispiele

### Modbus TCP

```python
class ModbusTCPConnection(BaseConnection):
    def __init__(self, connection_id, config, app_context):
        super().__init__(connection_id, config, app_context)
        from pymodbus.client import ModbusTcpClient

        self.client = ModbusTcpClient(
            host=config['host'],
            port=config.get('port', 502)
        )

    def connect(self) -> bool:
        try:
            self.client.connect()
            self.status = ConnectionStatus.CONNECTED
            return True
        except:
            self.status = ConnectionStatus.ERROR
            return False

    def read_holding_registers(self, address, count):
        """Custom Modbus read method"""
        result = self.client.read_holding_registers(address, count)
        self.update_stats(packets_sent=1, packets_received=1)
        return result.registers if result else []
```

### Serial Port (RS485)

```python
class SerialConnection(BaseConnection):
    def __init__(self, connection_id, config, app_context):
        super().__init__(connection_id, config, app_context)
        import serial

        self.port = config['port']  # "COM3" or "/dev/ttyUSB0"
        self.baudrate = config.get('baudrate', 9600)
        self.serial = None

    def connect(self) -> bool:
        try:
            import serial
            self.serial = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                timeout=1
            )
            self.status = ConnectionStatus.CONNECTED
            return True
        except:
            self.status = ConnectionStatus.ERROR
            return False
```

### HTTP REST API

```python
class RESTAPIConnection(BaseConnection):
    def __init__(self, connection_id, config, app_context):
        super().__init__(connection_id, config, app_context)
        import requests

        self.base_url = config['base_url']
        self.api_key = config.get('api_key')
        self.session = requests.Session()

    def connect(self) -> bool:
        try:
            # Test-Request
            response = self.session.get(f"{self.base_url}/health")
            if response.status_code == 200:
                self.status = ConnectionStatus.CONNECTED
                return True
            return False
        except:
            return False

    def get(self, endpoint):
        """Custom GET method"""
        response = self.session.get(f"{self.base_url}/{endpoint}")
        self.update_stats(packets_sent=1, packets_received=1)
        return response.json()
```

---

## Testing

### Unit-Test

```bash
python main.py
```

Führt Beispiel-Usage aus:
1. Connect
2. Health-Check
3. Send Data
4. Get Status
5. Disconnect

### Integration-Test

1. Erstelle connections.json Eintrag
2. Starte SmartHome Edge OS
3. Prüfe Connection Manager Status
4. Teste Reconnect (trenne Hardware)

---

## Debugging

### Connection nicht verfügbar

```python
conn = conn_mgr.get_connection("my_device")

if not conn:
    print("Connection nicht registriert!")
    print("Verfügbare:", list(conn_mgr.connections.keys()))
```

### Health-Check schlägt fehl

```python
def health_check(self) -> bool:
    try:
        # Debugging
        print(f"Health-Check für {self.connection_id}...")

        # Test
        result = self._ping()

        print(f"Result: {result}")
        return result
    except Exception as e:
        print(f"Health-Check Exception: {e}")
        return False
```

---

## Best Practices

### ✅ DO:
- Implementiere robustes Error-Handling in `connect()`
- Aktualisiere `status` bei allen State-Changes
- Nutze `update_stats()` für Monitoring
- Implementiere sinnvollen `health_check()`
- Cleanup in `disconnect()`

### ❌ DON'T:
- Blockiere nicht in `connect()` (Timeout nutzen!)
- Vergiss nicht Status-Updates
- Ignoriere nicht Exceptions
- Nutze keine blocking I/O ohne Timeout

---

## Referenz

### ConnectionStatus Enum

```python
class ConnectionStatus(Enum):
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    ERROR = "error"
    SUSPENDED = "suspended"
```

### BaseConnection Attribute

```python
self.connection_id: str        # Eindeutige ID
self.config: Dict               # Konfiguration
self.app_context: Any           # App-Context
self.status: ConnectionStatus   # Aktueller Status
self.last_error: Optional[str]  # Letzter Fehler
self.connected_at: Optional[float]  # Timestamp
self.reconnect_attempts: int    # Reconnect-Zähler
self.stats: Dict                # Statistiken
```

---

## Support

- **Connection Manager**: `modules/core/connection_manager.py`
- **BaseConnection**: `modules/core/connection_manager.py:30`
- **Weitere Beispiele**: `smarthome-sdk-v5/*/`

---

**Version**: 1.0.0
**Autor**: TwinCAT Team
**Lizenz**: MIT
**Min. OS Version**: 4.6.0
