"""
Battery Plugin v1.0.1
Batterie-Monitoring Card für SolarAssistant

📁 SPEICHERORT: modules/plugins/battery_plugin.py

Features:
- Anzeige von Spannung, Temp, Strom (A/W), SoC (Progress-Bar)
- Moderne UX: Farbige Progress-Bar für SoC (rot <20%, gelb <50%, grün >50%)

Changelog:
- v1.0.1 (2025-12-15): Fixed Tab/Space indentation error
- v1.0.0 (2025-12-04): Initiale Version mit MQTT-Integration.
"""

from module_manager import BaseModule
from typing import Any, Dict
import tkinter as tk
from tkinter import ttk

class BatteryPlugin(BaseModule):
    """
    Battery Plugin v1.0.1
    
    Monitort Batterie-Daten via MQTT.
    """
    
    NAME = "battery"
    VERSION = "1.0.1"
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
        self.app = None
        self.root_widget = None
    
    def initialize(self, app_context: Any):
        """Initialisiert das Battery Plugin"""
        super().initialize(app_context)
        self.app = app_context
        self.mqtt = app_context.module_manager.get_module('mqtt_integration')
        print(f"  ⚡ {self.NAME} v{self.VERSION} initialisiert")

    def create_card_content(self, parent: tk.Widget, card_data: dict):
        """Erstellt Battery-Card Inhalt"""
        prefix = card_data.get('mqtt_prefix', 'solar_assistant/inverter_1')
        self.root_widget = parent
        
        # Subscribe
        topics = [
            f"{prefix}/battery_voltage/state",
            f"solar_assistant/total/battery_temperature/state",
            f"solar_assistant/inverter_1/battery_current/state",  # A
            f"solar_assistant/total/battery_power/state",    # W (berechnet? Oder direkt)
            f"solar_assistant/total/battery_state_of_charge/state"  # SoC
        ]
        
        if self.mqtt:
            for topic in topics:
                self.mqtt.subscribe(topic, self._update_value)
        
        # UI - Hole Farben sicher
        colors = self.app.gui.colors if self.app and hasattr(self.app, 'gui') else {}
        bg_color = colors.get('card_bg', '#ffffff')
        
        frame = tk.Frame(parent, bg=bg_color)
        frame.pack(fill=tk.BOTH, expand=True)
        
        tk.Label(frame, text="🔋 Batterie", font=('Segoe UI', 14, 'bold'), 
                 bg=frame['bg'], fg=colors.get('text_dark', '#000000')).pack(pady=5)
        
        # SoC Progress
        self.soc_progress = ttk.Progressbar(frame, orient='horizontal', length=200, mode='determinate')
        self.soc_progress.pack(pady=5)
        self.soc_label = tk.Label(frame, text="SoC: --%", bg=frame['bg'],
                                   fg=colors.get('text_dark', '#000000'))
        self.soc_label.pack()
        
        # Details
        details = tk.Frame(frame, bg=frame['bg'])
        details.pack(fill=tk.X, pady=5)
        self.volt = tk.Label(details, text="Spannung: -- V", bg=frame['bg'],
                              fg=colors.get('text_dark', '#000000'))
        self.volt.pack(side=tk.LEFT, padx=10)
        self.temp = tk.Label(details, text="Temp: -- °C", bg=frame['bg'],
                              fg=colors.get('text_dark', '#000000'))
        self.temp.pack(side=tk.LEFT, padx=10)
        self.current = tk.Label(details, text="Strom: -- A", bg=frame['bg'],
                                 fg=colors.get('text_dark', '#000000'))
        self.current.pack(side=tk.LEFT, padx=10)
        self.power = tk.Label(details, text="Leistung: -- W", bg=frame['bg'],
                               fg=colors.get('text_dark', '#000000'))
        self.power.pack(side=tk.LEFT, padx=10)
    
    def _update_value(self, topic: str, value: Any):
        """Callback für MQTT Updates"""
        key = topic.split('/')[-2]
        self.values[key] = value
        if self.root_widget:
            self.root_widget.after(0, self._refresh_ui)
    
    def _refresh_ui(self):
        """Refreshes UI"""
        try:
            soc = float(self.values.get('battery_state_of_charge', 0))
        except (ValueError, TypeError):
            soc = 0
            
        self.soc_progress['value'] = soc
        # Note: Custom progressbar styles would need to be defined in theme
        self.soc_label.config(text=f"SoC: {soc:.0f}%")
        
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
