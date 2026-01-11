"""
BMS Monitor Example Plugin v1.0
Demonstriert BMS-Integration über Bluetooth

Features:
- Automatische BMS-Verbindung (JBD/Xiaoxiang)
- Periodisches Polling von BMS-Daten
- Alarm-Überwachung (Voltage, Temperature)
- DataGateway Integration
- Multi-BMS Support
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from modules.base.base_plugin import BasePlugin
from modules.bluetooth.bms_parser import bms_parser_registry
from typing import Dict, Any, Optional
import time


class BMSMonitorPlugin(BasePlugin):
    """
    BMS Monitor Plugin

    Überwacht BMS-Daten und routet sie zum DataGateway

    Use Cases:
    - Batterie-Monitoring für Camper/Wohnmobile
    - Solar-Speicher Überwachung
    - E-Bike/E-Scooter Batterie-Management
    - Stationäre Energiespeicher
    """

    def initialize(self):
        """Plugin-Initialisierung"""
        print(f"\n  🔋 {self.__class__.__name__} - Initialisierung...")

        # Hole Connection Manager
        self.conn_mgr = self.app.module_manager.get_module('connection_manager')
        if not self.conn_mgr:
            raise RuntimeError("Connection Manager nicht verfügbar!")

        # Hole Data Gateway
        self.data_gateway = self.app.module_manager.get_module('data_gateway')
        if not self.data_gateway:
            raise RuntimeError("Data Gateway nicht verfügbar!")

        # Settings
        self.poll_interval = self.config.get('poll_interval', 5.0)
        self.bms_protocol = self.config.get('bms_protocol', 'JBD')

        # Alarm-Limits
        self.alarm_voltage_min = self.config.get('alarm_voltage_min', 3.0)
        self.alarm_voltage_max = self.config.get('alarm_voltage_max', 3.65)
        self.alarm_temp_max = self.config.get('alarm_temp_max', 45.0)

        # BMS-Verbindungen & Parser
        self.bms_connections = {}  # connection_id -> BluetoothConnection
        self.bms_parsers = {}      # connection_id -> BMSParser

        # Alarms
        self.active_alarms = {}    # connection_id -> List[alarm]

        # Entdecke BMS-Verbindungen
        self._discover_bms_connections()

        # Initialisiere Parser
        self._initialize_parsers()

        print(f"  ✅ {self.__class__.__name__} initialisiert")

    def startup(self):
        """Plugin-Start"""
        print(f"  ▶️  {self.__class__.__name__} startet...")

        # Zeige BMS-Übersicht
        self._print_bms_overview()

    def execute(self):
        """Haupt-Loop"""
        print(f"  ▶️  {self.__class__.__name__} - Monitoring läuft...\n")

        while self.is_running:
            try:
                # Polle alle BMS
                for conn_id in self.bms_connections.keys():
                    self._poll_bms(conn_id)

                time.sleep(self.poll_interval)

            except Exception as e:
                print(f"  ⚠️  Fehler in execute(): {e}")
                time.sleep(5.0)

    def shutdown(self):
        """Plugin-Shutdown"""
        print(f"  ⏹️  {self.__class__.__name__} wird beendet...")

        print(f"  ✅ {self.__class__.__name__} beendet")

    # ========================================================================
    # BMS DISCOVERY & SETUP
    # ========================================================================

    def _discover_bms_connections(self):
        """Findet alle verfügbaren BMS (Bluetooth) Verbindungen"""
        all_connections = self.conn_mgr.get_all_connections()

        for conn_id, connection in all_connections.items():
            # Prüfe ob Bluetooth-Verbindung
            if connection.__class__.__name__ == 'BluetoothConnection':
                # Prüfe ob BMS (basierend auf connection_id oder device_name)
                if 'bms' in conn_id.lower() or 'bms' in connection.device_name.lower():
                    self.bms_connections[conn_id] = connection
                    print(f"    ✅ BMS gefunden: {conn_id}")

        print(f"\n  📊 {len(self.bms_connections)} BMS-Verbindung(en) verfügbar")

    def _initialize_parsers(self):
        """Initialisiert BMS-Parser für jede Verbindung"""
        for conn_id in self.bms_connections.keys():
            # Hole Parser aus Registry
            parser = bms_parser_registry.get_parser(self.bms_protocol, conn_id)

            if parser:
                self.bms_parsers[conn_id] = parser
                print(f"    ✅ Parser '{self.bms_protocol}' für {conn_id}")
            else:
                print(f"    ⚠️  Kein Parser für Protocol '{self.bms_protocol}'!")

    def _print_bms_overview(self):
        """Zeigt BMS-Übersicht"""
        print("\n" + "="*60)
        print("  BMS-ÜBERSICHT")
        print("="*60)

        if not self.bms_connections:
            print("  ⚠️  Keine BMS gefunden!")
            return

        for conn_id, bt_conn in self.bms_connections.items():
            status = bt_conn.get_status()

            print(f"\n  🔋 {conn_id}")
            print(f"     Status: {status['status']}")
            print(f"     Address: {bt_conn.address}")
            print(f"     Protocol: {self.bms_protocol}")

            if status['status'] == 'connected':
                # Zeige Device-Info
                if bt_conn.device_info:
                    print(f"     Device: {bt_conn.device_info}")

        print("\n" + "="*60 + "\n")

    # ========================================================================
    # BMS POLLING
    # ========================================================================

    def _poll_bms(self, connection_id: str):
        """
        Pollt BMS-Daten

        Args:
            connection_id: BMS Connection-ID
        """
        bt_conn = self.bms_connections.get(connection_id)
        parser = self.bms_parsers.get(connection_id)

        if not bt_conn or not parser:
            return

        if not bt_conn.is_connected():
            print(f"  ⚠️  {connection_id} - Nicht verbunden!")
            return

        try:
            # 1. Request Basic Info
            cmd_basic = parser.get_request_basic_info_command()
            bt_conn.write_characteristic(parser.get_write_characteristic_uuid(), cmd_basic)

            # Warte auf Response
            time.sleep(0.5)

            # Lese Response
            response_basic = bt_conn.read_characteristic(parser.get_read_characteristic_uuid())

            if response_basic:
                # Parse Basic Info
                bms_data = parser.parse(response_basic, "basic")

                if bms_data:
                    # 2. Request Cell Voltages
                    cmd_cells = parser.get_request_cell_voltages_command()
                    bt_conn.write_characteristic(parser.get_write_characteristic_uuid(), cmd_cells)

                    time.sleep(0.5)

                    response_cells = bt_conn.read_characteristic(parser.get_read_characteristic_uuid())

                    if response_cells:
                        # Parse Cell Voltages
                        bms_data = parser.parse(response_cells, "cells")

                    # 3. Verarbeite BMS-Daten
                    self._process_bms_data(connection_id, bms_data)

                    # 4. Prüfe Alarme
                    self._check_alarms(connection_id, bms_data)

                    # 5. Route zu DataGateway
                    self._route_bms_data(connection_id, bms_data)

        except Exception as e:
            print(f"  ✗ {connection_id} - Poll-Fehler: {e}")

    def _process_bms_data(self, connection_id: str, bms_data):
        """
        Verarbeitet BMS-Daten

        Args:
            connection_id: Connection-ID
            bms_data: BMSData-Objekt
        """
        # Log wichtige Werte
        print(f"\n  📊 {connection_id} - BMS Data:")
        print(f"     Voltage: {bms_data.total_voltage:.2f}V")
        print(f"     Current: {bms_data.current:.2f}A")
        print(f"     Power: {bms_data.power:.0f}W")
        print(f"     SoC: {bms_data.soc}%")
        print(f"     Temp Avg: {bms_data.temp_avg:.1f}°C")

        if bms_data.cell_voltages:
            print(f"     Cells: {len(bms_data.cell_voltages)} ({bms_data.cell_min:.3f}V - {bms_data.cell_max:.3f}V, Δ{bms_data.cell_delta*1000:.0f}mV)")

        if bms_data.balancing_active:
            print(f"     ⚡ Balancing: {bms_data.balancing_cells}")

    def _check_alarms(self, connection_id: str, bms_data):
        """
        Prüft Alarm-Bedingungen

        Args:
            connection_id: Connection-ID
            bms_data: BMSData-Objekt
        """
        alarms = []

        # Cell-Voltage Alarms
        for i, voltage in enumerate(bms_data.cell_voltages):
            if voltage < self.alarm_voltage_min:
                alarms.append({
                    'type': 'cell_undervoltage',
                    'cell': i,
                    'voltage': voltage,
                    'limit': self.alarm_voltage_min
                })
            elif voltage > self.alarm_voltage_max:
                alarms.append({
                    'type': 'cell_overvoltage',
                    'cell': i,
                    'voltage': voltage,
                    'limit': self.alarm_voltage_max
                })

        # Temperature Alarms
        if bms_data.temp_max > self.alarm_temp_max:
            alarms.append({
                'type': 'over_temperature',
                'temperature': bms_data.temp_max,
                'limit': self.alarm_temp_max
            })

        # Protection-Flags
        for flag_name, active in bms_data.protection_flags.items():
            if active:
                alarms.append({
                    'type': 'protection_active',
                    'flag': flag_name
                })

        # Speichere Alarme
        self.active_alarms[connection_id] = alarms

        # Publiziere Alarme
        if alarms:
            print(f"\n  🚨 {connection_id} - ALARME:")
            for alarm in alarms:
                print(f"     {alarm}")

            # Route Alarm-Liste zu DataGateway
            self.publish(f"{connection_id}/alarms", alarms)

    def _route_bms_data(self, connection_id: str, bms_data):
        """
        Routet BMS-Daten zum DataGateway

        Args:
            connection_id: Connection-ID
            bms_data: BMSData-Objekt
        """
        # Konvertiere zu Dict
        data_dict = bms_data.to_dict()

        # Route einzelne Werte
        for key, value in data_dict.items():
            tag = f"bms.{key}"
            self.publish(tag, value)

        # Route Gesamt-Objekt
        self.publish("bms/data", data_dict)

    # ========================================================================
    # STATISTICS
    # ========================================================================

    def get_bms_summary(self) -> Dict[str, Any]:
        """
        Liefert Gesamt-Übersicht aller BMS

        Returns:
            Summary-Dict
        """
        summary = {
            'total_bms': len(self.bms_connections),
            'connected': 0,
            'disconnected': 0,
            'total_capacity': 0.0,
            'total_soc_avg': 0,
            'total_alarms': 0,
            'bms_details': {}
        }

        soc_sum = 0

        for conn_id, bt_conn in self.bms_connections.items():
            status = bt_conn.get_status()

            if status['status'] == 'connected':
                summary['connected'] += 1
            else:
                summary['disconnected'] += 1

            # Hole letzte BMS-Daten
            parser = self.bms_parsers.get(conn_id)
            if parser and parser.last_data:
                bms_data = parser.last_data

                summary['total_capacity'] += bms_data.capacity_full
                soc_sum += bms_data.soc

                summary['bms_details'][conn_id] = {
                    'status': status['status'],
                    'voltage': bms_data.total_voltage,
                    'current': bms_data.current,
                    'soc': bms_data.soc,
                    'temp_avg': bms_data.temp_avg,
                    'alarms': len(self.active_alarms.get(conn_id, []))
                }

                summary['total_alarms'] += len(self.active_alarms.get(conn_id, []))

        # Durchschnittliche SoC
        if summary['total_bms'] > 0:
            summary['total_soc_avg'] = soc_sum // summary['total_bms']

        return summary


# ========================================================================
# STANDALONE TEST
# ========================================================================

def test_bms_plugin():
    """Testet BMS Plugin (benötigt BMS-Verbindung!)"""
    print("="*60)
    print("  BMS Monitor Plugin - Standalone Test")
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
        'poll_interval': 5.0,
        'bms_protocol': 'JBD',
        'alarm_voltage_min': 3.0,
        'alarm_voltage_max': 3.65,
        'alarm_temp_max': 45.0
    }

    # Erstelle Plugin
    plugin = BMSMonitorPlugin(MockApp(), config)

    try:
        # Initialisiere
        plugin.initialize()

        # Starte
        plugin.startup()

        # Laufe 30 Sekunden
        plugin.is_running = True
        for i in range(6):
            plugin.execute()
            if not plugin.is_running:
                break
            time.sleep(5.0)

            # Zeige Summary
            summary = plugin.get_bms_summary()
            print(f"\n  📊 BMS Summary:")
            print(f"     Connected: {summary['connected']}/{summary['total_bms']}")
            print(f"     Avg SoC: {summary['total_soc_avg']}%")
            print(f"     Total Alarms: {summary['total_alarms']}")

    except KeyboardInterrupt:
        print("\n  ⏹️  Test abgebrochen")
    except Exception as e:
        print(f"  ✗ Test-Fehler: {e}")
    finally:
        plugin.is_running = False
        plugin.shutdown()


if __name__ == "__main__":
    test_bms_plugin()
