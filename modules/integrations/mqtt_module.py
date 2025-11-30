"""
MQTT Integration Module
Version: 1.0.0
Verbindet mit MQTT Broker für SolarAssistant & andere IoT-Geräte
"""

from module_manager import BaseModule
from typing import Dict, Any, Optional, Callable
import threading


class MQTTIntegration(BaseModule):
    NAME = "mqtt_integration"
    VERSION = "1.0.0"
    DESCRIPTION = "MQTT für SolarAssistant & IoT"
    AUTHOR = "TwinCAT Team"
    DEPENDENCIES = []
    
    def __init__(self):
        super().__init__()
        self.client = None
        self.connected = False
        self.subscriptions = {}  # topic -> callback
        self.values = {}  # topic -> last_value
    
    def initialize(self, app_context: Any):
        super().initialize(app_context)
        print(f"  ⚡ {self.NAME} v{self.VERSION} initialisiert")
    
    def connect(self, broker: str, port: int = 1883, 
                username: str = None, password: str = None):
        """Verbindet mit MQTT Broker"""
        try:
            import paho.mqtt.client as mqtt
            
            self.client = mqtt.Client()
            
            if username and password:
                self.client.username_pw_set(username, password)
            
            self.client.on_connect = self._on_connect
            self.client.on_message = self._on_message
            
            self.client.connect(broker, port, 60)
            self.client.loop_start()
            
            print(f"  ✓ MQTT verbunden: {broker}:{port}")
            return True
            
        except ImportError:
            print("  ⚠️  paho-mqtt nicht installiert! pip install paho-mqtt")
            return False
        except Exception as e:
            print(f"  ✗ MQTT Fehler: {e}")
            return False
    
    def _on_connect(self, client, userdata, flags, rc):
        """Callback bei Verbindung"""
        if rc == 0:
            self.connected = True
            # Re-subscribe zu allen Topics
            for topic in self.subscriptions.keys():
                client.subscribe(topic)
        else:
            print(f"  ✗ MQTT Verbindung fehlgeschlagen: {rc}")
    
    def _on_message(self, client, userdata, msg):
        """Callback bei Nachricht"""
        topic = msg.topic
        payload = msg.payload.decode('utf-8')
        
        # Speichere letzten Wert
        self.values[topic] = payload
        
        # Rufe Callback auf
        if topic in self.subscriptions:
            try:
                self.subscriptions[topic](topic, payload)
            except Exception as e:
                print(f"  ✗ Callback-Fehler für {topic}: {e}")
    
    def subscribe(self, topic: str, callback: Callable = None):
        """Abonniert Topic"""
        if not self.client:
            return False
        
        self.subscriptions[topic] = callback or (lambda t, p: None)
        self.client.subscribe(topic)
        print(f"  ✓ MQTT Subscribe: {topic}")
        return True
    
    def publish(self, topic: str, payload: str):
        """Veröffentlicht Nachricht"""
        if not self.client:
            return False
        
        self.client.publish(topic, payload)
        return True
    
    def get_value(self, topic: str) -> Optional[str]:
        """Holt letzten Wert eines Topics"""
        return self.values.get(topic)
    
    def get_solarassistant_pv_power(self) -> Optional[float]:
        """Beispiel: SolarAssistant PV-Leistung"""
        value = self.get_value('solarassistant/pv_power')
        if value:
            try:
                return float(value)
            except:
                return None
        return None
    
    def shutdown(self):
        """Trennt MQTT-Verbindung"""
        if self.client:
            self.client.loop_stop()
            self.client.disconnect()
            print("  ✓ MQTT getrennt")


def register(module_manager):
    module_manager.register_module(
        MQTTIntegration.NAME,
        MQTTIntegration.VERSION,
        MQTTIntegration.DESCRIPTION,
        MQTTIntegration,
        author=MQTTIntegration.AUTHOR
    )
