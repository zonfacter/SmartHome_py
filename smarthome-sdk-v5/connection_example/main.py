"""
Custom Connection Example v1.0
Demonstriert wie man eigene Verbindungstypen erstellt

Features:
- Eigene Hardware-Verbindungen implementieren
- Integration in Connection Manager
- Health-Monitoring
- Auto-Reconnect
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'modules', 'core'))

from connection_manager import BaseConnection, ConnectionStatus
import time
import socket
from typing import Dict, Any


class CustomTCPConnection(BaseConnection):
    """
    Beispiel: Eigene TCP-Socket Verbindung

    Zeigt wie man BaseConnection implementiert für:
    - Proprietäre Hardware
    - Custom Protokolle
    - Spezielle Sensoren/Aktoren
    """

    def __init__(self, connection_id: str, config: Dict, app_context: Any):
        super().__init__(connection_id, config, app_context)

        # TCP-Socket Config
        self.host = config.get('host', 'localhost')
        self.port = config.get('port', 5000)
        self.timeout = config.get('timeout', 5.0)

        # Socket
        self.socket = None

    def connect(self) -> bool:
        """
        Stellt TCP-Verbindung her

        Returns:
            True wenn erfolgreich
        """
        try:
            print(f"  🔌 Verbinde zu {self.host}:{self.port}...")

            # Status aktualisieren
            self.status = ConnectionStatus.CONNECTING

            # Socket erstellen
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(self.timeout)

            # Verbinden
            self.socket.connect((self.host, self.port))

            # Erfolgreich
            self.status = ConnectionStatus.CONNECTED
            self.connected_at = time.time()
            self.reconnect_attempts = 0
            self.last_error = None

            print(f"  ✅ Verbunden mit {self.host}:{self.port}")

            # Initialisierungs-Handshake (optional)
            self._send_init_handshake()

            return True

        except Exception as e:
            self.status = ConnectionStatus.ERROR
            self.last_error = str(e)
            self.stats['errors'] += 1

            print(f"  ✗ Verbindungsfehler: {e}")
            return False

    def disconnect(self) -> bool:
        """
        Trennt TCP-Verbindung

        Returns:
            True wenn erfolgreich
        """
        try:
            if self.socket:
                # Optional: Sende Goodbye-Message
                try:
                    self._send_goodbye()
                except:
                    pass

                self.socket.close()
                self.socket = None

            self.status = ConnectionStatus.DISCONNECTED
            self.connected_at = None

            print(f"  🔌 Getrennt von {self.host}:{self.port}")
            return True

        except Exception as e:
            print(f"  ⚠️  Fehler beim Trennen: {e}")
            return False

    def is_connected(self) -> bool:
        """
        Prüft ob Verbindung aktiv ist

        Returns:
            True wenn verbunden
        """
        if self.status != ConnectionStatus.CONNECTED:
            return False

        if not self.socket:
            return False

        # Optional: Prüfe Socket-Status
        try:
            # Versuche minimales Read ohne Blocking
            self.socket.setblocking(0)
            data = self.socket.recv(1, socket.MSG_PEEK)
            self.socket.setblocking(1)
            return True
        except BlockingIOError:
            # Keine Daten = aber Socket OK
            self.socket.setblocking(1)
            return True
        except:
            return False

    def health_check(self) -> bool:
        """
        Führt Health-Check durch

        Returns:
            True wenn gesund
        """
        if not self.is_connected():
            return False

        try:
            # Sende Ping-Nachricht
            ping_data = b"PING\n"
            self.socket.send(ping_data)

            # Warte auf Antwort (mit Timeout)
            self.socket.settimeout(2.0)
            response = self.socket.recv(1024)
            self.socket.settimeout(self.timeout)

            # Erwarte "PONG"
            if b"PONG" in response:
                return True
            else:
                print(f"  ⚠️  Health-Check: Unerwartete Antwort: {response}")
                return False

        except socket.timeout:
            print(f"  ⚠️  Health-Check Timeout")
            return False
        except Exception as e:
            print(f"  ⚠️  Health-Check Fehler: {e}")
            return False

    # ========================================================================
    # CUSTOM METHODS
    # ========================================================================

    def _send_init_handshake(self):
        """Sendet Initialisierungs-Handshake"""
        try:
            init_msg = b"HELLO SmartHome Edge OS v5.0\n"
            self.socket.send(init_msg)
            self.update_stats(packets_sent=1, bytes_sent=len(init_msg))
        except Exception as e:
            print(f"  ⚠️  Init-Handshake Fehler: {e}")

    def _send_goodbye(self):
        """Sendet Goodbye-Message vor Disconnect"""
        try:
            goodbye_msg = b"GOODBYE\n"
            self.socket.send(goodbye_msg)
            self.update_stats(packets_sent=1, bytes_sent=len(goodbye_msg))
        except:
            pass

    def send_data(self, data: bytes) -> bool:
        """
        Sendet Daten über Socket

        Args:
            data: Binärdaten

        Returns:
            True wenn erfolgreich
        """
        if not self.is_connected():
            return False

        try:
            self.socket.send(data)
            self.update_stats(packets_sent=1, bytes_sent=len(data))
            return True
        except Exception as e:
            print(f"  ✗ Send-Fehler: {e}")
            self.stats['errors'] += 1
            return False

    def receive_data(self, buffer_size: int = 1024) -> bytes:
        """
        Empfängt Daten vom Socket

        Args:
            buffer_size: Buffer-Größe

        Returns:
            Empfangene Daten
        """
        if not self.is_connected():
            return b''

        try:
            data = self.socket.recv(buffer_size)
            self.update_stats(packets_received=1, bytes_received=len(data))
            return data
        except Exception as e:
            print(f"  ✗ Receive-Fehler: {e}")
            self.stats['errors'] += 1
            return b''


# ========================================================================
# VERWENDUNGS-BEISPIEL
# ========================================================================

def example_usage():
    """
    Zeigt wie man die Custom Connection nutzt
    """
    print("="*60)
    print("  Custom Connection Example")
    print("="*60)

    # Mock App-Context
    class MockApp:
        pass

    config = {
        'host': '192.168.1.100',
        'port': 5000,
        'timeout': 5.0
    }

    # Erstelle Verbindung
    connection = CustomTCPConnection(
        connection_id="tcp_device_001",
        config=config,
        app_context=MockApp()
    )

    print("\n1. Verbinden...")
    if connection.connect():
        print("   ✅ Verbindung hergestellt")

        print("\n2. Health-Check...")
        if connection.health_check():
            print("   ✅ Health-Check OK")
        else:
            print("   ⚠️  Health-Check fehlgeschlagen")

        print("\n3. Daten senden...")
        test_data = b"TEST MESSAGE\n"
        if connection.send_data(test_data):
            print(f"   ✅ Gesendet: {test_data}")

        print("\n4. Status abrufen...")
        status = connection.get_status()
        print(f"   Status: {status['status']}")
        print(f"   Packets Sent: {status['stats']['packets_sent']}")
        print(f"   Bytes Sent: {status['stats']['bytes_sent']}")

        print("\n5. Trennen...")
        connection.disconnect()
        print("   ✅ Getrennt")

    else:
        print("   ✗ Verbindung fehlgeschlagen")

    print("\n" + "="*60)


# ========================================================================
# INTEGRATION MIT CONNECTION MANAGER
# ========================================================================

def register_with_connection_manager(connection_manager):
    """
    Registriert Custom Connection im Connection Manager

    Usage:
        conn_mgr = app_context.module_manager.get_module('connection_manager')
        register_with_connection_manager(conn_mgr)
    """
    connection_manager.register_connection_type(
        'custom_tcp',
        CustomTCPConnection
    )

    print("  ✅ CustomTCPConnection registriert als 'custom_tcp'")
    print("     Kann jetzt in connections.json verwendet werden:")
    print("""
    {
      "my_device": {
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
    """)


if __name__ == "__main__":
    example_usage()
