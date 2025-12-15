"""
PV Plugin v1.0.0
Solar PV Monitoring Card für SolarAssistant

📁 SPEICHERORT: modules/plugins/pv_plugin.py

Features:
- Anzeige von PV1/PV2 Spannung/Power
- AUX Power
- Gesamt PV-Leistung
- Tagesertrag
- Moderne UX: Gauges für Power, Farben (grün >0W)

Changelog:
- v1.0.0 (2025-12-04): Initiale Version mit MQTT-Integration.
"""

from module_manager import BaseModule
from typing import Any, Dict  # Fix: Import Any und Dict
import tkinter as tk
from tkinter import ttk

class PvPlugin(BaseModule):
    """
    PV Plugin v1.0.0
    
    Monitort PV-Daten via MQTT.
    """
    
    NAME = "pv"
    VERSION = "1.0.0"
    DESCRIPTION = "Solar PV Monitoring"
    AUTHOR = "TwinCAT Team"
    DEPENDENCIES = ['mqtt_integration']
    
    SCHEMA = {
        "mqtt_prefix": {
            "type": "string",
            "label": "MQTT Prefix",
            "default": "solar_assistant/inverter_1",
            "description": "Basis-Topic für PV-Daten"
        }
    }
    
    def __init__(self):
        super().__init__()
        self.mqtt = None
        self.values = {}  # Cache für Werte
    
	def initialize(self, app_context: Any):
		super().initialize(app_context)
		self.app = app_context                           # <-- HINZUFÜGEN!
		self.mqtt = app_context.module_manager.get_module('mqtt_integration')
		
    def create_card_content(self, parent: tk.Widget, card_data: dict):
        """Erstellt PV-Card Inhalt"""
        prefix = card_data.get('mqtt_prefix', 'solar_assistant/inverter_1')
		self.root_widget = parent                        # <-- HINZUFÜGEN!
		
        # Subscribe zu Topics (Push-Updates)
        topics = [
            f"{prefix}/pv_voltage_1/state",  # PV1 Voltage
            f"{prefix}/pv_power_1/state",     # PV1 Power
            f"{prefix}/pv_voltage_2/state",  # PV2 Voltage
            f"{prefix}/pv_power_2/state",     # PV2 Power
            f"{prefix}/auxiliary_pv_power/state",  # AUX Power
            f"{prefix}/pv_power/state",       # Gesamt PV
            f"{prefix}/total_pv_day_energy/state"  # Tagesertrag (angenommen, passe ggf. an)
        ]
        
        for topic in topics:
            self.mqtt.subscribe(topic, self._update_value)
        
        # UI Layout
        frame = tk.Frame(parent, bg=self.app.gui.colors['card_bg'])
        frame.pack(fill=tk.BOTH, expand=True)
        
        # Header
        tk.Label(frame, text="☀️ PV Monitoring", font=('Segoe UI', 14, 'bold'), bg=frame['bg']).pack(pady=5)
        
        # PV1
        pv1_frame = tk.Frame(frame, bg=frame['bg'])
        pv1_frame.pack(fill=tk.X, pady=5)
        tk.Label(pv1_frame, text="PV1:", bg=frame['bg']).pack(side=tk.LEFT)
        self.pv1_volt = tk.Label(pv1_frame, text="Voltage: -- V", bg=frame['bg'])
        self.pv1_volt.pack(side=tk.LEFT, padx=10)
        self.pv1_power = tk.Label(pv1_frame, text="Power: -- W", bg=frame['bg'])
        self.pv1_power.pack(side=tk.LEFT, padx=10)
        
        # PV2
        pv2_frame = tk.Frame(frame, bg=frame['bg'])
        pv2_frame.pack(fill=tk.X, pady=5)
        tk.Label(pv2_frame, text="PV2:", bg=frame['bg']).pack(side=tk.LEFT)
        self.pv2_volt = tk.Label(pv2_frame, text="Voltage: -- V", bg=frame['bg'])
        self.pv2_volt.pack(side=tk.LEFT, padx=10)
        self.pv2_power = tk.Label(pv2_frame, text="Power: -- W", bg=frame['bg'])
        self.pv2_power.pack(side=tk.LEFT, padx=10)
        
        # AUX & Gesamt
        aux_total_frame = tk.Frame(frame, bg=frame['bg'])
        aux_total_frame.pack(fill=tk.X, pady=5)
        self.aux_power = tk.Label(aux_total_frame, text="AUX Power: -- W", bg=frame['bg'])
        self.aux_power.pack(side=tk.LEFT, padx=10)
        self.total_pv = tk.Label(aux_total_frame, text="Gesamt PV: -- W", bg=frame['bg'])
        self.total_pv.pack(side=tk.LEFT, padx=10)
        self.day_yield = tk.Label(aux_total_frame, text="Tagesertrag: -- kWh", bg=frame['bg'])
        self.day_yield.pack(side=tk.LEFT, padx=10)
    
    def _update_value(self, topic: str, value: Any):
        """Update Callback von MQTT"""
        key = topic.split('/')[-2]  # z.B. 'pv_voltage_1'
        self.values[key] = value
        
        # Update UI (im Main-Thread)
        self.root_widget.after(0, self._refresh_ui)
    
    def _refresh_ui(self):
        """Refresht Card-UI"""
        # PV1
        self.pv1_volt.config(text=f"Voltage: {self.values.get('pv_voltage_1', '--')} V")
        power1 = self.values.get('pv_power_1', 0)
        self.pv1_power.config(text=f"Power: {power1} W", fg='green' if power1 > 0 else 'red')
        
        # PV2
        self.pv2_volt.config(text=f"Voltage: {self.values.get('pv_voltage_2', '--')} V")
        power2 = self.values.get('pv_power_2', 0)
        self.pv2_power.config(text=f"Power: {power2} W", fg='green' if power2 > 0 else 'red')
        
        # AUX
        aux = self.values.get('auxiliary_pv_power', 0)
        self.aux_power.config(text=f"AUX Power: {aux} W", fg='green' if aux > 0 else 'red')
        
        # Gesamt PV
        total = self.values.get('pv_power', 0)
        self.total_pv.config(text=f"Gesamt PV: {total} W", fg='green' if total > 0 else 'red')
        
        # Tagesertrag
        yield_day = self.values.get('total_pv_day_energy', 0) / 1000  # Annahme Wh -> kWh
        self.day_yield.config(text=f"Tagesertrag: {yield_day:.2f} kWh")
    
    def get_schema(self) -> Dict:
        return self.SCHEMA

def register(module_manager):
    module_manager.register_module(
        PvPlugin.NAME,
        PvPlugin.VERSION,
        PvPlugin.DESCRIPTION,
        PvPlugin,
        author=PvPlugin.AUTHOR,
        dependencies=PvPlugin.DEPENDENCIES
    )