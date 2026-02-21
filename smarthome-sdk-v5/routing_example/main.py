"""
Routing Example Plugin v1.0
Demonstriert die Nutzung des Universal Data Routers (v4.6.0)

Features:
- Publizieren von Daten via route_data()
- Subscriben auf Datenströme
- Pattern-Matching
- Spam-Protection Handling
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from base_plugin import BasePlugin
import time
import random


class RoutingExamplePlugin(BasePlugin):
    """
    Beispiel-Plugin für Universal Data Router

    Dieses Plugin zeigt:
    1. Wie man Daten publiziert (route_data)
    2. Wie man auf Daten subscribt
    3. Wie man mit verschiedenen Quellen arbeitet
    4. Wie Spam-Protection funktioniert
    """

    def initialize(self):
        """Setup des Plugins"""
        self.log.info("🚀 Routing Example Plugin startet...")

        # Konfiguration
        self.publish_interval = self.config.get("publish_interval", 5.0)
        self.counter = 0

        # ⭐ Subscribe auf Datenströme
        # Beispiel 1: Subscribe auf spezifischen Datenpunkt
        if hasattr(self.app, 'data_gateway'):
            self.app.data_gateway.subscribe(
                "plc_001.MAIN.bAlarm",
                self.on_alarm_received
            )

            # Beispiel 2: Subscribe auf alle PLC-Daten mit Wildcard
            self.app.data_gateway.subscribe(
                "plc_001.*",
                self.on_plc_data_received
            )

            # Beispiel 3: Subscribe auf Bluetooth BMS
            self.app.data_gateway.subscribe(
                "bt.bms_001.voltage",
                self.on_bms_voltage_received
            )

        self.log.info("  ✅ Subscriptions registriert")

    def execute(self):
        """
        Hauptschleife - Publiziert Beispieldaten

        Zeigt verschiedene Publish-Szenarien:
        1. Einfache Werte
        2. Mit Metadaten
        3. Verschiedene Datentypen
        """
        while self.is_running:
            # ========================================================================
            # Beispiel 1: Einfaches Publish (Sensor-Wert)
            # ========================================================================
            temperature = round(random.uniform(18.0, 26.0), 2)
            self.publish("sensors/temperature", temperature)

            # ========================================================================
            # Beispiel 2: Publish mit Metadaten
            # ========================================================================
            humidity = round(random.uniform(40.0, 60.0), 1)

            # Nutze route_data() direkt für erweiterte Kontrolle
            if hasattr(self.app, 'data_gateway'):
                self.app.data_gateway.route_data(
                    source_id=self.__class__.__name__,
                    tag="sensors/humidity",
                    value=humidity,
                    metadata={
                        'quality': 'good',
                        'unit': '%RH',
                        'sensor_id': 'DHT22_01'
                    }
                )

            # ========================================================================
            # Beispiel 3: Verschiedene Datentypen
            # ========================================================================
            self.counter += 1

            # Boolean
            self.publish("status/active", True)

            # Integer
            self.publish("counters/updates", self.counter)

            # String
            self.publish("status/message", f"Update #{self.counter}")

            # Float-Array (JSON-serializable)
            self.publish("sensors/multi_temp", [20.1, 21.3, 19.8, 22.0])

            # ========================================================================
            # Beispiel 4: Simuliere verschiedene "Quellen"
            # ========================================================================
            if self.counter % 3 == 0:
                # Simuliere BMS-Daten
                if hasattr(self.app, 'data_gateway'):
                    self.app.data_gateway.route_data(
                        source_id="bt.bms_simulator",
                        tag="voltage",
                        value=round(random.uniform(48.0, 54.0), 2),
                        metadata={'rssi': -45, 'quality': 'good'}
                    )

                    self.app.data_gateway.route_data(
                        source_id="bt.bms_simulator",
                        tag="current",
                        value=round(random.uniform(-10.0, 10.0), 2)
                    )

                    self.app.data_gateway.route_data(
                        source_id="bt.bms_simulator",
                        tag="soc",
                        value=random.randint(0, 100)
                    )

            self.log.info(f"📤 Publiziert: Temperatur={temperature}°C, Feuchtigkeit={humidity}%, Counter={self.counter}")

            # CPU-Schonung
            time.sleep(self.publish_interval)

    # ========================================================================
    # Callback-Funktionen für Subscriptions
    # ========================================================================

    def on_alarm_received(self, datapoint: dict):
        """
        Callback wenn PLC-Alarm eintrifft

        Args:
            datapoint: {
                'source_id': 'plc_001',
                'tag': 'MAIN.bAlarm',
                'value': True/False,
                'timestamp': 1234567890.123,
                'quality': 'good',
                'metadata': {}
            }
        """
        value = datapoint['value']
        timestamp = datapoint['timestamp']

        if value:
            self.log.warning(f"🚨 ALARM empfangen von {datapoint['source_id']} @ {timestamp}")

            # Reagiere auf Alarm - z.B. eigene Daten publizieren
            self.publish("alarms/acknowledged", True)
        else:
            self.log.info(f"✅ Alarm zurückgesetzt @ {timestamp}")

    def on_plc_data_received(self, datapoint: dict):
        """
        Callback für alle PLC-Daten (Wildcard-Subscription)

        Demonstriert Pattern-Matching auf mehrere Datenpunkte
        """
        tag = datapoint['tag']
        value = datapoint['value']

        # Filtere nur bestimmte Tags
        if "temperature" in tag.lower():
            self.log.info(f"🌡️  PLC Temperatur empfangen: {tag} = {value}")

    def on_bms_voltage_received(self, datapoint: dict):
        """
        Callback für BMS-Spannungsdaten

        Zeigt wie man auf externe Hardware-Daten reagieren kann
        """
        voltage = datapoint['value']
        metadata = datapoint.get('metadata', {})
        rssi = metadata.get('rssi', 'N/A')

        self.log.info(f"🔋 BMS Spannung: {voltage}V (RSSI: {rssi}dBm)")

        # Beispiel: Reagiere auf kritische Spannung
        if voltage < 48.0:
            self.log.warning(f"⚠️  Niedrige Spannung erkannt: {voltage}V")
            self.publish("alarms/low_voltage", True)
        elif voltage > 54.0:
            self.log.warning(f"⚠️  Hohe Spannung erkannt: {voltage}V")
            self.publish("alarms/high_voltage", True)

    def stop(self):
        """Cleanup beim Beenden"""
        self.log.info("🛑 Routing Example Plugin gestoppt")

        # Unsubscribe (optional, wird automatisch beim Beenden gemacht)
        if hasattr(self.app, 'data_gateway'):
            try:
                self.app.data_gateway.unsubscribe("plc_001.MAIN.bAlarm", self.on_alarm_received)
            except:
                pass

        super().stop()


# ========================================================================
# Test-Funktionen
# ========================================================================

def test_spam_protection():
    """
    Test: Spam-Protection

    Zeigt was passiert wenn man zu viele Nachrichten sendet
    """
    print("\n" + "="*60)
    print("TEST: Spam-Protection")
    print("="*60)

    # Simuliere App-Context
    class MockApp:
        class DataGateway:
            def route_data(self, source_id, tag, value, metadata=None):
                print(f"  📨 {source_id}.{tag} = {value}")
                return True

        data_gateway = DataGateway()

    config = {"publish_interval": 0.001, "max_pps": 10}  # Sehr niedriges Limit für Test
    plugin = RoutingExamplePlugin(MockApp(), config)

    print("\n  Sende 100 Nachrichten so schnell wie möglich...")
    print(f"  Limit: {plugin.max_pps} pps\n")

    for i in range(100):
        success = plugin.publish(f"test/spam_{i}", i)
        if not success:
            print(f"\n  🚫 SPAM-SCHUTZ AKTIV nach {i+1} Nachrichten!")
            break


def test_routing_patterns():
    """
    Test: Routing-Patterns

    Demonstriert verschiedene Routing-Szenarien
    """
    print("\n" + "="*60)
    print("TEST: Routing-Patterns")
    print("="*60)

    examples = [
        # (source_id, tag, value, beschreibung)
        ("MyPlugin", "sensors/temp", 23.5, "Plugin → Sensor-Daten"),
        ("plc_001", "MAIN.bAlarm", True, "PLC → Alarm-Signal"),
        ("bt.bms_001", "voltage", 52.3, "Bluetooth BMS → Spannung"),
        ("mqtt.broker_local", "homeassistant/sensors/temp", 21.2, "MQTT → HA-Daten"),
    ]

    print("\n  Beispiel-Routen die im System erstellt würden:\n")

    for source_id, tag, value, desc in examples:
        full_path = f"{source_id}.{tag}"
        print(f"  📍 {desc}")
        print(f"     Source: {source_id}")
        print(f"     Tag:    {tag}")
        print(f"     Value:  {value}")
        print(f"     Full:   {full_path}")
        print()


if __name__ == "__main__":
    print("="*60)
    print("  Routing Example Plugin - Test Suite")
    print("="*60)

    # Test 1: Spam-Protection
    test_spam_protection()

    # Test 2: Routing-Patterns
    test_routing_patterns()

    print("\n" + "="*60)
    print("  Tests abgeschlossen")
    print("="*60)
