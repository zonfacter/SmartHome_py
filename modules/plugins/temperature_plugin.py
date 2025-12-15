"""
Temperature Plugin v2.1.0
Mit Live-Update vom PLC
"""

from module_manager import BaseModule
from typing import Any, Dict
import tkinter as tk


class Temperature(BaseModule):
    """Temperature Plugin mit Live-Update"""
    
    NAME = "temperature"
    VERSION = "2.1.0"
    DESCRIPTION = "Temperatur-Anzeige mit Live-Update"
    AUTHOR = "TwinCAT Team"
    
    # Schema (unverändert)
    SCHEMA = {
        "variable": {
            "type": "plc_variable",
            "label": "Temperatur-Variable",
            "description": "PLC-Variable mit Temperaturwert",
            "required": True,
            "plc_type": "REAL",
            "placeholder": "z.B. MAIN.fTemperatur"
        },
        "unit": {
            "type": "choice",
            "label": "Einheit",
            "description": "Temperatur-Einheit",
            "choices": [
                {"value": "°C", "label": "Celsius (°C)"},
                {"value": "°F", "label": "Fahrenheit (°F)"},
                {"value": "K", "label": "Kelvin (K)"}
            ],
            "default": "°C"
        },
        "decimals": {
            "type": "integer",
            "label": "Nachkommastellen",
            "description": "Anzahl Nachkommastellen",
            "min": 0,
            "max": 3,
            "default": 1,
            "step": 1
        }
    }
    
    def __init__(self):
        super().__init__()
        self.plc = None
        self.card_widgets = {}
    
    def initialize(self, app_context: Any):
        """Initialisiert Plugin"""
        super().initialize(app_context)
        print(f"  ⚡ {self.NAME} v{self.VERSION} initialisiert")
    
    def create_card_content(self, parent: tk.Widget, card_data: dict):
        """Erstellt Card-Inhalt"""
        card_id = card_data.get('_card_id', 'unknown')
        
        icon = card_data.get('icon', '🌡️')
        name = card_data.get('name', 'Temperatur')
        unit = card_data.get('unit', '°C')
        
        tk.Label(
            parent,
            text=f"{icon} {name}",
            font=('Segoe UI', 14, 'bold'),
            bg='#f0f0f0'
        ).pack(pady=10)
        
        # ⭐ Temperatur-Anzeige mit Live-Update
        temp_label = tk.Label(
            parent,
            text=f"--.- {unit}",
            font=('Segoe UI', 24, 'bold'),
            bg='#f0f0f0',
            fg='#2196F3'
        )
        temp_label.pack(pady=10)
        
        # Speichere für Update
        self.card_widgets[card_id] = {
            'label': temp_label,
            'variable': card_data.get('variable'),
            'unit': unit,
            'decimals': card_data.get('decimals', 1)
        }
    
    def update_card(self, card_id: str, card_data: dict):
        """Aktualisiert Temperatur-Anzeige"""
        if card_id not in self.card_widgets:
            return
        
        widgets = self.card_widgets[card_id]
        variable = widgets['variable']
        label = widgets['label']
        unit = widgets['unit']
        decimals = widgets['decimals']
        
        if not variable or not self.plc or not self.plc.connected:
            label.config(text=f"--.- {unit}", fg='gray')
            return
        
        try:
            import pyads
            value = self.plc.read_by_name(variable, pyads.PLCTYPE_REAL)
            formatted = f"{value:.{decimals}f} {unit}"
            
            # Farbe basierend auf Temperatur
            if value < 15:
                color = '#2196F3'  # Blau (kalt)
            elif value < 25:
                color = '#4CAF50'  # Grün (angenehm)
            else:
                color = '#FF5722'  # Rot (warm)
            
            label.config(text=formatted, fg=color)
        
        except Exception as e:
            label.config(text=f"Fehler", fg='#FF5722')
    
    def get_schema(self) -> Dict:
        """Gibt Schema zurück"""
        return self.SCHEMA
    
    def shutdown(self):
        """Cleanup"""
        self.card_widgets.clear()


def register(module_manager):
    """Registriert Modul"""
    module_manager.register_module(
        Temperature.NAME,
        Temperature.VERSION,
        Temperature.DESCRIPTION,
        Temperature,
        author=Temperature.AUTHOR
    )
