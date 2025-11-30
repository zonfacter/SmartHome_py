"""
Update Loop Module  
Version: 2.0.6
Live-Update System für PLC-Werte mit Smart-Update

📁 SPEICHERORT: modules/core/update_loop.py

Features:
- Live-Updates von PLC
- **GEFIXT: Liest OUTPUT statt INPUT (wie v1.2)!**
- Thread-Safe GUI-Updates
- Smart-Update (nur sichtbare Cards)
- Fehler-Handling & Auto-Reconnect
- Konfigurierbare Intervalle
"""

from module_manager import BaseModule
from typing import Any, Dict, Set
import threading
import time
import pyads


class UpdateLoop(BaseModule):
    """
    Update-Loop
    
    Features:
    - Live-Updates von PLC
    - Smart-Update (nur sichtbare Cards)
    - Fehler-Handling & Auto-Reconnect
    - Konfigurierbare Intervalle
    """
    
    NAME = "update_loop"
    VERSION = "2.0.6"
    DESCRIPTION = "Live-Update System"
    AUTHOR = "TwinCAT Team"
    DEPENDENCIES = ['plc_communication', 'card_renderer']
    
    def __init__(self):
        super().__init__()
        self.plc = None
        self.cards = None
        self.running = False
        self.update_thread = None
        self.update_interval = 1.0  # Sekunden
        self.visible_cards = set()
    
    def initialize(self, app_context: Any):
        """Initialisiert Update-Loop"""
        super().initialize(app_context)
        self.app = app_context
        
        # Hole Module
        self.plc = app_context.module_manager.get_module('plc_communication')
        self.cards = app_context.module_manager.get_module('card_renderer')
        
        print(f"  ⚡ {self.NAME} v{self.VERSION} initialisiert")
    
    def start(self, interval: float = 1.0):
        """Startet Update-Loop"""
        if self.running:
            return
        
        self.update_interval = interval
        self.running = True
        
        self.update_thread = threading.Thread(target=self._update_worker, daemon=True)
        self.update_thread.start()
        
        print(f"  ▶️ Update-Loop gestartet ({interval}s Intervall)")
    
    def stop(self):
        """Stoppt Update-Loop"""
        self.running = False
        if self.update_thread:
            self.update_thread.join(timeout=2.0)
        print("  ⏸️ Update-Loop gestoppt")
    
    def set_visible_cards(self, card_ids: Set[str]):
        """Setzt Liste sichtbarer Cards (für Smart-Update)"""
        self.visible_cards = card_ids
    
    def _update_worker(self):
        """Update-Worker Thread"""
        while self.running:
            try:
                self._update_all_cards()
            except Exception as e:
                print(f"  ⚠️ Update-Fehler: {e}")
            
            time.sleep(self.update_interval)
    
    def _update_all_cards(self):
        """Aktualisiert alle sichtbaren Cards"""
        if not self.plc or not self.cards:
            return
        
        all_cards = self.cards.get_all_cards()
        
        for card_id, card_widgets in all_cards.items():
            # Smart-Update: Nur sichtbare Cards
            if self.visible_cards and card_id not in self.visible_cards:
                continue
            
            self._update_single_card(card_id, card_widgets)
    
    def _update_single_card(self, card_id: str, card_widgets: Dict):
        """Aktualisiert einzelne Card"""
        if card_id not in self.cards.card_data:
            return
        
        card_data = self.cards.card_data[card_id]
        plugin_type = card_data.get('plugin_type', 'light')
        
        try:
            if plugin_type == 'light':
                self._update_light_card(card_widgets, card_data)
            elif plugin_type == 'temperature':
                self._update_temperature_card(card_widgets, card_data)
            elif plugin_type == 'gauge':
                self._update_gauge_card(card_widgets, card_data)
            elif plugin_type == 'weather':
                self._update_weather_card(card_widgets, card_data)
        except Exception as e:
            # Stille Fehler bei einzelnen Cards
            pass
    
    def _update_light_card(self, widgets: Dict, data: Dict):
        """Aktualisiert Light-Card"""
        # WICHTIG: Nutze INPUT für Status-Anzeige (echte Rückmeldung)!
        # OUTPUT ist nur zum Schreiben (Impuls)
        input_var = data.get('input')
        
        if not input_var:
            # Fallback: Wenn kein Input definiert, nutze Output
            input_var = data.get('output')
        
        if not input_var:
            return
        
        # Lese Wert vom PLC
        try:
            value = self.plc.read_by_name(input_var, pyads.PLCTYPE_BOOL)
        except:
            value = None
        
        if value is not None and self.cards and self.cards.gui:
            # Update GUI im Main-Thread (Thread-Safety!)
            def update_gui():
                if 'status_canvas' in widgets and 'status_circle' in widgets:
                    color = self.cards.gui.colors['success'] if value else '#cccccc'
                    try:
                        widgets['status_canvas'].itemconfig(
                            widgets['status_circle'],
                            fill=color
                        )
                    except:
                        pass
                
                if 'status_text' in widgets:
                    text = "EIN" if value else "AUS"
                    text_color = self.cards.gui.colors['success'] if value else self.cards.gui.colors['text_light']
                    try:
                        widgets['status_text'].config(text=text, fg=text_color)
                    except:
                        pass
                
                # Card-Border wie in v1.2
                if 'frame' in widgets:
                    try:
                        widgets['frame'].config(
                            borderwidth=2 if value else 1
                        )
                    except:
                        pass
            
            # Führe im Main-Thread aus
            try:
                self.cards.gui.root.after(0, update_gui)
            except:
                pass
    
    def _update_temperature_card(self, widgets: Dict, data: Dict):
        """Aktualisiert Temperature-Card"""
        variable = data.get('variable')
        if not variable:
            return
        
        # Lese Temperatur
        try:
            value = self.plc.read_by_name(variable, pyads.PLCTYPE_REAL)
        except:
            value = None
        
        if value is not None and 'temp_label' in widgets:
            # Einheit
            unit = data.get('unit', 'celsius')
            if unit == 'fahrenheit':
                value = value * 9/5 + 32
                symbol = "°F"
            else:
                symbol = "°C"
            
            # Farbe basierend auf Temperatur
            if value < 15:
                color = '#2196F3'
            elif value < 25:
                color = '#4CAF50'
            else:
                color = '#FF9800'
            
            def update_gui():
                try:
                    widgets['temp_label'].config(text=f"{value:.1f}{symbol}", fg=color)
                except:
                    pass
            
            try:
                self.cards.gui.root.after(0, update_gui)
            except:
                pass
    
    def _update_gauge_card(self, widgets: Dict, data: Dict):
        """Aktualisiert Gauge-Card"""
        variable = data.get('variable')
        if not variable:
            return
        
        # Bestimme Typ
        var_type = data.get('var_type', 'REAL')
        if var_type == 'REAL':
            plc_type = pyads.PLCTYPE_REAL
        elif var_type == 'INT':
            plc_type = pyads.PLCTYPE_INT
        else:
            plc_type = pyads.PLCTYPE_DINT
        
        # Lese Wert
        try:
            value = self.plc.read_by_name(variable, plc_type)
        except:
            value = None
        
        if value is not None:
            min_val = data.get('min_value', 0)
            max_val = data.get('max_value', 100)
            unit = data.get('unit', '')
            
            # Berechne Prozent
            if max_val > min_val:
                percent = ((value - min_val) / (max_val - min_val)) * 100
                percent = max(0, min(100, percent))
            else:
                percent = 0
            
            def update_gui():
                # Update Wert-Label
                if 'value_label' in widgets:
                    try:
                        widgets['value_label'].config(text=f"{value:.1f} {unit}")
                    except:
                        pass
                
                # Update Balken
                if 'bar_canvas' in widgets and 'bar' in widgets:
                    try:
                        bar_height = int(150 * (percent / 100))
                        widgets['bar_canvas'].coords(
                            widgets['bar'],
                            0, 150 - bar_height, 30, 150
                        )
                        
                        # Farbe basierend auf Prozent
                        if percent < 33:
                            color = '#4CAF50'
                        elif percent < 66:
                            color = '#FF9800'
                        else:
                            color = '#f44336'
                        
                        widgets['bar_canvas'].itemconfig(widgets['bar'], fill=color)
                    except:
                        pass
            
            try:
                self.cards.gui.root.after(0, update_gui)
            except:
                pass
    
    def _update_weather_card(self, widgets: Dict, data: Dict):
        """Aktualisiert Weather-Card"""
        # Temperatur
        temp_var = data.get('temp_var')
        if temp_var:
            temp = self.plc.read_by_name(temp_var, pyads.PLCTYPE_REAL)
            if temp is not None and 'temp_label' in widgets:
                try:
                    widgets['temp_label'].config(text=f"{temp:.1f}°C")
                except:
                    pass
        
        # Luftfeuchtigkeit
        humidity_var = data.get('humidity_var')
        if humidity_var:
            humidity = self.plc.read_by_name(humidity_var, pyads.PLCTYPE_REAL)
            if humidity is not None and 'humidity_label' in widgets:
                try:
                    widgets['humidity_label'].config(text=f"{humidity:.0f}%")
                except:
                    pass
        
        # Wind
        wind_var = data.get('wind_var')
        if wind_var:
            wind = self.plc.read_by_name(wind_var, pyads.PLCTYPE_REAL)
            if wind is not None and 'wind_label' in widgets:
                try:
                    widgets['wind_label'].config(text=f"{wind:.1f} km/h")
                except:
                    pass
    
    def shutdown(self):
        """Stoppt Update-Loop"""
        self.stop()


def register(module_manager):
    """Registriert Modul"""
    module_manager.register_module(
        UpdateLoop.NAME,
        UpdateLoop.VERSION,
        UpdateLoop.DESCRIPTION,
        UpdateLoop,
        author=UpdateLoop.AUTHOR,
        dependencies=UpdateLoop.DEPENDENCIES
    )
