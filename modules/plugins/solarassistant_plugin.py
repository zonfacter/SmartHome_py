"""
SolarAssistant Plugin v2.0.0
Mit JSON-Schema für dynamische Eingabemaske
"""

from module_manager import BaseModule
from typing import Any, Dict
import tkinter as tk


class SolarAssistant(BaseModule):
    """SolarAssistant Plugin mit Schema"""
    
    NAME = "solarassistant"
    VERSION = "2.0.0"
    DESCRIPTION = "PV-Anlagen-Monitoring mit Schema"
    AUTHOR = "TwinCAT Team"
    
    # ⭐ SCHEMA für Card-Editor
    SCHEMA = {
        "mqtt_topic_prefix": {
            "type": "string",
            "label": "MQTT Topic-Prefix",
            "description": "Basis-Topic für SolarAssistant MQTT-Daten",
            "placeholder": "z.B. solar_assistant",
            "default": "solar_assistant"
        },
        "pv_power_topic": {
            "type": "string",
            "label": "PV-Leistung Topic",
            "description": "MQTT-Topic für PV-Leistung",
            "placeholder": "z.B. solar/pv/power",
            "default": "solar/pv/power"
        },
        "battery_soc_topic": {
            "type": "string",
            "label": "Batterie-SOC Topic (optional)",
            "description": "MQTT-Topic für Batterie-Ladestand",
            "required": False,
            "placeholder": "z.B. solar/battery/soc"
        },
        "grid_power_topic": {
            "type": "string",
            "label": "Netz-Leistung Topic (optional)",
            "description": "MQTT-Topic für Netz-Leistung",
            "required": False,
            "placeholder": "z.B. solar/grid/power"
        },
        "home_consumption_topic": {
            "type": "string",
            "label": "Hausverbrauch Topic (optional)",
            "description": "MQTT-Topic für Hausverbrauch",
            "required": False,
            "placeholder": "z.B. solar/home/power"
        },
        "show_battery": {
            "type": "boolean",
            "label": "Batterie anzeigen",
            "description": "Batterie-Informationen auf Card anzeigen",
            "default": True
        },
        "show_grid": {
            "type": "boolean",
            "label": "Netz anzeigen",
            "description": "Netz-Informationen auf Card anzeigen",
            "default": True
        }
    }
    
    def __init__(self):
        super().__init__()
        self.mqtt = None
    
    def initialize(self, app_context: Any):
        """Initialisiert Plugin"""
        super().initialize(app_context)
        print(f"  ⚡ {self.NAME} v{self.VERSION} initialisiert")
    
    def create_card_content(self, parent: tk.Widget, card_data: dict):
        """Erstellt Card-Inhalt"""
        icon = card_data.get('icon', '☀️')
        name = card_data.get('name', 'PV-Anlage')
        
        tk.Label(
            parent,
            text=f"{icon} {name}",
            font=('Segoe UI', 14, 'bold'),
            bg='#f0f0f0'
        ).pack(pady=10)
        
        # PV-Leistung
        tk.Label(
            parent,
            text="PV: ---- W",
            font=('Segoe UI', 16, 'bold'),
            bg='#f0f0f0',
            fg='#FF9800'
        ).pack(pady=5)
        
        # Batterie
        if card_data.get('show_battery', True):
            tk.Label(
                parent,
                text="🔋 ---%",
                font=('Segoe UI', 12),
                bg='#f0f0f0'
            ).pack(pady=2)
        
        # Netz
        if card_data.get('show_grid', True):
            tk.Label(
                parent,
                text="⚡ ---- W",
                font=('Segoe UI', 12),
                bg='#f0f0f0'
            ).pack(pady=2)
    
    def get_schema(self) -> Dict:
        """Gibt Schema zurück"""
        return self.SCHEMA


def register(module_manager):
    """Registriert Modul"""
    module_manager.register_module(
        SolarAssistant.NAME,
        SolarAssistant.VERSION,
        SolarAssistant.DESCRIPTION,
        SolarAssistant,
        author=SolarAssistant.AUTHOR
    )
