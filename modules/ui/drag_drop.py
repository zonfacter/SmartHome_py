"""
Drag & Drop Module
Version: 2.0.5
Advanced Drag & Drop mit Grid-Snapping und Multi-Select

📁 SPEICHERORT: modules/ui/drag_drop.py

Features:
- Smooth Card-Bewegung
- Grid-Snapping (10px Raster, konfigurierbar)
- Visuelles Feedback
- Position-Swap
- Multi-Card Select (Ctrl+Click)
- Layout-Speicherung
- FIXED: Korrekter Offset beim Drag
"""

from module_manager import BaseModule
from typing import Any, Dict, Optional, Set
import tkinter as tk


class DragDrop(BaseModule):
    """
    Drag & Drop System v2.0
    
    Features:
    - Smooth Card-Bewegung
    - Grid-Snapping (10px Raster)
    - Visuelles Feedback
    - Position-Swap
    - Multi-Card Select (Bonus)
    - Layout-Speicherung
    """
    
    NAME = "drag_drop"
    VERSION = "2.0.5"
    DESCRIPTION = "Advanced Drag & Drop mit Grid-Snapping"
    AUTHOR = "TwinCAT Team"
    DEPENDENCIES = ['gui_manager', 'card_renderer', 'config_manager']
    
    def __init__(self):
        super().__init__()
        self.drag_data = {}
        self.gui = None
        self.cards = None
        self.config = None
        self.grid_size = 10  # Grid-Snapping Größe
        self.selected_cards: Set[str] = set()  # Multi-Select
    
    def initialize(self, app_context: Any):
        """Initialisiert Drag & Drop"""
        super().initialize(app_context)
        self.app = app_context
        
        # Hole Module
        self.gui = app_context.module_manager.get_module('gui_manager')
        self.cards = app_context.module_manager.get_module('card_renderer')
        self.config = app_context.module_manager.get_module('config_manager')
        
        print(f"  ⚡ {self.NAME} v{self.VERSION} initialisiert")
    
    def start_drag(self, event, card_id: str):
        """Startet Drag-Operation"""
        widget = event.widget
        
        # Finde Card-Widget
        while widget and not isinstance(widget, tk.Frame):
            widget = widget.master
        
        if not widget:
            return
        
        # Hole Card-Frame für korrekte Position
        card_frame = None
        if self.cards:
            card_widget = self.cards.get_card(card_id)
            if card_widget and 'frame' in card_widget:
                card_frame = card_widget['frame']
        
        # Nutze Card-Frame falls verfügbar, sonst widget
        position_widget = card_frame if card_frame else widget
        
        # Speichere Drag-Daten
        self.drag_data = {
            'item': card_id,
            'widget': widget,
            'start_x': event.x_root,
            'start_y': event.y_root,
            'orig_x': position_widget.winfo_x(),
            'orig_y': position_widget.winfo_y()
        }
        
        # Visuelles Feedback
        if card_frame:
            card_frame.config(relief=tk.GROOVE, borderwidth=3)
    
    def on_drag(self, event, card_id: str):
        """Während des Drags"""
        if not self.drag_data or self.drag_data.get('item') != card_id:
            return
        
        # Berechne Bewegung
        delta_x = event.x_root - self.drag_data['start_x']
        delta_y = event.y_root - self.drag_data['start_y']
        
        # Grid-Snapping
        if self.grid_size > 0:
            delta_x = round(delta_x / self.grid_size) * self.grid_size
            delta_y = round(delta_y / self.grid_size) * self.grid_size
        
        if self.cards:
            card_widget = self.cards.get_card(card_id)
            if card_widget and 'frame' in card_widget:
                card_frame = card_widget['frame']
                
                # Temporär aus Grid nehmen
                if 'grid_info' not in self.drag_data:
                    self.drag_data['grid_info'] = card_frame.grid_info()
                    card_frame.grid_forget()
                
                # Bewege smooth mit Snapping
                new_x = self.drag_data['orig_x'] + delta_x
                new_y = self.drag_data['orig_y'] + delta_y
                
                card_frame.place(x=new_x, y=new_y)
                
                # Finde Ziel-Card
                self._find_drop_target(card_id, event.x_root, event.y_root)
    
    def _find_drop_target(self, dragged_id: str, mouse_x: int, mouse_y: int):
        """Findet Drop-Ziel"""
        if not self.cards:
            return
        
        all_cards = self.cards.get_all_cards()
        min_distance = float('inf')
        target_card = None
        
        for cid, widget_dict in all_cards.items():
            if cid == dragged_id:
                continue
            
            if 'frame' not in widget_dict:
                continue
            
            frame = widget_dict['frame']
            
            # Berechne Distanz
            try:
                cx = frame.winfo_rootx() + frame.winfo_width() / 2
                cy = frame.winfo_rooty() + frame.winfo_height() / 2
                distance = ((mouse_x - cx)**2 + (mouse_y - cy)**2)**0.5
                
                if distance < min_distance:
                    min_distance = distance
                    target_card = cid
            except:
                pass
        
        # Markiere Ziel
        if hasattr(self, '_last_target') and self._last_target:
            last_widget = all_cards.get(self._last_target, {}).get('frame')
            if last_widget:
                last_widget.config(borderwidth=1, relief=tk.RAISED)
        
        if target_card:
            target_widget = all_cards.get(target_card, {}).get('frame')
            if target_widget:
                target_widget.config(borderwidth=3, relief=tk.SUNKEN)
                self._last_target = target_card
                self.drag_data['target'] = target_card
    
    def stop_drag(self, event, card_id: str):
        """Beendet Drag-Operation"""
        if not self.drag_data:
            return
        
        if self.cards:
            card_widget = self.cards.get_card(card_id)
            if card_widget and 'frame' in card_widget:
                card_frame = card_widget['frame']
                
                # Entferne place
                card_frame.place_forget()
                
                # Hole Ziel
                target = self.drag_data.get('target')
                
                if target and target in self.cards.get_all_cards():
                    # Tausche Positionen
                    self._swap_positions(card_id, target)
                else:
                    # Zurück zur Original-Position
                    grid_info = self.drag_data.get('grid_info', {})
                    if grid_info:
                        card_frame.grid(**grid_info)
                
                # Reset visuelles Feedback
                card_frame.config(relief=tk.RAISED, borderwidth=1)
        
        # Cleanup Ziel-Markierung
        if hasattr(self, '_last_target') and self._last_target:
            all_cards = self.cards.get_all_cards()
            last_widget = all_cards.get(self._last_target, {}).get('frame')
            if last_widget:
                last_widget.config(borderwidth=1, relief=tk.RAISED)
            delattr(self, '_last_target')
        
        # Speichere Layout
        self._save_layout()
        
        # Cleanup
        self.drag_data.clear()
    
    def _swap_positions(self, source_id: str, target_id: str):
        """Tauscht zwei Cards"""
        if not self.cards:
            return
        
        all_cards = self.cards.get_all_cards()
        
        source_widget = all_cards.get(source_id, {}).get('frame')
        target_widget = all_cards.get(target_id, {}).get('frame')
        
        if not source_widget or not target_widget:
            return
        
        # Hole Grid-Infos
        source_grid = self.drag_data.get('grid_info', {})
        target_grid = target_widget.grid_info()
        
        # Tausche
        source_widget.grid(
            row=target_grid.get('row', 0),
            column=target_grid.get('column', 0),
            padx=target_grid.get('padx', 10),
            pady=target_grid.get('pady', 10),
            sticky=target_grid.get('sticky', 'nsew')
        )
        
        target_widget.grid(
            row=source_grid.get('row', 0),
            column=source_grid.get('column', 0),
            padx=source_grid.get('padx', 10),
            pady=source_grid.get('pady', 10),
            sticky=source_grid.get('sticky', 'nsew')
        )
    
    def _save_layout(self):
        """Speichert Layout"""
        if not self.cards or not self.config:
            return
        
        layout = {}
        all_cards = self.cards.get_all_cards()
        
        for card_id, widget_dict in all_cards.items():
            if 'frame' not in widget_dict:
                continue
            
            frame = widget_dict['frame']
            grid_info = frame.grid_info()
            
            layout[card_id] = {
                'row': grid_info.get('row', 0),
                'column': grid_info.get('column', 0)
            }
        
        # Speichere über Config-Manager
        self.config.save_layout(layout)
    
    def bind_to_widget(self, widget: tk.Widget, card_id: str):
        """Bindet Drag & Drop an Widget"""
        widget.bind("<Button-1>", lambda e: self.start_drag(e, card_id))
        widget.bind("<B1-Motion>", lambda e: self.on_drag(e, card_id))
        widget.bind("<ButtonRelease-1>", lambda e: self.stop_drag(e, card_id))
        
        # Multi-Select mit Ctrl+Click
        widget.bind("<Control-Button-1>", lambda e: self.toggle_selection(card_id))
    
    def toggle_selection(self, card_id: str):
        """Toggle Card-Auswahl (Multi-Select)"""
        if not self.cards:
            return
        
        card_widget = self.cards.get_card(card_id)
        if not card_widget or 'frame' not in card_widget:
            return
        
        frame = card_widget['frame']
        
        if card_id in self.selected_cards:
            # Deselect
            self.selected_cards.remove(card_id)
            frame.config(relief=tk.RAISED, borderwidth=1)
        else:
            # Select
            self.selected_cards.add(card_id)
            frame.config(relief=tk.SUNKEN, borderwidth=2,
                        highlightthickness=2, highlightbackground=self.gui.colors['primary'])
    
    def clear_selection(self):
        """Löscht alle Selektionen"""
        if not self.cards:
            return
        
        for card_id in list(self.selected_cards):
            card_widget = self.cards.get_card(card_id)
            if card_widget and 'frame' in card_widget:
                card_widget['frame'].config(relief=tk.RAISED, borderwidth=1,
                                           highlightthickness=0)
        
        self.selected_cards.clear()
    
    def set_grid_size(self, size: int):
        """Setzt Grid-Snapping Größe (0 = aus)"""
        self.grid_size = max(0, size)
        print(f"  📐 Grid-Snapping: {self.grid_size}px")
    
    def get_selected_cards(self) -> Set[str]:
        """Gibt ausgewählte Cards zurück"""
        return self.selected_cards.copy()
    
    def shutdown(self):
        """Aufräumen"""
        pass


def register(module_manager):
    """Registriert Modul"""
    module_manager.register_module(
        DragDrop.NAME,
        DragDrop.VERSION,
        DragDrop.DESCRIPTION,
        DragDrop,
        author=DragDrop.AUTHOR,
        dependencies=DragDrop.DEPENDENCIES
    )
