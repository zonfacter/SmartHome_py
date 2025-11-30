"""
SolarAssistant Plugin
Version: 1.0.0
Zeigt PV-Daten von SolarAssistant via MQTT

📁 SPEICHERORT: modules/plugins/solarassistant_plugin.py

Features:
- PV-Leistung
- Battery-SOC
- Grid-Power
- Tages-Ertrag
- Live-Updates via MQTT
"""

from module_manager import BaseModule
from typing import Any, Dict
import tkinter as tk


class SolarAssistantPlugin(BaseModule):
    """
    SolarAssistant Card Plugin
    
    Zeigt PV-Daten von SolarAssistant
    """
    
    NAME = "solarassistant"
    VERSION = "1.0.0"
    DESCRIPTION = "SolarAssistant PV-Daten"
    AUTHOR = "TwinCAT Team"
    ICON = "☀️"
    
    def __init__(self):
        super().__init__()
        self.mqtt = None
    
    def initialize(self, app_context: Any):
        """Initialisiert Plugin"""
        super().initialize(app_context)
        print(f"  ⚡ {self.NAME} v{self.VERSION} initialisiert")
    
    def create_card(self, parent: tk.Widget, card_id: str, 
                   config: Dict, colors: Dict) -> Dict:
        """
        Erstellt SolarAssistant Card
        
        Config:
            topics: Dict mit MQTT-Topics
                pv_power: PV-Leistung (W)
                battery_soc: Batterie-SOC (%)
                grid_power: Netz-Leistung (W)
                daily_yield: Tages-Ertrag (kWh)
        """
        # Card Frame
        card = tk.Frame(parent, bg=colors['card_bg'], relief=tk.RAISED, 
                       borderwidth=1, cursor='hand2')
        
        # Content
        content = tk.Frame(card, bg=colors['card_bg'])
        content.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Drag Handle
        drag_handle = tk.Frame(content, bg=colors['card_bg'], 
                              relief=tk.FLAT, cursor='fleur')
        drag_handle.pack(fill=tk.X, pady=(0, 10))
        
        drag_label = tk.Label(
            drag_handle,
            text="⋮⋮⋮",
            font=('Segoe UI', 8),
            bg=colors['card_bg'],
            fg=colors.get('text_light', '#999'),
            cursor='fleur'
        )
        drag_label.pack()
        
        # Header
        header = tk.Frame(content, bg=colors['card_bg'])
        header.pack(fill=tk.X, pady=(0, 15))
        
        # Icon
        icon = tk.Label(header, text=self.ICON,
                       font=('Segoe UI', 32), bg=colors['card_bg'])
        icon.pack(side=tk.LEFT)
        
        # Name
        name = tk.Label(header, text=config.get('name', 'SolarAssistant'),
                       font=('Segoe UI', 14, 'bold'),
                       bg=colors['card_bg'], fg=colors['text_dark'])
        name.pack(side=tk.LEFT, padx=15)
        
        # --- PV Power ---
        pv_frame = tk.Frame(content, bg=colors['card_bg'])
        pv_frame.pack(fill=tk.X, pady=5)
        
        tk.Label(pv_frame, text="PV-Leistung:",
                font=('Segoe UI', 10),
                bg=colors['card_bg'], fg=colors['text_light']).pack(side=tk.LEFT)
        
        pv_value = tk.Label(pv_frame, text="--- W",
                           font=('Segoe UI', 16, 'bold'),
                           bg=colors['card_bg'], fg=colors['success'])
        pv_value.pack(side=tk.RIGHT)
        
        # --- Battery SOC ---
        battery_frame = tk.Frame(content, bg=colors['card_bg'])
        battery_frame.pack(fill=tk.X, pady=5)
        
        tk.Label(battery_frame, text="Batterie:",
                font=('Segoe UI', 10),
                bg=colors['card_bg'], fg=colors['text_light']).pack(side=tk.LEFT)
        
        battery_value = tk.Label(battery_frame, text="--- %",
                                font=('Segoe UI', 16, 'bold'),
                                bg=colors['card_bg'], fg=colors['primary'])
        battery_value.pack(side=tk.RIGHT)
        
        # --- Grid Power ---
        grid_frame = tk.Frame(content, bg=colors['card_bg'])
        grid_frame.pack(fill=tk.X, pady=5)
        
        tk.Label(grid_frame, text="Netz:",
                font=('Segoe UI', 10),
                bg=colors['card_bg'], fg=colors['text_light']).pack(side=tk.LEFT)
        
        grid_value = tk.Label(grid_frame, text="--- W",
                             font=('Segoe UI', 16, 'bold'),
                             bg=colors['card_bg'], fg=colors['text_dark'])
        grid_value.pack(side=tk.RIGHT)
        
        # --- Daily Yield ---
        daily_frame = tk.Frame(content, bg=colors['card_bg'])
        daily_frame.pack(fill=tk.X, pady=5)
        
        tk.Label(daily_frame, text="Heute:",
                font=('Segoe UI', 10),
                bg=colors['card_bg'], fg=colors['text_light']).pack(side=tk.LEFT)
        
        daily_value = tk.Label(daily_frame, text="--- kWh",
                              font=('Segoe UI', 16, 'bold'),
                              bg=colors['card_bg'], fg=colors['warning'])
        daily_value.pack(side=tk.RIGHT)
        
        return {
            'frame': card,
            'drag_handle': drag_handle,
            'pv_value': pv_value,
            'battery_value': battery_value,
            'grid_value': grid_value,
            'daily_value': daily_value
        }
    
    def update_display(self, widgets: Dict, values: Dict, colors: Dict):
        """
        Aktualisiert Anzeige
        
        values:
            pv_power: PV-Leistung (W)
            battery_soc: Batterie-SOC (%)
            grid_power: Netz-Leistung (W)
            daily_yield: Tages-Ertrag (kWh)
        """
        # PV Power
        if 'pv_power' in values and values['pv_power'] is not None:
            pv = values['pv_power']
            if isinstance(pv, (int, float)):
                widgets['pv_value'].config(text=f"{pv:.0f} W")
        
        # Battery SOC
        if 'battery_soc' in values and values['battery_soc'] is not None:
            soc = values['battery_soc']
            if isinstance(soc, (int, float)):
                widgets['battery_value'].config(text=f"{soc:.0f} %")
                # Farbe je nach SOC
                if soc > 80:
                    widgets['battery_value'].config(fg=colors['success'])
                elif soc > 30:
                    widgets['battery_value'].config(fg=colors['warning'])
                else:
                    widgets['battery_value'].config(fg='#f44336')
        
        # Grid Power
        if 'grid_power' in values and values['grid_power'] is not None:
            grid = values['grid_power']
            if isinstance(grid, (int, float)):
                # Positiv = Bezug, Negativ = Einspeisung
                if grid > 0:
                    widgets['grid_value'].config(
                        text=f"↓ {grid:.0f} W",
                        fg='#f44336'
                    )
                elif grid < 0:
                    widgets['grid_value'].config(
                        text=f"↑ {abs(grid):.0f} W",
                        fg=colors['success']
                    )
                else:
                    widgets['grid_value'].config(
                        text="0 W",
                        fg=colors['text_light']
                    )
        
        # Daily Yield
        if 'daily_yield' in values and values['daily_yield'] is not None:
            daily = values['daily_yield']
            if isinstance(daily, (int, float)):
                widgets['daily_value'].config(text=f"{daily:.2f} kWh")


def register(module_manager):
    """Registriert Plugin"""
    module_manager.register_module(
        SolarAssistantPlugin.NAME,
        SolarAssistantPlugin.VERSION,
        SolarAssistantPlugin.DESCRIPTION,
        SolarAssistantPlugin,
        author=SolarAssistantPlugin.AUTHOR
    )
