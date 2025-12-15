"""
Weather Plugin v2.0.0
Mit JSON-Schema für dynamische Eingabemaske
"""

from module_manager import BaseModule
from typing import Any, Dict
import tkinter as tk


class Weather(BaseModule):
    """Weather Plugin mit Schema"""
    
    NAME = "weather"
    VERSION = "2.0.0"
    DESCRIPTION = "Wetter-Anzeige mit Schema"
    AUTHOR = "TwinCAT Team"
    
    # ⭐ SCHEMA für Card-Editor
    SCHEMA = {
        "location": {
            "type": "string",
            "label": "Standort",
            "description": "Standort für Wetterdaten",
            "placeholder": "z.B. Haltern am See",
            "default": "Haltern am See"
        },
        "temp_variable": {
            "type": "plc_variable",
            "label": "Temperatur-Variable (optional)",
            "description": "PLC-Variable für Temperatur",
            "required": False,
            "plc_type": "REAL",
            "placeholder": "z.B. MAIN.fAussenTemp"
        },
        "humidity_variable": {
            "type": "plc_variable",
            "label": "Luftfeuchte-Variable (optional)",
            "description": "PLC-Variable für Luftfeuchtigkeit",
            "required": False,
            "plc_type": "REAL",
            "placeholder": "z.B. MAIN.fAussenFeuchte"
        },
        "wind_variable": {
            "type": "plc_variable",
            "label": "Wind-Variable (optional)",
            "description": "PLC-Variable für Windgeschwindigkeit",
            "required": False,
            "plc_type": "REAL",
            "placeholder": "z.B. MAIN.fWindSpeed"
        },
        "api_key": {
            "type": "password",
            "label": "API-Key (optional)",
            "description": "OpenWeatherMap API-Key für Live-Daten",
            "required": False,
            "placeholder": "Leer lassen für PLC-Daten"
        },
        "update_interval": {
            "type": "integer",
            "label": "Update-Intervall (Minuten)",
            "description": "Wie oft Live-Daten aktualisiert werden",
            "min": 5,
            "max": 60,
            "default": 15,
            "step": 5
        }
    }
    
    def __init__(self):
        super().__init__()
        self.plc = None
    
    def initialize(self, app_context: Any):
        """Initialisiert Plugin"""
        super().initialize(app_context)
        print(f"  ⚡ {self.NAME} v{self.VERSION} initialisiert")
    
    def create_card_content(self, parent: tk.Widget, card_data: dict):
        """Erstellt Card-Inhalt"""
        icon = card_data.get('icon', '🌤️')
        name = card_data.get('name', 'Wetter')
        location = card_data.get('location', 'N/A')
        
        tk.Label(
            parent,
            text=f"{icon} {name}",
            font=('Segoe UI', 14, 'bold'),
            bg='#f0f0f0'
        ).pack(pady=10)
        
        tk.Label(
            parent,
            text=location,
            font=('Segoe UI', 10),
            bg='#f0f0f0',
            fg='gray'
        ).pack()
        
        # Wetter-Info
        tk.Label(
            parent,
            text="--.- °C | --% | -- km/h",
            font=('Segoe UI', 12),
            bg='#f0f0f0'
        ).pack(pady=10)
    
    def get_schema(self) -> Dict:
        """Gibt Schema zurück"""
        return self.SCHEMA


def register(module_manager):
    """Registriert Modul"""
    module_manager.register_module(
        Weather.NAME,
        Weather.VERSION,
        Weather.DESCRIPTION,
        Weather,
        author=Weather.AUTHOR
    )
