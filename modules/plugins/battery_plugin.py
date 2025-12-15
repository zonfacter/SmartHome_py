"""
Battery Plugin v1.0.0
Batterie-Monitoring Card für SolarAssistant

📁 SPEICHERORT: modules/plugins/battery_plugin.py

Features:
- Anzeige von Spannung, Temp, Strom (A/W), SoC (Progress-Bar)
- Moderne UX: Farbige Progress-Bar für SoC (rot <20%, gelb <50%, grün >50%)

Changelog:
- v1.0.0 (2025-12-04): Initiale Version mit MQTT-Integration.
"""

from module_manager import BaseModule
from typing import Any, Dict  # Fix: Import Any und Dict
import tkinter as tk
from tkinter import ttk

class BatteryPlugin(BaseModule):
    """
    Battery Plugin v1.0.0
    
    Monitort Batterie-Daten via MQTT.
    """
    
    NAME = "battery"
    VERSION = "1.0.0"
    DESCRIPTION = "Batterie Monitoring"
    AUTHOR = "TwinCAT Team"
    DEPENDENCIES = ['mqtt_integration']
    
    SCHEMA = {
        "mqtt_prefix": {
            "type": "string",
            "label": "MQTT Prefix",
            "default": "solar_assistant/inverter_1",
            "description": "Basis-Topic für Batterie-Daten"
        }
    }
    
    def __init__(self):
        super().__init__()
        self.mqtt = None
        self.values = {}
    
	def	initialize(self, app_context: Any):
		super().initialize(app_context)
		self.app = app_context	# <-- FEHLTE!
		self.mqtt = app_context.module_manager.get_module('mqtt_integration')

    def create_card_content(self, parent: tk.Widget, card_data: dict):
        """Erstellt Battery-Card Inhalt"""
		prefix = card_data.get('mqtt_prefix', 'solar_assistant/inverter_1')
		self.root_widget = parent                        # <-- FEHLTE!
        # Subscribe
        topics = [
            f"{prefix}/battery_voltage/state",
            f"{prefix}/battery_temperature/state",
            f"{prefix}/battery_current/state",  # A
            f"{prefix}/battery_power/state",    # W (berechnet? Oder direkt)
            f"{prefix}/battery_state_of_charge/state"  # SoC
        ]
        
        for topic in topics:
            self.mqtt.subscribe(topic, self._update_value)
        
        # UI
        frame = tk.Frame(parent, bg=self.app.gui.colors['card_bg'])
        frame.pack(fill=tk.BOTH, expand=True)
        
        tk.Label(frame, text="🔋 Batterie", font=('Segoe UI', 14, 'bold'), bg=frame['bg']).pack(pady=5)
        
        # SoC Progress
        self.soc_progress = ttk.Progressbar(frame, orient='horizontal', length=200, mode='determinate')
        self.soc_progress.pack(pady=5)
        self.soc_label = tk.Label(frame, text="SoC: --%", bg=frame['bg'])
        self.soc_label.pack()
        
        # Details
        details = tk.Frame(frame, bg=frame['bg'])
        details.pack(fill=tk.X, pady=5)
        self.volt = tk.Label(details, text="Spannung: -- V", bg=frame['bg'])
        self.volt.pack(side=tk.LEFT, padx=10)
        self.temp = tk.Label(details, text="Temp: -- °C", bg=frame['bg'])
        self.temp.pack(side=tk.LEFT, padx=10)
        self.current = tk.Label(details, text="Strom: -- A", bg=frame['bg'])
        self.current.pack(side=tk.LEFT, padx=10)
        self.power = tk.Label(details, text="Leistung: -- W", bg=frame['bg'])
        self.power.pack(side=tk.LEFT, padx=10)
    
    def _update_value(self, topic: str, value: Any):
        key = topic.split('/')[-2]
        self.values[key] = value
        self.root_widget.after(0, self._refresh_ui)
    
    def _refresh_ui(self):
        """Refreshes UI"""
        soc = self.values.get('battery_state_of_charge', 0)
        self.soc_progress['value'] = soc
        color = 'red' if soc < 20 else 'orange' if soc < 50 else 'green'
        self.soc_progress['style'] = f"{color}.Horizontal.TProgressbar"  # Assumed theme support
        self.soc_label.config(text=f"SoC: {soc}%")
        
        self.volt.config(text=f"Spannung: {self.values.get('battery_voltage', '--')} V")
        self.temp.config(text=f"Temp: {self.values.get('battery_temperature', '--')} °C")
        self.current.config(text=f"Strom: {self.values.get('battery_current', '--')} A")
        self.power.config(text=f"Leistung: {self.values.get('battery_power', '--')} W")
    
    def get_schema(self) -> Dict:
        return self.SCHEMA

def register(module_manager):
    module_manager.register_module(
        BatteryPlugin.NAME,
        BatteryPlugin.VERSION,
        BatteryPlugin.DESCRIPTION,
        BatteryPlugin,
        author=BatteryPlugin.AUTHOR,
        dependencies=BatteryPlugin.DEPENDENCIES
    )