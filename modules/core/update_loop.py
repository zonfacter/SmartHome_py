"""
Update Loop Module v2.1.0
Plugin-basiertes Update-System

📁 SPEICHERORT: modules/core/update_loop.py

🆕 v2.1.0:
- Generisches Plugin-Update (statt hardcoded)
- Ruft plugin.update_card() auf
- Plugins managen ihre eigenen Updates
- Keine hardcoded Plugin-Logik mehr!

Features:
- Live-Updates von PLC über Plugins
- Thread-Safe GUI-Updates
- Smart-Update (nur sichtbare Cards)
- Fehler-Handling & Auto-Reconnect
- Konfigurierbare Intervalle
"""

from module_manager import BaseModule
from typing import Any, Dict, Set
import threading
import time


class UpdateLoop(BaseModule):
    """
    Update-Loop v2.1.0
    
    ⭐ NEU: Generisches Plugin-Update-System!
    - Keine hardcoded Plugin-Logik
    - Jedes Plugin managed seine eigenen Updates
    - Sauber & erweiterbar
    
    Features:
    - Live-Updates über plugin.update_card()
    - Smart-Update (nur sichtbare Cards)
    - Fehler-Handling & Auto-Reconnect
    - Konfigurierbare Intervalle
    """
    
    NAME = "update_loop"
    VERSION = "2.1.0"
    DESCRIPTION = "Plugin-basiertes Update-System"
    AUTHOR = "TwinCAT Team"
    DEPENDENCIES = ['plc_communication', 'card_renderer']
    
    def __init__(self):
        super().__init__()
        self.plc = None
        self.cards = None
        self.app = None
        self.running = False
        self.update_thread = None
        self.update_interval = 1.0  # Sekunden
        self.visible_cards = set()  # Für Smart-Update (zukünftig)
        
        # Statistik
        self.update_count = 0
        self.error_count = 0
    
    def initialize(self, app_context: Any):
        """Initialisiert Update-Loop"""
        super().initialize(app_context)
        self.app = app_context
        
        # Hole Module
        self.plc = app_context.module_manager.get_module('plc_communication')
        self.cards = app_context.module_manager.get_module('card_renderer')
        
        print(f"  ⚡ {self.NAME} v{self.VERSION} initialisiert")
    
    def start(self, interval: float = 1.0):
        """
        Startet Update-Loop
        
        Args:
            interval: Update-Intervall in Sekunden (default: 1.0)
        """
        if self.running:
            print("  ⚠️  Update-Loop läuft bereits!")
            return
        
        self.update_interval = interval
        self.running = True
        
        # Starte Worker-Thread
        self.update_thread = threading.Thread(target=self._update_worker, daemon=True)
        self.update_thread.start()
        
        print(f"  ▶️ Update-Loop gestartet ({interval}s Intervall)")
    
    def stop(self):
        """Stoppt Update-Loop"""
        if not self.running:
            return
        
        self.running = False
        
        if self.update_thread:
            self.update_thread.join(timeout=2.0)
        
        print(f"  ⏸️ Update-Loop gestoppt")
        print(f"     📊 Updates: {self.update_count}, Fehler: {self.error_count}")
    
    def set_visible_cards(self, card_ids: Set[str]):
        """
        Setzt Liste sichtbarer Cards (für Smart-Update)
        
        Args:
            card_ids: Set von Card-IDs die aktuell sichtbar sind
        """
        self.visible_cards = card_ids
    
    def _update_worker(self):
        """
        Update-Worker Thread
        
        Läuft in separatem Thread und ruft zyklisch Updates auf
        """
        print(f"  🔄 Update-Worker gestartet")
        
        while self.running:
            try:
                # ⭐ Haupt-Update
                self._update_all_cards()
                self.update_count += 1
                
            except Exception as e:
                self.error_count += 1
                print(f"  ⚠️  Update-Fehler: {e}")
                # Keine Details im normalen Betrieb (zu viel Spam)
            
            # Warte bis nächster Zyklus
            time.sleep(self.update_interval)
        
        print(f"  🛑 Update-Worker beendet")
    
    def _update_all_cards(self):
        """
        Aktualisiert alle Cards über ihre Plugins
        
        ⭐ v2.1.0: Generisch! Keine hardcoded Plugin-Logik!
        """
        if not self.cards:
            return
        
        # Hole alle Cards vom Renderer
        try:
            all_cards = self.cards.get_all_cards()
        except Exception as e:
            # Card-Renderer noch nicht bereit
            return
        
        # Update jede Card
        for card_id, widgets in all_cards.items():
            # Smart-Update: Nur sichtbare Cards aktualisieren (Performance-Optimierung)
            if self.visible_cards and card_id not in self.visible_cards:
                continue

            # Update diese Card
            self._update_single_card(card_id, widgets)
    
    def _update_single_card(self, card_id: str, widgets: Dict):
        """
        Aktualisiert einzelne Card über ihr Plugin
        
        ⭐ v2.1.0: Ruft plugin.update_card() auf!
        
        Args:
            card_id: Card-ID
            widgets: Widget-Dict vom Renderer
        """
        # Hole Card-Daten
        card_data = widgets.get('data', {})
        if not card_data:
            return
        
        # Hole Plugin-Typ
        plugin_type = card_data.get('plugin_type')
        if not plugin_type:
            return
        
        # Hole Plugin vom Manager
        plugin = self.app.module_manager.get_module(plugin_type)
        if not plugin:
            return
        
        # ⭐ Hat Plugin update_card() Methode?
        if not hasattr(plugin, 'update_card'):
            # Plugin unterstützt keine Updates (ist OK)
            return
        
        # ⭐ Rufe Plugin-Update auf!
        try:
            plugin.update_card(card_id, card_data)
        except Exception as e:
            # Stille Fehler bei einzelnen Cards
            # (Card könnte gelöscht/versteckt sein, etc.)
            pass
    
    def shutdown(self):
        """Cleanup beim Beenden"""
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
