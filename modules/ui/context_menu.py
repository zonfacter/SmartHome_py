"""
Context Menu Module
Version: 1.0.0
Rechtsklick-Menü für Cards (Quick Actions)
"""

from module_manager import BaseModule
from typing import Any, Callable, Dict
import tkinter as tk
from tkinter import messagebox
import random
import string


class ContextMenu(BaseModule):
    """
    Kontext-Menü (Rechtsklick)
    
    Funktionen:
    - Rechtsklick-Menü
    - Quick-Actions
    - Card-Aktionen
    """
    
    NAME = "context_menu"
    VERSION = "1.0.0"
    DESCRIPTION = "Rechtsklick-Menü für Cards"
    AUTHOR = "TwinCAT Team"
    DEPENDENCIES = ['gui_manager', 'card_renderer', 'config_manager']
    
    def __init__(self):
        super().__init__()
        self.gui = None
        self.cards = None
        self.config = None
    
    def initialize(self, app_context: Any):
        """Initialisiert Context Menu"""
        super().initialize(app_context)
        self.app = app_context
        
        # Hole Module
        self.gui = app_context.module_manager.get_module('gui_manager')
        self.cards = app_context.module_manager.get_module('card_renderer')
        self.config = app_context.module_manager.get_module('config_manager')
        
        print(f"  ⚡ {self.NAME} v{self.VERSION} initialisiert")
    
    def show_menu(self, event, card_id: str):
        """Zeigt Kontext-Menü"""
        menu = tk.Menu(self.gui.root, tearoff=0, font=('Segoe UI', 10))
        
        # ✏️ Bearbeiten
        menu.add_command(
            label="✏️  Bearbeiten",
            command=lambda: self.edit_card(card_id)
        )
        
        # 📋 Duplizieren
        menu.add_command(
            label="📋  Duplizieren",
            command=lambda: self.duplicate_card(card_id)
        )
        
        menu.add_separator()
        
        # 🔼 Verschieben
        floors_menu = tk.Menu(menu, tearoff=0)
        for floor in ['🏡 Erdgeschoss', '🔼 Obergeschoss', '⬆️ Dachboden']:
            floors_menu.add_command(
                label=floor,
                command=lambda f=floor: self.move_card(card_id, f)
            )
        menu.add_cascade(label="🔼  Verschieben nach...", menu=floors_menu)
        
        menu.add_separator()
        
        # 👁️ Ausblenden
        menu.add_command(
            label="👁️  Ausblenden",
            command=lambda: self.hide_card(card_id)
        )
        
        # 🗑️ Löschen
        menu.add_command(
            label="🗑️  Löschen",
            command=lambda: self.delete_card(card_id)
        )
        
        menu.add_separator()
        
        # ℹ️ Info
        menu.add_command(
            label="ℹ️  Info",
            command=lambda: self.show_info(card_id)
        )
        
        # Zeige Menü
        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()
    
    def edit_card(self, card_id: str):
        """Öffnet Card-Editor"""
        messagebox.showinfo("Bearbeiten", f"Editor für Card {card_id}\n(Kommt bald!)")
    
    def duplicate_card(self, card_id: str):
        """Dupliziert Card"""
        if not self.config:
            return
        
        # Hole Original-Daten
        custom_lights = self.config.get_custom_lights()
        if card_id not in custom_lights:
            messagebox.showwarning("Fehler", "Nur Custom Cards können dupliziert werden!")
            return
        
        # Kopiere Daten
        original = custom_lights[card_id].copy()
        
        # Neue ID
        new_id = f"Card_{''.join(random.choices(string.ascii_uppercase + string.digits, k=6))}"
        
        # Name anpassen
        original['name'] = f"{original.get('name', 'Card')} (Kopie)"
        
        # Speichere
        self.config.add_custom_light(new_id, original)
        
        messagebox.showinfo("Dupliziert", f"Card '{new_id}' wurde erstellt!")
        
        # Event triggern für Reload
        if self.gui:
            self.gui.trigger_event('cards_changed')
    
    def move_card(self, card_id: str, target_floor: str):
        """Verschiebt Card zu anderer Etage"""
        if not self.config:
            return
        
        custom_lights = self.config.get_custom_lights()
        
        if card_id in custom_lights:
            custom_lights[card_id]['floor'] = target_floor
            self.config.save_config()
            
            messagebox.showinfo("Verschoben", f"Card nach '{target_floor}' verschoben!")
            
            if self.gui:
                self.gui.trigger_event('cards_changed')
        else:
            messagebox.showinfo("Info", "Standard-Cards können nicht verschoben werden.")
    
    def hide_card(self, card_id: str):
        """Versteckt Card"""
        if self.cards:
            card_widget = self.cards.get_card(card_id)
            if card_widget and 'frame' in card_widget:
                card_widget['frame'].grid_remove()
                messagebox.showinfo("Ausgeblendet", "Card wurde ausgeblendet.\n\nNutze Reload um sie wieder anzuzeigen.")
    
    def delete_card(self, card_id: str):
        """Löscht Card"""
        if not self.config:
            return
        
        custom_lights = self.config.get_custom_lights()
        
        if card_id not in custom_lights:
            messagebox.showwarning("Fehler", "Standard-Cards können nicht gelöscht werden!")
            return
        
        card_name = custom_lights[card_id].get('name', card_id)
        
        if messagebox.askyesno("Löschen bestätigen",
            f"Card '{card_name}' wirklich löschen?\n\nDiese Aktion kann nicht rückgängig gemacht werden!"):
            
            self.config.delete_custom_light(card_id)
            
            messagebox.showinfo("Gelöscht", f"Card '{card_name}' wurde gelöscht!")
            
            if self.gui:
                self.gui.trigger_event('cards_changed')
    
    def show_info(self, card_id: str):
        """Zeigt Card-Informationen"""
        if not self.config:
            return
        
        custom_lights = self.config.get_custom_lights()
        card_data = custom_lights.get(card_id, {})
        
        info = f"ID: {card_id}\n"
        info += f"Name: {card_data.get('name', 'N/A')}\n"
        info += f"Typ: {card_data.get('plugin_type', 'light')}\n"
        info += f"Etage: {card_data.get('floor', 'N/A')}\n"
        
        if 'input' in card_data:
            info += f"Input: {card_data['input']}\n"
        if 'output' in card_data:
            info += f"Output: {card_data['output']}\n"
        if 'variable' in card_data:
            info += f"Variable: {card_data['variable']}\n"
        
        messagebox.showinfo(f"Card Info: {card_data.get('name', card_id)}", info)
    
    def bind_to_widget(self, widget: tk.Widget, card_id: str):
        """Bindet Rechtsklick an Widget"""
        widget.bind("<Button-3>", lambda e: self.show_menu(e, card_id))
    
    def shutdown(self):
        """Aufräumen"""
        pass


def register(module_manager):
    """Registriert Modul"""
    module_manager.register_module(
        ContextMenu.NAME,
        ContextMenu.VERSION,
        ContextMenu.DESCRIPTION,
        ContextMenu,
        author=ContextMenu.AUTHOR,
        dependencies=ContextMenu.DEPENDENCIES
    )
