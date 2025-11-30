"""
Card Renderer Module
Version: 2.0.0
Erstellt und verwaltet alle Card-Widgets mit Drag&Drop Integration

📁 SPEICHERORT: modules/ui/card_renderer.py

Features:
- Card-Erstellung mit Drag&Drop
- Plugin-System Integration
- Layout-Verwaltung
- Update-Loop Support
- Drag Handle Integration
"""

from module_manager import BaseModule
from typing import Dict, Any, Optional, List
import tkinter as tk
import random
import string


class CardRenderer(BaseModule):
    """
    Card-Renderer v2.0
    
    Features:
    - Card-Erstellung mit Drag&Drop
    - Plugin-System Integration
    - Layout-Verwaltung
    - Update-Loop Support
    - Drag Handle Integration
    """
    
    NAME = "card_renderer"
    VERSION = "2.0.0"
    DESCRIPTION = "Advanced Card-Rendering mit Drag&Drop"
    AUTHOR = "TwinCAT Team"
    DEPENDENCIES = ['gui_manager', 'drag_drop']
    
    def __init__(self):
        super().__init__()
        self.cards = {}  # card_id -> card_widget
        self.card_data = {}  # card_id -> data
        self.tab_frames = {}  # floor_name -> frame
        self.gui = None
        self.drag_drop = None  # Drag&Drop Modul
    
    def initialize(self, app_context: Any):
        """Initialisiert Card-Renderer"""
        super().initialize(app_context)
        self.app = app_context
        
        # Hole Module
        self.gui = app_context.module_manager.get_module('gui_manager')
        self.drag_drop = app_context.module_manager.get_module('drag_drop')
        
        print(f"  ⚡ {self.NAME} v{self.VERSION} initialisiert")
    
    def create_card(self, parent: tk.Widget, card_id: str, 
                   card_data: Dict) -> tk.Frame:
        """
        Erstellt Card-Widget via Plugin-System
        
        Args:
            parent: Parent-Widget
            card_id: Eindeutige ID
            card_data: Card-Konfiguration
        
        Returns:
            Card-Frame
        """
        # Hole Plugin-Type
        plugin_type = card_data.get('plugin_type', 'light')
        
        # Hole Plugin-Modul
        plugin = self.app.module_manager.get_module(plugin_type)
        
        if plugin and hasattr(plugin, 'create_card'):
            # Nutze Plugin zur Card-Erstellung!
            widgets = plugin.create_card(
                parent, 
                card_id, 
                card_data, 
                self.gui.colors
            )
            
            # Speichere Card-Referenzen
            if widgets and isinstance(widgets, dict):
                self.cards[card_id] = widgets
                self.card_data[card_id] = card_data
                
                # Bind Drag & Drop
                if self.drag_drop and 'frame' in widgets:
                    # Finde Drag-Handle im Widget-Dict
                    drag_handle = widgets.get('drag_handle') or widgets.get('frame')
                    if drag_handle:
                        self.drag_drop.bind_to_widget(drag_handle, card_id)
                
                return widgets.get('frame')
        
        # Fallback: Generische Card (falls Plugin fehlt)
        print(f"  ⚠️  Plugin '{plugin_type}' nicht gefunden, nutze generische Card")
        return self._create_generic_card(parent, card_id, card_data)
    
    def _create_generic_card(self, parent: tk.Widget, card_id: str,
                            card_data: Dict) -> tk.Frame:
        """Erstellt generische Card (Fallback)"""
        # Card Frame
        card = self.gui.create_frame(
            parent,
            bg=self.gui.colors['card_bg'],
            relief=tk.RAISED,
            borderwidth=1,
            cursor='hand2'
        )
        
        # Content Frame
        content = self.gui.create_frame(card, relief=tk.FLAT)
        content.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Drag Handle
        drag_handle = self.gui.create_frame(content, relief=tk.FLAT, cursor='fleur')
        drag_handle.pack(fill=tk.X, pady=(0, 10))
        
        drag_label = tk.Label(
            drag_handle,
            text="⋮⋮⋮",
            font=('Segoe UI', 8),
            bg=self.gui.colors['card_bg'],
            fg=self.gui.colors['text_light'],
            cursor='fleur'
        )
        drag_label.pack()
        
        # Header
        header = self.gui.create_frame(content, relief=tk.FLAT)
        header.pack(fill=tk.X)
        
        # Icon
        icon = tk.Label(
            header,
            text=card_data.get('icon', '💡'),
            font=('Segoe UI', 32),
            bg=self.gui.colors['card_bg']
        )
        icon.pack(side=tk.LEFT)
        
        # Name
        name = tk.Label(
            header,
            text=card_data.get('name', 'Card'),
            font=('Segoe UI', 14, 'bold'),
            bg=self.gui.colors['card_bg'],
            fg=self.gui.colors['text_dark'],
            wraplength=200
        )
        name.pack(side=tk.LEFT, padx=15)
        
        # Status Indicator
        status_frame = self.gui.create_frame(content, relief=tk.FLAT)
        status_frame.pack(pady=20)
        
        status_canvas = tk.Canvas(
            status_frame,
            width=100,
            height=100,
            bg=self.gui.colors['card_bg'],
            highlightthickness=0
        )
        status_canvas.pack()
        
        # Zeichne Kreis
        circle = status_canvas.create_oval(15, 15, 85, 85, fill='gray', outline='')
        
        # Status Text
        status_text = tk.Label(
            content,
            text="•••",
            font=('Segoe UI', 12, 'bold'),
            bg=self.gui.colors['card_bg'],
            fg=self.gui.colors['text_light']
        )
        status_text.pack()
        
        # Action Button
        action_btn = self.gui.create_button(
            content,
            text="Toggle",
            command=lambda: self.on_card_action(card_id),
            style='primary'
        )
        action_btn.config(font=('Segoe UI', 13, 'bold'), padx=30, pady=12)
        action_btn.pack(pady=15, fill=tk.X)
        
        # Speichere Card-Referenzen
        self.cards[card_id] = {
            'frame': card,
            'status_canvas': status_canvas,
            'status_circle': circle,
            'status_text': status_text,
            'button': action_btn,
            'drag_handle': drag_handle
        }
        
        self.card_data[card_id] = card_data
        
        # Bind Drag & Drop
        if self.drag_drop:
            self.drag_drop.bind_to_widget(drag_handle, card_id)
            self.drag_drop.bind_to_widget(drag_label, card_id)
        
        return card
    
    def on_card_action(self, card_id: str):
        """Card-Aktion ausführen"""
        print(f"Card Action: {card_id}")
        
        # Event triggern für Haupt-App
        if self.gui:
            self.gui.trigger_event('card_action', card_id, self.card_data.get(card_id))
    
    def update_card_status(self, card_id: str, value: Any):
        """Aktualisiert Card-Status"""
        if card_id not in self.cards:
            return
        
        card_widgets = self.cards[card_id]
        
        # Update Kreis-Farbe
        color = self.gui.colors['success'] if value else 'gray'
        card_widgets['status_canvas'].itemconfig(
            card_widgets['status_circle'],
            fill=color
        )
        
        # Update Text
        text = "EIN" if value else "AUS"
        card_widgets['status_text'].config(text=text)
    
    def delete_card(self, card_id: str) -> bool:
        """Löscht Card"""
        if card_id in self.cards:
            self.cards[card_id]['frame'].destroy()
            del self.cards[card_id]
            del self.card_data[card_id]
            return True
        return False
    
    def get_card(self, card_id: str) -> Optional[Dict]:
        """Holt Card-Widget"""
        return self.cards.get(card_id)
    
    def get_all_cards(self) -> Dict:
        """Gibt alle Cards zurück"""
        return self.cards
    
    def generate_card_id(self) -> str:
        """Generiert eindeutige Card-ID"""
        return f"Card_{''.join(random.choices(string.ascii_uppercase + string.digits, k=6))}"
    
    def create_floor_tab(self, notebook: tk.Widget, floor_name: str, 
                        icon: str = "") -> tk.Frame:
        """Erstellt Etagen-Tab"""
        # Tab Frame
        tab_frame = self.gui.create_frame(notebook, bg=self.gui.colors['bg'])
        
        # Container für Cards
        container = self.gui.create_frame(tab_frame, bg=self.gui.colors['bg'], relief=tk.FLAT)
        container.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Speichere
        self.tab_frames[floor_name] = container
        
        return tab_frame
    
    def get_tab_frame(self, floor_name: str) -> Optional[tk.Frame]:
        """Holt Tab-Frame"""
        return self.tab_frames.get(floor_name)
    
    def update_grid_layout(self, floor_name: str, cols: int = 3):
        """Aktualisiert Grid-Layout"""
        if floor_name not in self.tab_frames:
            return
        
        container = self.tab_frames[floor_name]
        
        # Finde alle Cards für diese Etage
        cards_in_floor = [
            (cid, widgets) for cid, widgets in self.cards.items()
            if self.card_data.get(cid, {}).get('floor') == floor_name
        ]
        
        # Layout im Grid
        for idx, (card_id, widgets) in enumerate(cards_in_floor):
            row = idx // cols
            col = idx % cols
            
            widgets['frame'].grid(row=row, column=col, padx=10, pady=10, sticky='nsew')
        
        # Grid Weights
        for i in range(cols):
            container.grid_columnconfigure(i, weight=1, minsize=350)
    
    def shutdown(self):
        """Aufräumen"""
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
