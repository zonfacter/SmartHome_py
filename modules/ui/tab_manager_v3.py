"""
Tab Manager v3.0.0
ID-basierte Tab-Verwaltung mit Sortierung

🔄 BREAKING CHANGE:
- Tabs haben jetzt IDs statt Namen als Identifier
- Tab-Positionen sind sortierbar
- Migration von alten floor-Namen zu IDs

📁 SPEICHERORT: modules/ui/tab_manager.py
"""

from module_manager import BaseModule
from typing import Any, Dict, List, Optional, Callable
import tkinter as tk
from tkinter import messagebox, simpledialog
import uuid
import time
import json


class TabManager(BaseModule):
    """
    Tab Manager v3.0
    
    ⭐ NEU in v3.0:
    - ID-basierte Tabs (TabID_XXXXXX)
    - Tab-Sortierung/Reihenfolge
    - Migration alter Configs
    - Drag & Drop Ready
    """
    
    NAME = "tab_manager"
    VERSION = "3.0.0"
    DESCRIPTION = "ID-basierte Tab-Verwaltung"
    AUTHOR = "TwinCAT Team"
    DEPENDENCIES = ['gui_manager', 'config_manager']
    
    def __init__(self):
        super().__init__()
        self.gui = None
        self.config = None
        self.tabs: Dict[str, dict] = {}  # tab_id -> tab_data
        self.tab_widgets: Dict[str, tk.Widget] = {}  # tab_id -> frame
        self.notebook = None
        
        # System-Tabs (werden automatisch erstellt)
        self.system_tabs = [
            {
                'name': 'Erdgeschoss',
                'icon': '🏡',
                'order': 0
            },
            {
                'name': 'Obergeschoss', 
                'icon': '🏠',
                'order': 1
            },
            {
                'name': 'Dachboden',
                'icon': '🏚️',
                'order': 2
            }
        ]
    
    def initialize(self, app_context: Any):
        """Initialisiert Tab-Manager"""
        super().initialize(app_context)
        self.app = app_context
        
        # Hole Module
        self.gui = app_context.module_manager.get_module('gui_manager')
        self.config = app_context.module_manager.get_module('config_manager')
        
        # Lade Tabs aus Config
        self._load_tabs()
        
        print(f"  ⚡ {self.NAME} v{self.VERSION} initialisiert")
        print(f"     📑 {len(self.tabs)} Tabs geladen")
    
    def generate_tab_id(self) -> str:
        """
        Generiert eindeutige Tab-ID
        
        Format: TabID_XXXXXX (6 Zeichen hex)
        
        Returns:
            Eindeutige Tab-ID
        """
        # UUID4 → hex → erste 6 Zeichen
        unique_id = uuid.uuid4().hex[:6]
        tab_id = f"TabID_{unique_id}"
        
        # Prüfe ob schon existiert (extrem unwahrscheinlich)
        while tab_id in self.tabs:
            unique_id = uuid.uuid4().hex[:6]
            tab_id = f"TabID_{unique_id}"
        
        return tab_id
    
    def _load_tabs(self):
        """Lädt Tabs aus Config"""
        if not self.config:
            return
        
        config_data = self.config.config
        
        # Prüfe ob Tabs existieren
        if 'tabs' not in config_data or not config_data['tabs']:
            print("  📑 Erstelle Standard-Tabs...")
            self._create_default_tabs()
            self._save_tabs()
        else:
            # Lade existierende Tabs
            self.tabs = config_data['tabs']
            print(f"  ✓ {len(self.tabs)} Tabs aus Config geladen")
            
            # Migriere alte Configs (falls nötig)
            self._migrate_old_configs()
    
    def _create_default_tabs(self):
        """Erstellt Standard System-Tabs"""
        for tab_def in self.system_tabs:
            tab_id = self.generate_tab_id()
            self.tabs[tab_id] = {
                'id': tab_id,
                'name': tab_def['name'],
                'icon': tab_def['icon'],
                'order': tab_def['order'],
                'is_system': True,
                'created_at': time.strftime('%Y-%m-%d %H:%M:%S')
            }
            print(f"     ✓ System-Tab erstellt: {tab_def['icon']} {tab_def['name']} (ID: {tab_id})")
    
    def _migrate_old_configs(self):
        """
        Migriert alte floor-basierte Cards zu Tab-IDs
        
        Alte Config:
          card['floor'] = 'Erdgeschoss'
        
        Neue Config:
          card['tab_id'] = 'TabID_a1b2c3'
        """
        if not self.config:
            return
        
        # Baue Mapping: Name → Tab-ID
        name_to_id = {}
        for tab_id, tab_data in self.tabs.items():
            name = tab_data['name']
            icon = tab_data.get('icon', '')
            
            # Verschiedene Varianten
            name_to_id[name] = tab_id
            name_to_id[f"{icon} {name}"] = tab_id
            # Alte Emoji-Varianten
            if name == 'Obergeschoss':
                name_to_id['🔼 Obergeschoss'] = tab_id
                name_to_id['⬆️ Obergeschoss'] = tab_id
        
        # Migriere Cards
        custom_lights = self.config.get_custom_lights()
        migrated_count = 0
        
        for card_id, card_data in custom_lights.items():
            # Hat Card schon tab_id?
            if 'tab_id' in card_data:
                continue
            
            # Hat Card alten 'floor' Eintrag?
            if 'floor' in card_data:
                old_floor = card_data['floor']
                
                # Finde passende Tab-ID
                if old_floor in name_to_id:
                    card_data['tab_id'] = name_to_id[old_floor]
                    migrated_count += 1
                else:
                    # Fallback: Erste Tab-ID
                    first_tab_id = list(self.tabs.keys())[0]
                    card_data['tab_id'] = first_tab_id
                    migrated_count += 1
                    print(f"  ⚠️  Card '{card_data.get('name')}': Floor '{old_floor}' nicht gefunden, nutze Default-Tab")
        
        if migrated_count > 0:
            print(f"  🔄 Migration: {migrated_count} Cards von floor → tab_id konvertiert")
            self.config.save_config()
    
    def _save_tabs(self):
        """Speichert Tabs in Config"""
        if not self.config:
            return
        
        config_data = self.config.config
        config_data['tabs'] = self.tabs
        self.config.save_config()
    
    def add_tab(self, name: str, icon: str = "📄", 
                create_content_callback: Callable = None,
                skip_save: bool = False) -> str:
        """
        Fügt neuen Tab hinzu
        
        Args:
            name: Tab-Name
            icon: Emoji-Icon
            create_content_callback: Funktion die Tab-Inhalt erstellt
            skip_save: Wenn True, nicht in Config speichern (für temporäre Tabs)
        
        Returns:
            Tab-ID
        """
        # Generiere ID
        tab_id = self.generate_tab_id()
        
        # Höchste Order finden
        max_order = max([t.get('order', 0) for t in self.tabs.values()], default=-1)
        
        # Tab-Daten
        tab_data = {
            'id': tab_id,
            'name': name,
            'icon': icon,
            'order': max_order + 1,
            'is_system': False,
            'created_at': time.strftime('%Y-%m-%d %H:%M:%S')
        }
        
        self.tabs[tab_id] = tab_data
        
        # Erstelle Tab in GUI
        if self.notebook:
            frame = tk.Frame(self.notebook, bg=self.gui.colors['bg'])
            self.notebook.add(frame, text=f"{icon} {name}")
            self.tab_widgets[tab_id] = frame
            
            # Content-Callback
            if create_content_callback:
                create_content_callback(frame)
        
        # Speichern
        if not skip_save:
            self._save_tabs()
            print(f"  ✓ Tab hinzugefügt: {icon} {name} (ID: {tab_id})")
        
        return tab_id
    
    def remove_tab(self, tab_id: str):
        """Entfernt Tab"""
        if tab_id not in self.tabs:
            return False
        
        tab_data = self.tabs[tab_id]
        
        # System-Tabs nicht löschbar
        if tab_data.get('is_system'):
            messagebox.showwarning("Warnung", 
                "System-Tabs können nicht gelöscht werden!")
            return False
        
        # Prüfe ob Cards in diesem Tab
        if self.config:
            custom_lights = self.config.get_custom_lights()
            cards_in_tab = [c for c in custom_lights.values() 
                           if c.get('tab_id') == tab_id]
            
            if cards_in_tab:
                result = messagebox.askyesno("Cards vorhanden",
                    f"Dieser Tab enthält {len(cards_in_tab)} Card(s).\n\n"
                    f"Sollen diese Cards gelöscht werden?")
                if not result:
                    return False
                
                # Lösche Cards
                for card_id in list(custom_lights.keys()):
                    if custom_lights[card_id].get('tab_id') == tab_id:
                        del custom_lights[card_id]
                
                self.config.save_config()
        
        # Entferne Tab
        del self.tabs[tab_id]
        
        # Entferne aus GUI
        if tab_id in self.tab_widgets:
            widget = self.tab_widgets[tab_id]
            # Finde Tab-Index
            for i in range(self.notebook.index('end')):
                if self.notebook.nametowidget(self.notebook.tabs()[i]) == widget:
                    self.notebook.forget(i)
                    break
            del self.tab_widgets[tab_id]
        
        self._save_tabs()
        print(f"  ✓ Tab entfernt: {tab_data['name']}")
        return True
    
    def rename_tab(self, tab_id: str, new_name: str, new_icon: str = None):
        """Benennt Tab um"""
        if tab_id not in self.tabs:
            return False
        
        tab_data = self.tabs[tab_id]
        tab_data['name'] = new_name
        
        if new_icon:
            tab_data['icon'] = new_icon
        
        # Update GUI
        if tab_id in self.tab_widgets:
            widget = self.tab_widgets[tab_id]
            for i in range(self.notebook.index('end')):
                if self.notebook.nametowidget(self.notebook.tabs()[i]) == widget:
                    icon = tab_data.get('icon', '')
                    self.notebook.tab(i, text=f"{icon} {new_name}")
                    break
        
        self._save_tabs()
        return True
    
    def reorder_tabs(self, tab_order: List[str]):
        """
        Ändert Tab-Reihenfolge
        
        Args:
            tab_order: Liste von Tab-IDs in gewünschter Reihenfolge
        """
        for i, tab_id in enumerate(tab_order):
            if tab_id in self.tabs:
                self.tabs[tab_id]['order'] = i
        
        self._save_tabs()
        print(f"  ✓ Tab-Reihenfolge aktualisiert")
    
    def get_tab_by_id(self, tab_id: str) -> Optional[dict]:
        """Holt Tab-Daten per ID"""
        return self.tabs.get(tab_id)
    
    def get_tab_by_name(self, name: str) -> Optional[dict]:
        """Holt Tab-Daten per Name (für Migration)"""
        for tab_data in self.tabs.values():
            if tab_data['name'] == name:
                return tab_data
        return None
    
    def get_all_tabs(self, sorted_by_order: bool = True) -> List[dict]:
        """
        Holt alle Tabs
        
        Args:
            sorted_by_order: Sortiert nach order-Feld
        
        Returns:
            Liste von Tab-Daten
        """
        tabs = list(self.tabs.values())
        
        if sorted_by_order:
            tabs.sort(key=lambda t: t.get('order', 999))
        
        return tabs
    
    def get_tab_widget(self, tab_id: str) -> Optional[tk.Widget]:
        """Holt Tab-Widget per ID"""
        return self.tab_widgets.get(tab_id)
    
    def get_tab_choices_for_dropdown(self) -> List[tuple]:
        """
        Holt Tab-Auswahl für Dropdowns
        
        Returns:
            Liste von (display_name, tab_id) Tupeln
        """
        choices = []
        for tab_data in self.get_all_tabs():
            icon = tab_data.get('icon', '')
            name = tab_data['name']
            tab_id = tab_data['id']
            display = f"{icon} {name}"
            choices.append((display, tab_id))
        
        return choices
    
    def create_management_dialog(self):
        """Öffnet Tab-Verwaltungs-Dialog"""
        dialog = tk.Toplevel()
        dialog.title("Tab-Verwaltung")
        dialog.geometry("600x500")
        
        # Header
        tk.Label(dialog, text="📑 Tab-Verwaltung",
                font=('Segoe UI', 16, 'bold')).pack(pady=20)
        
        # Tab-Liste
        list_frame = tk.Frame(dialog)
        list_frame.pack(fill='both', expand=True, padx=20, pady=10)
        
        # Listbox mit Scrollbar
        scrollbar = tk.Scrollbar(list_frame)
        scrollbar.pack(side='right', fill='y')
        
        listbox = tk.Listbox(list_frame, yscrollcommand=scrollbar.set,
                            font=('Segoe UI', 11), height=15)
        listbox.pack(side='left', fill='both', expand=True)
        scrollbar.config(command=listbox.yview)
        
        def refresh_list():
            """Aktualisiert Liste"""
            listbox.delete(0, 'end')
            for tab_data in self.get_all_tabs():
                icon = tab_data.get('icon', '')
                name = tab_data['name']
                system = " [System]" if tab_data.get('is_system') else ""
                listbox.insert('end', f"{icon} {name}{system}")
        
        refresh_list()
        
        # Buttons
        btn_frame = tk.Frame(dialog)
        btn_frame.pack(pady=10)
        
        def add_new_tab():
            """Fügt neuen Tab hinzu"""
            name = simpledialog.askstring("Neuer Tab", "Tab-Name:")
            if not name:
                return
            
            icon = simpledialog.askstring("Icon", "Emoji-Icon:", 
                                         initialvalue="📄")
            if not icon:
                icon = "📄"
            
            self.add_tab(name, icon)
            refresh_list()
            messagebox.showinfo("Erfolg", f"Tab '{name}' erstellt!")
        
        def rename_selected():
            """Benennt ausgewählten Tab um"""
            selection = listbox.curselection()
            if not selection:
                messagebox.showwarning("Fehler", "Bitte Tab auswählen!")
                return
            
            idx = selection[0]
            tab_data = self.get_all_tabs()[idx]
            
            if tab_data.get('is_system'):
                messagebox.showwarning("Warnung", 
                    "System-Tabs können nicht umbenannt werden!")
                return
            
            new_name = simpledialog.askstring("Umbenennen", 
                "Neuer Name:", initialvalue=tab_data['name'])
            if not new_name:
                return
            
            self.rename_tab(tab_data['id'], new_name)
            refresh_list()
        
        def delete_selected():
            """Löscht ausgewählten Tab"""
            selection = listbox.curselection()
            if not selection:
                messagebox.showwarning("Fehler", "Bitte Tab auswählen!")
                return
            
            idx = selection[0]
            tab_data = self.get_all_tabs()[idx]
            
            self.remove_tab(tab_data['id'])
            refresh_list()
        
        tk.Button(btn_frame, text="➕ Neuer Tab", command=add_new_tab,
                 font=('Segoe UI', 10), padx=15, pady=5).pack(side='left', padx=5)
        
        tk.Button(btn_frame, text="✏️ Umbenennen", command=rename_selected,
                 font=('Segoe UI', 10), padx=15, pady=5).pack(side='left', padx=5)
        
        tk.Button(btn_frame, text="🗑️ Löschen", command=delete_selected,
                 font=('Segoe UI', 10), padx=15, pady=5).pack(side='left', padx=5)
        
        # Close
        tk.Button(dialog, text="Schließen", command=dialog.destroy,
                 font=('Segoe UI', 10)).pack(pady=10)


def register(module_manager):
    """Registriert Modul"""
    module_manager.register_module(
        TabManager.NAME,
        TabManager.VERSION,
        TabManager.DESCRIPTION,
        TabManager,
        author=TabManager.AUTHOR,
        dependencies=TabManager.DEPENDENCIES
    )
