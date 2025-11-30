"""
Temperature Plugin
Version: 1.0.0
Temperatur-Anzeige Plugin
"""

from typing import Dict, Any
import tkinter as tk


class TemperaturePlugin:
    """Temperature Card Plugin"""
    
    NAME = "temperature"
    VERSION = "1.0.0"
    DESCRIPTION = "Temperatur-Anzeige"
    ICON = "🌡️"
    
    def __init__(self):
        self.plc = None
    
    def initialize(self, plc_module):
        """Initialisiert Plugin"""
        self.plc = plc_module
    
    def create_card(self, parent: tk.Widget, card_id: str, config: Dict, colors: Dict) -> Dict:
        """Erstellt Temperature-Card"""
        # Card Frame
        card = tk.Frame(parent, bg=colors['card_bg'], relief=tk.RAISED, borderwidth=1)
        
        # Content
        content = tk.Frame(card, bg=colors['card_bg'])
        content.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Header
        header = tk.Frame(content, bg=colors['card_bg'])
        header.pack(fill=tk.X)
        
        # Icon
        icon = tk.Label(header, text=config.get('icon', self.ICON),
                       font=('Segoe UI', 32), bg=colors['card_bg'])
        icon.pack(side=tk.LEFT)
        
        # Name
        name = tk.Label(header, text=config.get('name', 'Temperature'),
                       font=('Segoe UI', 14, 'bold'),
                       bg=colors['card_bg'], fg=colors['text_dark'])
        name.pack(side=tk.LEFT, padx=15)
        
        # Temperatur-Anzeige
        temp_label = tk.Label(content, text="--.-°C",
                             font=('Segoe UI', 48, 'bold'),
                             bg=colors['card_bg'], fg=colors['primary'])
        temp_label.pack(pady=30)
        
        # Einheit
        unit = config.get('unit', 'celsius')
        unit_symbol = "°C" if unit == 'celsius' else "°F"
        
        unit_label = tk.Label(content, text=f"Einheit: {unit_symbol}",
                             font=('Segoe UI', 10),
                             bg=colors['card_bg'], fg=colors['text_light'])
        unit_label.pack()
        
        return {
            'frame': card,
            'temp_label': temp_label,
            'unit': unit
        }
    
    def update_display(self, widgets: Dict, value: Any, colors: Dict):
        """Aktualisiert Anzeige"""
        if value is None:
            widgets['temp_label'].config(text="--.-°C")
            return
        
        # Einheit
        unit = widgets.get('unit', 'celsius')
        
        # Konvertiere wenn nötig
        if unit == 'fahrenheit':
            value = value * 9/5 + 32
            symbol = "°F"
        else:
            symbol = "°C"
        
        # Farbe basierend auf Temperatur
        if value < 15:
            color = '#2196F3'  # Blau
        elif value < 25:
            color = '#4CAF50'  # Grün
        else:
            color = '#FF9800'  # Orange
        
        widgets['temp_label'].config(text=f"{value:.1f}{symbol}", fg=color)
    
    def get_config_fields(self) -> list:
        """Gibt Konfigurations-Felder zurück"""
        return [
            {'name': 'variable', 'type': 'variable', 'label': 'Temperatur Variable'},
            {'name': 'unit', 'type': 'choice', 'label': 'Einheit',
             'choices': ['celsius', 'fahrenheit']}
        ]


def register(module_manager):
    """Registriert Plugin"""
    module_manager.register_module(
        TemperaturePlugin.NAME,
        TemperaturePlugin.VERSION,
        TemperaturePlugin.DESCRIPTION,
        TemperaturePlugin
    )
