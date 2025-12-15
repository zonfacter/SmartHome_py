"""
Card Renderer v3.1.0
Advanced Card-Rendering mit Tab-ID Support

🆕 v3.1.0: 
- Nutzt tab_id statt floor
- Grid-Layout mit tab_id
"""

from module_manager import BaseModule
from typing import Any, Dict, Optional
import tkinter as tk
from tkinter import ttk


class CardRenderer(BaseModule):
    """
    Card Renderer v3.1.0
    
    ⭐ v3.1.0: Tab-ID basiert!
    - tab_frames[tab_id] statt tab_frames[floor_name]
    - Grid-Layout mit tab_id
    """
    
    NAME = "card_renderer"
    VERSION = "3.1.0"
    DESCRIPTION = "Tab-ID basiertes Card-Rendering"
    AUTHOR = "TwinCAT Team"
    DEPENDENCIES = ['gui_manager']
    
    def __init__(self):
        super().__init__()
        self.gui = None
        self.tab_frames = {}  # tab_id -> frame (v3.1.0: IDs statt Namen!)
        self.cards = {}  # card_id -> widget_dict
        self.card_data = {}  # card_id -> card_data
    
    def initialize(self, app_context: Any):
        """Initialisiert Card-Renderer"""
        super().initialize(app_context)
        self.app = app_context
        
        # Hole GUI-Manager
        self.gui = app_context.module_manager.get_module('gui_manager')
        
        print(f"  ⚡ {self.NAME} v{self.VERSION} initialisiert")
    
    def get_tab_frame(self, tab_id: str) -> Optional[tk.Frame]:
        """
        Holt Tab-Frame per ID (v3.1.0)
        
        Args:
            tab_id: Tab-ID (z.B. 'TabID_a1b2c3')
        
        Returns:
            Frame oder None
        """
        return self.tab_frames.get(tab_id)
    
    def create_card(self, parent: tk.Widget, card_id: str, card_data: dict) -> Optional[tk.Frame]:
        """
        Erstellt Card
        
        Args:
            parent: Parent Widget (Tab-Frame)
            card_id: Eindeutige Card-ID
            card_data: Card-Daten inkl. tab_id
        
        Returns:
            Card-Frame
        """
        # ⭐ WICHTIG: Card-ID in Daten speichern für Plugin-Updates!
        card_data['_card_id'] = card_id
        
        # Speichere Card-Daten
        self.card_data[card_id] = card_data
        
        # Hole Plugin
        plugin_type = card_data.get('plugin_type', 'light')
        plugin = self.app.module_manager.get_module(plugin_type)
        
        if not plugin:
            print(f"  ⚠️  Plugin '{plugin_type}' nicht gefunden für Card {card_id}")
            return None
        
        # Erstelle Frame
        card_frame = tk.Frame(parent, bg=self.gui.colors['card_bg'],
                             relief=tk.RAISED, borderwidth=2)
        
        # Plugin erstellt Inhalt
        if hasattr(plugin, 'create_card_content'):
            plugin.create_card_content(card_frame, card_data)
        
        # Speichere Widget
        self.cards[card_id] = {
            'frame': card_frame,
            'data': card_data
        }
        
        return card_frame
    
    def update_grid_layout(self, tab_id: str, cols: int = 3):
        """
        Aktualisiert Grid-Layout für Tab (⭐ v3.1.0: Mit tab_id!)
        
        Args:
            tab_id: Tab-ID (z.B. 'TabID_a1b2c3')
            cols: Anzahl Spalten
        """
        if tab_id not in self.tab_frames:
            print(f"  ⚠️  update_grid_layout: Tab-ID {tab_id} nicht gefunden!")
            print(f"      Verfügbare IDs: {list(self.tab_frames.keys())}")
            return
        
        container = self.tab_frames[tab_id]
        
        # ⭐ v3.1.0: Finde alle Cards für diese Tab-ID
        cards_in_tab = [
            (cid, widgets) for cid, widgets in self.cards.items()
            if self.card_data.get(cid, {}).get('tab_id') == tab_id
        ]
        
        print(f"    📦 Layout {len(cards_in_tab)} Cards in Tab {tab_id}")
        
        # Layout im Grid
        for idx, (card_id, widgets) in enumerate(cards_in_tab):
            row = idx // cols
            col = idx % cols
            
            frame = widgets['frame']
            frame.grid(row=row, column=col, padx=10, pady=10, sticky='nsew')
            print(f"      ✓ Card {card_id} → Grid[{row},{col}]")
        
        # Grid Weights
        for i in range(cols):
            container.grid_columnconfigure(i, weight=1, minsize=350)
    
    def remove_card(self, card_id: str):
        """Entfernt Card"""
        if card_id in self.cards:
            widgets = self.cards[card_id]
            widgets['frame'].destroy()
            del self.cards[card_id]
            del self.card_data[card_id]
    
    def get_all_cards(self) -> Dict:
        """
        Gibt alle Cards zurück (für Update-Loop)
        
        Returns:
            Dict mit {card_id: widgets}
        """
        return self.cards
    
    def shutdown(self):
        """Cleanup"""
        pass


def register(module_manager):
    """Registriert Modul"""
    module_manager.register_module(
        CardRenderer.NAME,
        CardRenderer.VERSION,
        CardRenderer.DESCRIPTION,
        CardRenderer,
        author=CardRenderer.AUTHOR,
        dependencies=CardRenderer.DEPENDENCIES
    )
