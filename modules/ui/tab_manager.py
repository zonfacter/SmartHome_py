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
    
    def add_tab(self, name: str, icon: str = "", create_content_callback=None) -> str:
        """
        Fügt neuen Tab hinzu
        
        Args:
            name: Tab-Name
            icon: Optional icon
            create_content_callback: Funktion die Tab-Inhalt erstellt
        
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
        tab_id = f"tab_{len(self.tabs)}"
        
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
        
        return tab_id
    
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
                    self.add_tab(name, selected_icon.get())
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
        """Aufräumen"""
        pass


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
