"""
Multi-PLC Example Plugin v1.0
Demonstriert parallelen Zugriff auf mehrere PLCs

Features:
- Mehrere PLC-Verbindungen gleichzeitig nutzen
- Cross-PLC Datenrouting
- Aggregierte Statusüberwachung
- Alarm-Sammlung über mehrere PLCs
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from modules.base.base_plugin import BasePlugin
from typing import Dict, Any, List
import time


class MultiPLCExamplePlugin(BasePlugin):
    """
    Beispiel-Plugin für Multi-PLC Zugriff

    Use Cases:
    - Gebäudesteuerung über mehrere PLCs
    - Aggregierte Alarmliste
    - Cross-PLC Datenweiterleitung
    - Zentrale Statusübersicht
    """

    def initialize(self):
        """Plugin-Initialisierung"""
        print(f"\n  🔌 {self.__class__.__name__} - Initialisierung...")

        # Hole Connection Manager
        self.conn_mgr = self.app.module_manager.get_module('connection_manager')
        if not self.conn_mgr:
            raise RuntimeError("Connection Manager nicht verfügbar!")

        # Hole Data Gateway
        self.data_gateway = self.app.module_manager.get_module('data_gateway')
        if not self.data_gateway:
            raise RuntimeError("Data Gateway nicht verfügbar!")

        # Settings
        self.monitor_interval = self.config.get('monitor_interval', 1.0)
        self.log_changes = self.config.get('log_data_changes', True)

        # State
        self.active_plcs = {}  # connection_id -> PLCConnection
        self.last_values = {}  # unified_key -> value
        self.alarm_counts = {}  # connection_id -> count

        # Subscribe auf alle PLC-Daten
        self.data_gateway.subscribe("plc_*", self.on_plc_data_received)

        print(f"  ✅ {self.__class__.__name__} initialisiert")

    def startup(self):
        """Plugin-Start"""
        print(f"  ▶️  {self.__class__.__name__} startet...")

        # Hole alle PLC-Verbindungen
        self._discover_plc_connections()

        # Zeige PLC-Übersicht
        self._print_plc_overview()

    def execute(self):
        """Haupt-Loop"""
        print(f"  ▶️  {self.__class__.__name__} - Monitoring läuft...\n")

        while self.is_running:
            try:
                # 1. Überwache alle PLCs
                self._monitor_all_plcs()

                # 2. Sammle Alarme
                self._collect_alarms()

                # 3. Cross-PLC Logik (Beispiel)
                self._cross_plc_logic()

                # 4. Aggregierte Statistik
                self._publish_aggregate_stats()

                time.sleep(self.monitor_interval)

            except Exception as e:
                print(f"  ⚠️  Fehler in execute(): {e}")
                time.sleep(5.0)

    def shutdown(self):
        """Plugin-Shutdown"""
        print(f"  ⏹️  {self.__class__.__name__} wird beendet...")

        # Unsubscribe
        if self.data_gateway:
            self.data_gateway.unsubscribe("plc_*", self.on_plc_data_received)

        print(f"  ✅ {self.__class__.__name__} beendet")

    # ========================================================================
    # PLC DISCOVERY & MANAGEMENT
    # ========================================================================

    def _discover_plc_connections(self):
        """Findet alle verfügbaren PLC-Verbindungen"""
        all_connections = self.conn_mgr.get_all_connections()

        for conn_id, connection in all_connections.items():
            # Prüfe ob PLC-Verbindung
            if connection.__class__.__name__ == 'PLCConnection':
                self.active_plcs[conn_id] = connection
                self.alarm_counts[conn_id] = 0

                print(f"    ✅ PLC gefunden: {conn_id}")

        print(f"\n  📊 {len(self.active_plcs)} PLC(s) verfügbar")

    def _print_plc_overview(self):
        """Zeigt PLC-Übersicht"""
        print("\n" + "="*60)
        print("  PLC-ÜBERSICHT")
        print("="*60)

        if not self.active_plcs:
            print("  ⚠️  Keine PLCs gefunden!")
            return

        for conn_id, plc_conn in self.active_plcs.items():
            status = plc_conn.get_status()

            print(f"\n  🔌 {conn_id}")
            print(f"     Status: {status['status']}")
            print(f"     Config: {plc_conn.ams_net_id}:{plc_conn.ams_port}")

            if status['status'] == 'connected':
                # Zeige Device Info
                device_info = plc_conn.read_device_info()
                if device_info:
                    print(f"     Device: {device_info.name}")
                    print(f"     Version: {device_info.version}")

                # Zeige State
                state = plc_conn.read_state()
                if state:
                    print(f"     PLC State: {state}")

        print("\n" + "="*60 + "\n")

    # ========================================================================
    # MONITORING
    # ========================================================================

    def _monitor_all_plcs(self):
        """Überwacht alle PLC-Verbindungen"""
        for conn_id, plc_conn in self.active_plcs.items():
            if not plc_conn.is_connected():
                # PLC offline
                if self.log_changes:
                    print(f"  ⚠️  {conn_id} - OFFLINE")
                continue

            # Beispiel: Lese Standard-Variablen
            self._read_plc_variables(conn_id, plc_conn)

    def _read_plc_variables(self, conn_id: str, plc_conn: Any):
        """Liest Standard-Variablen einer PLC"""
        # Beispiel-Variablen (anpassen an echte PLC!)
        variables = [
            "MAIN.bAlarm",
            "MAIN.nTemperature",
            "MAIN.bSystemReady"
        ]

        for var in variables:
            try:
                value = plc_conn.read_by_name(var, use_cache=True)

                # Check für Änderungen
                unified_key = f"{conn_id}.{var}"
                last_value = self.last_values.get(unified_key)

                if value != last_value:
                    if self.log_changes:
                        print(f"  📊 {unified_key}: {last_value} → {value}")

                    self.last_values[unified_key] = value

                    # Route zu DataGateway (wird automatisch gemacht, aber könnte manuell sein)
                    # self.data_gateway.route_data(conn_id, var, value)

            except Exception as e:
                # Variable existiert nicht oder Lesefehler
                pass

    def _collect_alarms(self):
        """Sammelt Alarme von allen PLCs"""
        total_alarms = 0

        for conn_id, plc_conn in self.active_plcs.items():
            if not plc_conn.is_connected():
                continue

            try:
                # Beispiel: Lese Alarm-Flag
                alarm_active = plc_conn.read_by_name("MAIN.bAlarm", use_cache=True)

                if alarm_active:
                    self.alarm_counts[conn_id] += 1
                    total_alarms += 1

                    # Lese Alarm-Details
                    alarm_code = plc_conn.read_by_name("MAIN.nAlarmCode", use_cache=True)
                    alarm_text = plc_conn.read_by_name("MAIN.sAlarmText", use_cache=True)

                    print(f"  🚨 ALARM auf {conn_id}:")
                    print(f"     Code: {alarm_code}")
                    print(f"     Text: {alarm_text}")

            except:
                pass

        # Publiziere Gesamt-Alarmzahl
        if total_alarms > 0:
            self.publish("alarms/total", total_alarms)

    # ========================================================================
    # CROSS-PLC LOGIK
    # ========================================================================

    def _cross_plc_logic(self):
        """
        Beispiel für Cross-PLC Logik

        Szenario:
        - Wenn Haupt-PLC Energie-Alarm hat
        - Dann schalte Garagen-PLC in Standby-Modus
        """
        try:
            # Hole Verbindungen
            plc_main = self.active_plcs.get('plc_main')
            plc_garage = self.active_plcs.get('plc_garage')

            if not plc_main or not plc_garage:
                return

            if not plc_main.is_connected() or not plc_garage.is_connected():
                return

            # Lese Energy-Alarm von Haupt-PLC
            energy_alarm = plc_main.read_by_name("MAIN.bEnergyAlarm", use_cache=True)

            if energy_alarm:
                # Setze Garagen-PLC in Standby
                current_mode = plc_garage.read_by_name("MAIN.nOperationMode", use_cache=False)

                if current_mode != 2:  # 2 = Standby
                    print(f"  ⚡ Energy-Alarm! Setze Garage in Standby...")
                    plc_garage.write_by_name("MAIN.nOperationMode", 2)

                    # Publiziere Event
                    self.publish("system/cross_plc_action", {
                        'action': 'standby_garage',
                        'reason': 'energy_alarm',
                        'timestamp': time.time()
                    })

        except Exception as e:
            # Variables nicht vorhanden oder Fehler
            pass

    # ========================================================================
    # STATISTIK & AGGREGATION
    # ========================================================================

    def _publish_aggregate_stats(self):
        """Publiziert aggregierte Statistik aller PLCs"""
        stats = {
            'total_plcs': len(self.active_plcs),
            'connected_plcs': 0,
            'disconnected_plcs': 0,
            'total_packets_sent': 0,
            'total_packets_received': 0,
            'total_errors': 0,
            'plc_details': {}
        }

        for conn_id, plc_conn in self.active_plcs.items():
            plc_status = plc_conn.get_status()

            if plc_status['status'] == 'connected':
                stats['connected_plcs'] += 1
            else:
                stats['disconnected_plcs'] += 1

            # Aggregiere Statistik
            stats['total_packets_sent'] += plc_status['stats']['packets_sent']
            stats['total_packets_received'] += plc_status['stats']['packets_received']
            stats['total_errors'] += plc_status['stats']['errors']

            # Detail-Statistik
            stats['plc_details'][conn_id] = {
                'status': plc_status['status'],
                'packets_sent': plc_status['stats']['packets_sent'],
                'packets_received': plc_status['stats']['packets_received'],
                'errors': plc_status['stats']['errors'],
                'alarms': self.alarm_counts.get(conn_id, 0)
            }

        # Publiziere über DataGateway
        self.publish("stats/aggregate", stats)

    # ========================================================================
    # CALLBACKS
    # ========================================================================

    def on_plc_data_received(self, datapoint: Dict):
        """
        Callback wenn PLC-Daten empfangen werden

        Args:
            datapoint: {
                'source_id': 'plc_main',
                'tag': 'MAIN.temperature',
                'value': 22.5,
                'timestamp': 1735926000.123,
                'metadata': {...}
            }
        """
        source_id = datapoint['source_id']
        tag = datapoint['tag']
        value = datapoint['value']

        # Beispiel: Reagiere auf spezielle Variablen
        if tag == "MAIN.bEmergencyStop":
            if value:
                print(f"  🚨 EMERGENCY STOP auf {source_id}!")
                # Stoppe alle anderen PLCs
                self._emergency_shutdown_all_plcs(exclude=source_id)

    def _emergency_shutdown_all_plcs(self, exclude: str = None):
        """Notfall-Shutdown aller PLCs außer exclude"""
        for conn_id, plc_conn in self.active_plcs.items():
            if conn_id == exclude:
                continue

            if plc_conn.is_connected():
                try:
                    print(f"  ⚠️  Emergency Shutdown: {conn_id}")
                    plc_conn.write_by_name("MAIN.bEmergencyStop", True)
                except Exception as e:
                    print(f"  ✗ Fehler beim Emergency Shutdown von {conn_id}: {e}")

    # ========================================================================
    # HELPER
    # ========================================================================

    def get_plc_by_id(self, connection_id: str) -> Any:
        """Holt spezifische PLC-Verbindung"""
        return self.active_plcs.get(connection_id)

    def write_to_plc(self, connection_id: str, symbol: str, value: Any) -> bool:
        """Schreibt Wert zu spezifischer PLC"""
        plc = self.get_plc_by_id(connection_id)
        if not plc:
            print(f"  ✗ PLC {connection_id} nicht gefunden!")
            return False

        if not plc.is_connected():
            print(f"  ✗ PLC {connection_id} nicht verbunden!")
            return False

        return plc.write_by_name(symbol, value)

    def read_from_plc(self, connection_id: str, symbol: str, use_cache: bool = True) -> Any:
        """Liest Wert von spezifischer PLC"""
        plc = self.get_plc_by_id(connection_id)
        if not plc:
            return None

        if not plc.is_connected():
            return None

        return plc.read_by_name(symbol, use_cache=use_cache)


# ========================================================================
# STANDALONE TEST
# ========================================================================

def test_multi_plc():
    """Testet Multi-PLC Plugin (benötigt laufende PLCs!)"""
    print("="*60)
    print("  Multi-PLC Example - Standalone Test")
    print("="*60)

    # Mock App-Context
    class MockModuleManager:
        def __init__(self):
            from modules.core.connection_manager import ConnectionManager
            from modules.gateway.data_gateway import DataGateway

            self.modules = {
                'connection_manager': ConnectionManager(None, None),
                'data_gateway': DataGateway(None, None)
            }

        def get_module(self, name):
            return self.modules.get(name)

    class MockApp:
        def __init__(self):
            self.module_manager = MockModuleManager()

    # Konfiguration
    config = {
        'monitor_interval': 2.0,
        'log_data_changes': True
    }

    # Erstelle Plugin
    plugin = MultiPLCExamplePlugin(MockApp(), config)

    try:
        # Initialisiere
        plugin.initialize()

        # Starte
        plugin.startup()

        # Laufe 30 Sekunden
        plugin.is_running = True
        for i in range(15):
            plugin.execute()
            if not plugin.is_running:
                break
            time.sleep(2.0)

    except KeyboardInterrupt:
        print("\n  ⏹️  Test abgebrochen")
    except Exception as e:
        print(f"  ✗ Test-Fehler: {e}")
    finally:
        plugin.is_running = False
        plugin.shutdown()


if __name__ == "__main__":
    test_multi_plc()
