"""
Tab Manager Module
Version: 2.0.4
Dynamisches Tab-Management (Hinzufügen, Löschen, Umbenennen)

📁 SPEICHERORT: modules/ui/tab_manager.py

Features:
- Tabs dynamisch hinzufügen
- Tabs umbenennen
- Tabs löschen (mit Bestätigung)
- Icon-Auswahl (10 Icons)
- Verwaltungs-Dialog
"""

from module_manager import BaseModule
from typing import Any, Dict, List
import tkinter as tk
from tkinter import ttk, simpledialog, messagebox


class TabManager(BaseModule):
    """
    Tab-Manager
    
    Features:
    - Tabs hinzufügen
    - Tabs umbenennen
    - Tabs löschen
    - Tab-Reihenfolge ändern
    - Icon-Auswahl
    """
    
    NAME = "tab_manager"
    VERSION = "2.0.4"
    DESCRIPTION = "Dynamisches Tab-Management"
    AUTHOR = "TwinCAT Team"
    DEPENDENCIES = ['gui_manager', 'config_manager']
    
    def __init__(self):
        super().__init__()
        self.gui = None
        self.config = None
        self.notebook = None
        self.tabs = {}  # tab_id -> {'frame': frame, 'name': name, 'icon': icon}
    
    def initialize(self, app_context: Any):
        """Initialisiert Tab-Manager"""
        super().initialize(app_context)
        self.app = app_context
        
        # Hole Module
        self.gui = app_context.module_manager.get_module('gui_manager')
        self.config = app_context.module_manager.get_module('config_manager')
        
        print(f"  ⚡ {self.NAME} v{self.VERSION} initialisiert")
    
    def set_notebook(self, notebook: ttk.Notebook):
        """Setzt Notebook-Widget"""
        self.notebook = notebook
        
        # Lade gespeicherte Custom-Tabs
        self._load_tabs()
    
    def add_tab(self, name: str, icon: str = "", create_content_callback=None, tab_id: str = None, skip_save: bool = False) -> str:
        """
        Fügt neuen Tab hinzu
        
        Args:
            name: Tab-Name
            icon: Optional icon
            create_content_callback: Funktion die Tab-Inhalt erstellt
            tab_id: Optional feste ID (für Laden aus Config)
            skip_save: Wenn True, wird nicht gespeichert (beim Laden aus Config)
        
        Returns:
            tab_id
        """
        if not self.notebook:
            return None
        
        # Erstelle Tab
        tab_frame = self.gui.create_frame(
            self.notebook,
            bg=self.gui.colors['bg']
        )
        
        # Tab-ID
        if tab_id is None:
            # Generiere eindeutige ID mit Timestamp
            import time
            tab_id = f"tab_{int(time.time() * 1000)}"  # Millisekunden-Timestamp
        
        # Füge zu Notebook hinzu
        tab_text = f"{icon} {name}" if icon else name
        self.notebook.add(tab_frame, text=tab_text)
        
        # Speichere
        self.tabs[tab_id] = {
            'frame': tab_frame,
            'name': name,
            'icon': icon,
            'content_callback': create_content_callback
        }
        
        # Erstelle Inhalt wenn Callback vorhanden
        if create_content_callback:
            create_content_callback(tab_frame)
        
        # WICHTIG: Speichere Tabs (außer beim Laden!)
        if not skip_save:
            self._save_tabs()
        
        return tab_id
    
    def _save_tabs(self):
        """Speichert Tab-Konfiguration"""
        if not self.config:
            return
        
        # Erstelle serialisierbares Dict (ohne callbacks und frames)
        tabs_config = {}
        for tab_id, tab_info in self.tabs.items():
            # Nur Name und Icon speichern
            tabs_config[tab_id] = {
                'name': tab_info['name'],
                'icon': tab_info['icon']
            }
        
        # Speichere in Config
        config_data = self.config.config
        config_data['custom_tabs'] = tabs_config
        self.config.save_config()
    
    def _load_tabs(self):
        """Lädt gespeicherte Tabs"""
        if not self.config:
            return
        
        config_data = self.config.config
        tabs_config = config_data.get('custom_tabs', {})
        
        # Lade jeden Tab
        for tab_id, tab_info in tabs_config.items():
            # Erstelle Tab mit Callback der tab_info übergib (closure!)
            def make_callback(info):
                return lambda parent: self._create_custom_tab_content(parent, info)
            
            self.add_tab(
                name=tab_info['name'],
                icon=tab_info.get('icon', ''),
                create_content_callback=make_callback(tab_info),
                tab_id=tab_id,
                skip_save=True  # WICHTIG: Nicht speichern beim Laden!
            )
    
    def _create_custom_tab_content(self, parent, tab_info):
        """Erstellt Inhalt für benutzerdefinierten Tab"""
        # Nutze die gleiche Logik wie für Standard-Floors
        # Tab-Name = Floor-Name für Cards
        floor_name = f"{tab_info['icon']} {tab_info['name']}" if tab_info['icon'] else tab_info['name']
        
        if self.app and hasattr(self.app, 'create_floor_content'):
            self.app.create_floor_content(parent, floor_name)
        else:
            # Fallback: Zeige Info
            tk.Label(
                parent,
                text="📝 Custom Tab",
                font=('Segoe UI', 16, 'bold'),
                bg=self.gui.colors['bg'] if self.gui else 'white'
            ).pack(pady=20)
            
            tk.Label(
                parent,
                text="Füge Cards über 'Card-Verwaltung' hinzu\nund wähle diesen Tab als Etage.",
                font=('Segoe UI', 10),
                bg=self.gui.colors['bg'] if self.gui else 'white',
                fg='gray'
            ).pack(pady=10)
    
    def remove_tab(self, tab_id: str) -> bool:
        """Entfernt Tab"""
        if tab_id not in self.tabs:
            return False
        
        tab_info = self.tabs[tab_id]
        
        # Bestätige Löschung
        if not messagebox.askyesno(
            "Tab löschen",
            f"Tab '{tab_info['name']}' wirklich löschen?"
        ):
            return False
        
        # Finde Index
        for i in range(self.notebook.index('end')):
            if self.notebook.nametowidget(self.notebook.tabs()[i]) == tab_info['frame']:
                self.notebook.forget(i)
                break
        
        # Entferne aus Dict
        del self.tabs[tab_id]
        
        # WICHTIG: Speichere Änderung!
        self._save_tabs()
        
        return True
    
    def rename_tab(self, tab_id: str, new_name: str = None, new_icon: str = None):
        """Benennt Tab um"""
        if tab_id not in self.tabs:
            return False
        
        tab_info = self.tabs[tab_id]
        
        # Dialog für neuen Namen
        if new_name is None:
            new_name = simpledialog.askstring(
                "Tab umbenennen",
                f"Neuer Name für '{tab_info['name']}':",
                initialvalue=tab_info['name']
            )
            if not new_name:
                return False
        
        # Update Name
        tab_info['name'] = new_name
        
        # Update Icon wenn gegeben
        if new_icon:
            tab_info['icon'] = new_icon
        
        # Finde Tab-Index und update Text
        for i in range(self.notebook.index('end')):
            if self.notebook.nametowidget(self.notebook.tabs()[i]) == tab_info['frame']:
                icon = tab_info.get('icon', '')
                tab_text = f"{icon} {new_name}" if icon else new_name
                self.notebook.tab(i, text=tab_text)
                break
        
        return True
    
    def create_management_dialog(self):
        """Öffnet Tab-Verwaltungs-Dialog"""
        dialog = tk.Toplevel(self.gui.root)
        dialog.title("📑 Tab-Verwaltung")
        dialog.geometry("500x400")
        dialog.transient(self.gui.root)
        dialog.grab_set()  # Modal machen
        
        # Liste der Tabs
        list_frame = tk.Frame(dialog, bg='white')
        list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        tk.Label(
            list_frame,
            text="Bestehende Tabs:",
            font=('Segoe UI', 12, 'bold'),
            bg='white'
        ).pack(anchor='w', pady=(0, 10))
        
        # Listbox
        scrollbar = tk.Scrollbar(list_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        tab_listbox = tk.Listbox(
            list_frame,
            yscrollcommand=scrollbar.set,
            font=('Segoe UI', 10)
        )
        tab_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=tab_listbox.yview)
        
        # Lade Tabs
        tab_id_map = {}
        for tab_id, tab_info in self.tabs.items():
            icon = tab_info.get('icon', '')
            name = tab_info['name']
            display = f"{icon} {name}" if icon else name
            tab_listbox.insert(tk.END, display)
            tab_id_map[display] = tab_id
        
        # Buttons
        btn_frame = tk.Frame(dialog, bg='white')
        btn_frame.pack(fill=tk.X, padx=10, pady=10)
        
        def rename_selected():
            """Umbenennen"""
            selection = tab_listbox.curselection()
            if not selection:
                return
            display = tab_listbox.get(selection[0])
            tab_id = tab_id_map.get(display)
            if tab_id:
                self.rename_tab(tab_id)
                dialog.destroy()
                self.create_management_dialog()  # Refresh
        
        def delete_selected():
            """Löschen"""
            selection = tab_listbox.curselection()
            if not selection:
                return
            display = tab_listbox.get(selection[0])
            tab_id = tab_id_map.get(display)
            if tab_id:
                self.remove_tab(tab_id)
                dialog.destroy()
        
        def add_new():
            """Neuen Tab hinzufügen"""
            name = simpledialog.askstring("Neuer Tab", "Tab-Name:")
            if name:
                # Icon-Auswahl
                icon_dialog = tk.Toplevel(dialog)
                icon_dialog.title("Icon wählen")
                icon_dialog.geometry("400x200")
                icon_dialog.transient(dialog)
                
                selected_icon = tk.StringVar(value='📋')
                
                tk.Label(icon_dialog, text="Wähle Icon:",
                        font=('Segoe UI', 11, 'bold')).pack(pady=10)
                
                icon_frame = tk.Frame(icon_dialog)
                icon_frame.pack()
                
                icons = ['📋', '🏡', '🔼', '⬆️', '☀️', '🌤️', '📊', '🎥', '🔧', '⚙️']
                for i, icon in enumerate(icons):
                    tk.Radiobutton(
                        icon_frame,
                        text=icon,
                        variable=selected_icon,
                        value=icon,
                        font=('Segoe UI', 16)
                    ).grid(row=i//5, column=i%5, padx=5, pady=5)
                
                def confirm_icon():
                    icon_dialog.destroy()
                    # Erstelle Tab mit content_callback für Cards
                    tab_id = self.add_tab(
                        name, 
                        selected_icon.get(),
                        create_content_callback=lambda parent: self.app.create_floor_content(parent, f"{selected_icon.get()} {name}")
                    )
                    # Tab wird automatisch in add_tab() gespeichert
                    dialog.destroy()
                    self.create_management_dialog()  # Refresh
                
                tk.Button(icon_dialog, text="✓ OK",
                         command=confirm_icon).pack(pady=10)
        
        self.gui.create_button(
            btn_frame,
            "➕ Neuer Tab",
            add_new,
            style='success'
        ).pack(side=tk.LEFT, padx=5)
        
        self.gui.create_button(
            btn_frame,
            "✏️ Umbenennen",
            rename_selected,
            style='primary'
        ).pack(side=tk.LEFT, padx=5)
        
        self.gui.create_button(
            btn_frame,
            "🗑️ Löschen",
            delete_selected,
            style='danger'
        ).pack(side=tk.LEFT, padx=5)
        
        self.gui.create_button(
            btn_frame,
            "✕ Schließen",
            dialog.destroy,
            style='primary'
        ).pack(side=tk.RIGHT, padx=5)
    
    def get_all_tabs(self) -> Dict:
        """Gibt alle Tabs zurück"""
        return self.tabs
    
    def shutdown(self):
        """Speichert Tabs beim Beenden"""
        self._save_tabs()


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
