"""
Gen Charge Time Plugin v1.0.0
Uhrzeit-Einstellung für Generator-Ladung (schreibbar)

📁 SPEICHERORT: modules/plugins/gen_charge_time_plugin.py

Features:
- Anzeige/Schreiben von Time Points (z.B. time_point_1 bis 6)
- UX: Timepicker-Dropdowns, Publish bei Änderung

Changelog:
- v1.0.0 (2025-12-04): Initiale Version mit Read/Write via MQTT.
"""

from module_manager import BaseModule
from typing import Any, Dict  # Fix: Import Any und Dict
import tkinter as tk
from tkinter import ttk
import datetime  # Für Time-Validation

class GenChargeTimePlugin(BaseModule):
    """
    Gen Charge Time Plugin v1.0.0
    
    Verwalten von Gen-Lade-Uhrzeiten.
    """
    
    NAME = "gen_charge_time"
    VERSION = "1.0.0"
    DESCRIPTION = "Generator Charge Time Settings"
    AUTHOR = "TwinCAT Team"
    DEPENDENCIES = ['mqtt_integration']
    
    SCHEMA = {
        "mqtt_prefix": {
            "type": "string",
            "label": "MQTT Prefix",
            "default": "solar_assistant/inverter_1",
            "description": "Basis-Topic für Time-Points"
        }
    }
    
    def __init__(self):
        super().__init__()
        self.mqtt = None
        self.values = {}
    
    def initialize(self, app_context: Any):
        super().initialize(app_context)
        self.mqtt = app_context.module_manager.get_module('mqtt_integration')
    
    def create_card_content(self, parent: tk.Widget, card_data: dict):
        """Erstellt Gen-Time Card"""
        prefix = card_data.get('mqtt_prefix', 'solar_assistant/inverter_1')
        
        # Subscribe & Command Topics
        for i in range(1, 7):
            topic = f"{prefix}/time_point_{i}/state"
            cmd_topic = f"{prefix}/time_point_{i}/set"  # Annahme für Write
            self.mqtt.subscribe(topic, lambda t, v, idx=i: self._update_time(idx, v))
        
        # UI
        frame = tk.Frame(parent, bg=self.app.gui.colors['card_bg'])
        frame.pack(fill=tk.BOTH, expand=True)
        
        tk.Label(frame, text="⏰ Gen Charge Times", font=('Segoe UI', 14, 'bold'), bg=frame['bg']).pack(pady=5)
        
        self.time_entries = {}
        for i in range(1, 7):
            row = tk.Frame(frame, bg=frame['bg'])
            row.pack(fill=tk.X, pady=2)
            tk.Label(row, text=f"Time Point {i}:", bg=frame['bg']).pack(side=tk.LEFT)
            entry = ttk.Entry(row, width=10)
            entry.pack(side=tk.LEFT, padx=5)
            entry.bind('<Return>', lambda e, idx=i: self._publish_time(idx, entry.get()))
            self.time_entries[i] = entry
    
    def _update_time(self, idx: int, value: str):
        """Update Entry"""
        self.time_entries[idx].delete(0, tk.END)
        self.time_entries[idx].insert(0, value)
    
    def _publish_time(self, idx: int, value: str):
        """Publish neue Time (mit Validation)"""
        try:
            datetime.datetime.strptime(value, '%H:%M')  # Validate HH:MM
            prefix = "solar_assistant/inverter_1"  # Hardcoded or from card_data
            cmd_topic = f"{prefix}/time_point_{idx}/set"
            self.mqtt.publish(cmd_topic, value)
            print(f"  📤 Published: {cmd_topic} = {value}")
        except ValueError:
            print("  ⚠️ Ungültiges Format: HH:MM")
    
    def get_schema(self) -> Dict:
        return self.SCHEMA

def register(module_manager):
    module_manager.register_module(
        GenChargeTimePlugin.NAME,
        GenChargeTimePlugin.VERSION,
        GenChargeTimePlugin.DESCRIPTION,
        GenChargeTimePlugin,
        author=GenChargeTimePlugin.AUTHOR,
        dependencies=GenChargeTimePlugin.DEPENDENCIES
    )