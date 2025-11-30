"""
Gauge Plugin
Version: 1.0.0
Messwertsanzeige mit Balken
"""

from typing import Dict, Any
import tkinter as tk


class GaugePlugin:
    """Gauge Card Plugin"""
    
    NAME = "gauge"
    VERSION = "1.0.0"
    DESCRIPTION = "Messwertsanzeige (Druck, Durchfluss, etc.)"
    ICON = "📊"
    
    def __init__(self):
        self.plc = None
    
    def initialize(self, plc_module):
        """Initialisiert Plugin"""
        self.plc = plc_module
    
    def create_card(self, parent: tk.Widget, card_id: str, config: Dict, colors: Dict) -> Dict:
        """Erstellt Gauge-Card"""
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
        name = tk.Label(header, text=config.get('name', 'Gauge'),
                       font=('Segoe UI', 14, 'bold'),
                       bg=colors['card_bg'], fg=colors['text_dark'])
        name.pack(side=tk.LEFT, padx=15)
        
        # Wert-Anzeige
        unit = config.get('unit', '')
        value_label = tk.Label(content, text=f"0.0 {unit}",
                              font=('Segoe UI', 32, 'bold'),
                              bg=colors['card_bg'], fg=colors['primary'])
        value_label.pack(pady=20)
        
        # Progress Bar (Canvas)
        bar_frame = tk.Frame(content, bg=colors['card_bg'])
        bar_frame.pack(fill=tk.X, pady=10)
        
        bar_canvas = tk.Canvas(bar_frame, width=280, height=40,
                              bg='#f0f0f0', highlightthickness=0)
        bar_canvas.pack()
        
        # Balken
        bar = bar_canvas.create_rectangle(0, 0, 0, 40, fill=colors['primary'], outline='')
        
        # Min/Max Labels
        min_val = config.get('min_value', 0)
        max_val = config.get('max_value', 100)
        
        range_label = tk.Label(content, text=f"Bereich: {min_val} - {max_val} {unit}",
                              font=('Segoe UI', 9),
                              bg=colors['card_bg'], fg=colors['text_light'])
        range_label.pack()
        
        return {
            'frame': card,
            'value_label': value_label,
            'bar_canvas': bar_canvas,
            'bar': bar,
            'min_value': min_val,
            'max_value': max_val,
            'unit': unit
        }
    
    def update_display(self, widgets: Dict, value: Any, colors: Dict):
        """Aktualisiert Anzeige"""
        if value is None:
            value = 0
        
        # Wert anzeigen
        unit = widgets.get('unit', '')
        widgets['value_label'].config(text=f"{value:.1f} {unit}")
        
        # Balken aktualisieren
        min_val = widgets.get('min_value', 0)
        max_val = widgets.get('max_value', 100)
        
        # Prozent berechnen
        if max_val > min_val:
            percent = (value - min_val) / (max_val - min_val)
            percent = max(0, min(1, percent))  # Clamp 0-1
        else:
            percent = 0
        
        # Balken-Breite
        bar_width = int(280 * percent)
        
        # Farbe basierend auf Prozent
        if percent < 0.5:
            color = colors['success']
        elif percent < 0.8:
            color = colors['warning']
        else:
            color = colors['danger']
        
        # Update Balken
        widgets['bar_canvas'].coords(widgets['bar'], 0, 0, bar_width, 40)
        widgets['bar_canvas'].itemconfig(widgets['bar'], fill=color)
    
    def get_config_fields(self) -> list:
        """Gibt Konfigurations-Felder zurück"""
        return [
            {'name': 'variable', 'type': 'variable', 'label': 'Variable'},
            {'name': 'min_value', 'type': 'number', 'label': 'Min-Wert', 'default': 0},
            {'name': 'max_value', 'type': 'number', 'label': 'Max-Wert', 'default': 100},
            {'name': 'unit', 'type': 'text', 'label': 'Einheit', 'default': ''},
            {'name': 'var_type', 'type': 'choice', 'label': 'Variablen-Typ',
             'choices': ['REAL', 'INT', 'DINT']}
        ]


def register(module_manager):
    """Registriert Plugin"""
    module_manager.register_module(
        GaugePlugin.NAME,
        GaugePlugin.VERSION,
        GaugePlugin.DESCRIPTION,
        GaugePlugin
    )
