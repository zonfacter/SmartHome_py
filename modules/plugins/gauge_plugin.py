"""
Gauge Plugin v2.0.0
Mit JSON-Schema für dynamische Eingabemaske
"""

from module_manager import BaseModule
from typing import Any, Dict
import tkinter as tk


class Gauge(BaseModule):
    """Gauge Plugin mit Schema"""
    
    NAME = "gauge"
    VERSION = "2.0.0"
    DESCRIPTION = "Messanzeige mit Schema"
    AUTHOR = "TwinCAT Team"
    
    # ⭐ SCHEMA für Card-Editor
    SCHEMA = {
        "variable": {
            "type": "plc_variable",
            "label": "Messwert-Variable",
            "description": "PLC-Variable mit Messwert",
            "required": True,
            "plc_type": "REAL",
            "placeholder": "z.B. MAIN.fDruck"
        },
        "min_value": {
            "type": "float",
            "label": "Minimum",
            "description": "Minimaler Anzeigewert",
            "default": 0.0
        },
        "max_value": {
            "type": "float",
            "label": "Maximum",
            "description": "Maximaler Anzeigewert",
            "default": 100.0
        },
        "unit": {
            "type": "string",
            "label": "Einheit",
            "description": "Anzeigeeinheit (z.B. bar, l/min, kW)",
            "placeholder": "z.B. bar",
            "default": ""
        },
        "decimals": {
            "type": "integer",
            "label": "Nachkommastellen",
            "description": "Anzahl Nachkommastellen",
            "min": 0,
            "max": 3,
            "default": 1,
            "step": 1
        },
        "warn_threshold": {
            "type": "float",
            "label": "Warngrenze (optional)",
            "description": "Wert ab dem Warnung angezeigt wird",
            "required": False
        },
        "critical_threshold": {
            "type": "float",
            "label": "Kritische Grenze (optional)",
            "description": "Wert ab dem kritischer Zustand angezeigt wird",
            "required": False
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
        icon = card_data.get('icon', '📊')
        name = card_data.get('name', 'Messanzeige')
        
        tk.Label(
            parent,
            text=f"{icon} {name}",
            font=('Segoe UI', 14, 'bold'),
            bg='#f0f0f0'
        ).pack(pady=10)
        
        # Wert-Anzeige
        value_label = tk.Label(
            parent,
            text="--.- ?",
            font=('Segoe UI', 24, 'bold'),
            bg='#f0f0f0',
            fg='#4CAF50'
        )
        value_label.pack(pady=10)
    
    def get_schema(self) -> Dict:
        """Gibt Schema zurück"""
        return self.SCHEMA


def register(module_manager):
    """Registriert Modul"""
    module_manager.register_module(
        Gauge.NAME,
        Gauge.VERSION,
        Gauge.DESCRIPTION,
        Gauge,
        author=Gauge.AUTHOR
    )
