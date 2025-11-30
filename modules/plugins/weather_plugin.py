"""
Weather Plugin
Version: 1.0.0
Wetter-Anzeige mit mehreren Werten
"""

from typing import Dict, Any
import tkinter as tk


class WeatherPlugin:
    """Weather Card Plugin"""
    
    NAME = "weather"
    VERSION = "1.0.0"
    DESCRIPTION = "Wetter-Anzeige (Temp, Feuchte, Wind)"
    ICON = "🌤️"
    
    def __init__(self):
        self.plc = None
    
    def initialize(self, plc_module):
        """Initialisiert Plugin"""
        self.plc = plc_module
    
    def create_card(self, parent: tk.Widget, card_id: str, config: Dict, colors: Dict) -> Dict:
        """Erstellt Weather-Card"""
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
        
        # Name/Location
        location = config.get('location', 'Wetter')
        name = tk.Label(header, text=location,
                       font=('Segoe UI', 14, 'bold'),
                       bg=colors['card_bg'], fg=colors['text_dark'])
        name.pack(side=tk.LEFT, padx=15)
        
        # Wetter-Daten Container
        data_frame = tk.Frame(content, bg=colors['card_bg'])
        data_frame.pack(pady=20)
        
        # Temperatur
        temp_frame = tk.Frame(data_frame, bg=colors['card_bg'])
        temp_frame.pack(pady=5)
        
        tk.Label(temp_frame, text="🌡️",
                font=('Segoe UI', 20), bg=colors['card_bg']).pack(side=tk.LEFT)
        
        temp_label = tk.Label(temp_frame, text="--.-°C",
                             font=('Segoe UI', 24, 'bold'),
                             bg=colors['card_bg'], fg=colors['primary'])
        temp_label.pack(side=tk.LEFT, padx=10)
        
        # Luftfeuchtigkeit
        humidity_frame = tk.Frame(data_frame, bg=colors['card_bg'])
        humidity_frame.pack(pady=5)
        
        tk.Label(humidity_frame, text="💧",
                font=('Segoe UI', 20), bg=colors['card_bg']).pack(side=tk.LEFT)
        
        humidity_label = tk.Label(humidity_frame, text="--%",
                                  font=('Segoe UI', 18),
                                  bg=colors['card_bg'], fg=colors['text_dark'])
        humidity_label.pack(side=tk.LEFT, padx=10)
        
        # Wind (optional)
        wind_frame = tk.Frame(data_frame, bg=colors['card_bg'])
        wind_frame.pack(pady=5)
        
        tk.Label(wind_frame, text="💨",
                font=('Segoe UI', 20), bg=colors['card_bg']).pack(side=tk.LEFT)
        
        wind_label = tk.Label(wind_frame, text="-- km/h",
                             font=('Segoe UI', 18),
                             bg=colors['card_bg'], fg=colors['text_dark'])
        wind_label.pack(side=tk.LEFT, padx=10)
        
        return {
            'frame': card,
            'temp_label': temp_label,
            'humidity_label': humidity_label,
            'wind_label': wind_label
        }
    
    def update_display(self, widgets: Dict, values: Dict, colors: Dict):
        """
        Aktualisiert Anzeige
        
        Args:
            values: Dict mit 'temp', 'humidity', 'wind'
        """
        if not isinstance(values, dict):
            return
        
        # Temperatur
        temp = values.get('temp')
        if temp is not None:
            widgets['temp_label'].config(text=f"{temp:.1f}°C")
        
        # Luftfeuchtigkeit
        humidity = values.get('humidity')
        if humidity is not None:
            widgets['humidity_label'].config(text=f"{humidity:.0f}%")
        
        # Wind
        wind = values.get('wind')
        if wind is not None:
            widgets['wind_label'].config(text=f"{wind:.1f} km/h")
    
    def read_values(self, config: Dict) -> Dict:
        """Liest Wetter-Werte vom PLC"""
        import pyads
        
        values = {}
        
        if self.plc:
            # Temperatur
            temp_var = config.get('temp_var')
            if temp_var:
                temp = self.plc.read_by_name(temp_var, pyads.PLCTYPE_REAL)
                if temp is not None:
                    values['temp'] = temp
            
            # Luftfeuchtigkeit
            humidity_var = config.get('humidity_var')
            if humidity_var:
                humidity = self.plc.read_by_name(humidity_var, pyads.PLCTYPE_REAL)
                if humidity is not None:
                    values['humidity'] = humidity
            
            # Wind (optional)
            wind_var = config.get('wind_var')
            if wind_var:
                wind = self.plc.read_by_name(wind_var, pyads.PLCTYPE_REAL)
                if wind is not None:
                    values['wind'] = wind
        
        return values
    
    def get_config_fields(self) -> list:
        """Gibt Konfigurations-Felder zurück"""
        return [
            {'name': 'location', 'type': 'text', 'label': 'Standort'},
            {'name': 'temp_var', 'type': 'variable', 'label': 'Temperatur Variable'},
            {'name': 'humidity_var', 'type': 'variable', 'label': 'Luftfeuchte Variable'},
            {'name': 'wind_var', 'type': 'variable', 'label': 'Wind Variable (optional)'},
            {'name': 'api_key', 'type': 'password', 'label': 'API Key (optional)'}
        ]


def register(module_manager):
    """Registriert Plugin"""
    module_manager.register_module(
        WeatherPlugin.NAME,
        WeatherPlugin.VERSION,
        WeatherPlugin.DESCRIPTION,
        WeatherPlugin
    )
