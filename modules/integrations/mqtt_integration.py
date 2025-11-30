"""
MQTT Integration Module
Version: 1.0.0
MQTT-Verbindung für SolarAssistant, IoT-Devices, etc.

📁 SPEICHERORT: modules/integrations/mqtt_integration.py

Features:
- MQTT Broker Verbindung
- Topic Subscription
- Werte-Caching
- Auto-Reconnect
- Wildcard-Topics
- JSON-Payload Parsing
"""

from module_manager import BaseModule
from typing import Any, Dict, Callable, Optional
import threading
import time
import json


class MqttIntegration(BaseModule):
    """
    MQTT Integration
    
    Features:
    - Broker-Verbindung (mit Auth)
    - Topic-Subscription
    - Callback-System
    - Werte-Cache
    - Auto-Reconnect
    - JSON-Parsing
    """
    
    NAME = "mqtt_integration"
    VERSION = "1.0.0"
    DESCRIPTION = "MQTT für SolarAssistant & IoT"
    AUTHOR = "TwinCAT Team"
    
    def __init__(self):
        super().__init__()
        self.client = None
        self.connected = False
        self.mqtt_available = False
        self.mqtt_error = None
        self.config = {
            'broker': 'localhost',
            'port': 1883,
            'username': None,
            'password': None,
            'client_id': 'twincat_smarthome',
            'keepalive': 60
        }
        self.subscriptions = {}  # topic -> callback
        self.values = {}  # topic -> last_value
        self.reconnect_thread = None
        self.running = True
        
        # Prüfe paho-mqtt Verfügbarkeit
        try:
            import paho.mqtt.client as mqtt
            self.mqtt_available = True
            self.mqtt_module = mqtt
        except ImportError as e:
            self.mqtt_available = False
            self.mqtt_error = "paho-mqtt nicht installiert"
            self.mqtt_module = None
        except Exception as e:
            self.mqtt_available = False
            self.mqtt_error = str(e)
            self.mqtt_module = None
    
    def initialize(self, app_context: Any):
        """Initialisiert MQTT"""
        super().initialize(app_context)
        
        if not self.mqtt_available:
            print(f"  ⚠️  {self.NAME}: paho-mqtt nicht verfügbar! ({self.mqtt_error})")
            print(f"      Installiere mit: pip install paho-mqtt --break-system-packages")
        else:
            print(f"  ⚡ {self.NAME} v{self.VERSION} initialisiert")
    
    def configure(self, broker: str, port: int = 1883, 
                  username: str = None, password: str = None,
                  client_id: str = None):
        """
        Konfiguriert MQTT-Verbindung
        
        Args:
            broker: Broker-Adresse (IP oder Hostname)
            port: Port (Standard: 1883)
            username: Optional Username
            password: Optional Password
            client_id: Optional Client-ID
        """
        self.config['broker'] = broker
        self.config['port'] = port
        if username:
            self.config['username'] = username
        if password:
            self.config['password'] = password
        if client_id:
            self.config['client_id'] = client_id
    
    def connect(self) -> bool:
        """Verbindet zu MQTT-Broker"""
        if not self.mqtt_available:
            print(f"  ✗ MQTT nicht verfügbar: {self.mqtt_error}")
            return False
        
        try:
            # Erstelle Client
            self.client = self.mqtt_module.Client(client_id=self.config['client_id'])
            
            # Callbacks
            self.client.on_connect = self._on_connect
            self.client.on_disconnect = self._on_disconnect
            self.client.on_message = self._on_message
            
            # Auth wenn vorhanden
            if self.config['username'] and self.config['password']:
                self.client.username_pw_set(
                    self.config['username'],
                    self.config['password']
                )
            
            # Verbinden
            print(f"  🔌 Verbinde zu MQTT: {self.config['broker']}:{self.config['port']}")
            self.client.connect(
                self.config['broker'],
                self.config['port'],
                self.config['keepalive']
            )
            
            # Starte Loop in Thread
            self.client.loop_start()
            
            return True
            
        except Exception as e:
            print(f"  ✗ MQTT-Verbindung fehlgeschlagen: {e}")
            return False
    
    def _on_connect(self, client, userdata, flags, rc):
        """Callback: Verbunden"""
        if rc == 0:
            self.connected = True
            print(f"  ✓ MQTT verbunden: {self.config['broker']}")
            
            # Re-Subscribe zu allen Topics
            for topic in self.subscriptions.keys():
                client.subscribe(topic)
                print(f"    📥 Subscribe: {topic}")
        else:
            print(f"  ✗ MQTT-Verbindung fehlgeschlagen: Code {rc}")
    
    def _on_disconnect(self, client, userdata, rc):
        """Callback: Getrennt"""
        self.connected = False
        print(f"  ⚠️  MQTT getrennt (Code {rc})")
        
        # Auto-Reconnect wenn nicht manuell getrennt
        if rc != 0 and self.running:
            print(f"  🔄 Auto-Reconnect in 5s...")
            time.sleep(5)
            try:
                client.reconnect()
            except:
                pass
    
    def _on_message(self, client, userdata, msg):
        """Callback: Nachricht empfangen"""
        topic = msg.topic
        payload = msg.payload.decode('utf-8')
        
        # Versuche JSON zu parsen
        try:
            value = json.loads(payload)
        except:
            # Kein JSON, nutze String
            value = payload
        
        # Cache Wert
        self.values[topic] = {
            'value': value,
            'timestamp': time.time()
        }
        
        # Rufe Callback auf wenn registriert
        if topic in self.subscriptions:
            callback = self.subscriptions[topic]
            try:
                callback(topic, value)
            except Exception as e:
                print(f"  ✗ Callback-Fehler für {topic}: {e}")
    
    def subscribe(self, topic: str, callback: Callable = None):
        """
        Abonniert Topic
        
        Args:
            topic: MQTT-Topic (kann Wildcards enthalten: +, #)
            callback: Optional Callback-Funktion (topic, value)
        """
        if not self.client:
            return False
        
        # Speichere Subscription
        self.subscriptions[topic] = callback
        
        # Subscribe wenn verbunden
        if self.connected:
            self.client.subscribe(topic)
            print(f"  📥 Subscribe: {topic}")
        
        return True
    
    def unsubscribe(self, topic: str):
        """Deabonniert Topic"""
        if not self.client:
            return False
        
        if topic in self.subscriptions:
            del self.subscriptions[topic]
        
        if self.connected:
            self.client.unsubscribe(topic)
        
        return True
    
    def publish(self, topic: str, payload: Any, retain: bool = False):
        """
        Veröffentlicht Nachricht
        
        Args:
            topic: MQTT-Topic
            payload: Daten (wird zu JSON wenn Dict/List)
            retain: Retain-Flag
        """
        if not self.client or not self.connected:
            return False
        
        # Konvertiere zu JSON wenn nötig
        if isinstance(payload, (dict, list)):
            payload = json.dumps(payload)
        
        self.client.publish(topic, payload, retain=retain)
        return True
    
    def get_value(self, topic: str, default=None) -> Any:
        """
        Holt letzten Wert von Topic
        
        Args:
            topic: MQTT-Topic
            default: Default-Wert wenn nicht vorhanden
        
        Returns:
            Letzter Wert oder default
        """
        if topic in self.values:
            return self.values[topic]['value']
        return default
    
    def get_all_values(self) -> Dict:
        """Gibt alle gecachten Werte zurück"""
        return {topic: data['value'] for topic, data in self.values.items()}
    
    def disconnect(self):
        """Trennt Verbindung"""
        self.running = False
        
        if self.client:
            self.client.loop_stop()
            self.client.disconnect()
            self.connected = False
            print(f"  ✓ MQTT getrennt")
    
    def shutdown(self):
        """Beendet MQTT"""
        self.disconnect()


def register(module_manager):
    """Registriert Modul"""
    module_manager.register_module(
        MqttIntegration.NAME,
        MqttIntegration.VERSION,
        MqttIntegration.DESCRIPTION,
        MqttIntegration,
        author=MqttIntegration.AUTHOR
    )
