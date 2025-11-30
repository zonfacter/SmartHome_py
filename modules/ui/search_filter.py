"""
Search & Filter Module
Version: 1.0.0
Suchleiste und Filter-Funktionen
"""

from module_manager import BaseModule
from typing import Dict, Any, Callable, List
import tkinter as tk


class SearchFilter(BaseModule):
    """
    Suche & Filter
    
    Funktionen:
    - Live-Suchleiste
    - Kategorie-Filter
    - Ergebnis-Counter
    - Filter-Kombinationen
    """
    
    NAME = "search_filter"
    VERSION = "1.0.0"
    DESCRIPTION = "Suche & Filter für Cards"
    AUTHOR = "TwinCAT Team"
    DEPENDENCIES = ['gui_manager']
    
    def __init__(self):
        super().__init__()
        self.gui = None
        self.search_var = None
        self.filter_category = None
        self.filter_buttons = {}
        self.result_label = None
        self.on_filter_change = None  # Callback
    
    def initialize(self, app_context: Any):
        """Initialisiert Search & Filter"""
        super().initialize(app_context)
        self.app = app_context
        
        # Hole GUI-Manager
        self.gui = app_context.module_manager.get_module('gui_manager')
        
        print(f"  ⚡ {self.NAME} v{self.VERSION} initialisiert")
    
    def create_search_bar(self, parent: tk.Widget) -> tk.Frame:
        """Erstellt Suchleiste"""
        # Container
        search_frame = self.gui.create_frame(
            parent,
            bg='white',
            relief=tk.RAISED,
            borderwidth=1
        )
        
        inner = self.gui.create_frame(search_frame, bg='white', relief=tk.FLAT)
        inner.pack(fill=tk.X, padx=15, pady=10)
        
        # Such-Icon
        tk.Label(
            inner,
            text="🔍",
            font=('Segoe UI', 16),
            bg='white'
        ).pack(side=tk.LEFT, padx=(0, 10))
        
        # Suchfeld
        self.search_var = tk.StringVar()
        self.search_var.trace('w', lambda *args: self._trigger_filter())
        
        search_entry = tk.Entry(
            inner,
            textvariable=self.search_var,
            font=('Segoe UI', 12),
            bg='#f5f5f5',
            relief=tk.FLAT
        )
        search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=8)
        
        # Placeholder
        placeholder = "Suche Cards... (Name, Typ, Variable)"
        search_entry.insert(0, placeholder)
        search_entry.config(fg='gray')
        
        def on_focus_in(e):
            if search_entry.get() == placeholder:
                search_entry.delete(0, tk.END)
                search_entry.config(fg='black')
        
        def on_focus_out(e):
            if not search_entry.get():
                search_entry.insert(0, placeholder)
                search_entry.config(fg='gray')
        
        search_entry.bind('<FocusIn>', on_focus_in)
        search_entry.bind('<FocusOut>', on_focus_out)
        
        # Clear Button
        def clear_search():
            self.search_var.set('')
            search_entry.delete(0, tk.END)
            self._trigger_filter()
        
        tk.Button(
            inner,
            text="✕",
            font=('Segoe UI', 12),
            bg='white',
            relief=tk.FLAT,
            cursor='hand2',
            command=clear_search
        ).pack(side=tk.LEFT, padx=5)
        
        # Filter-Buttons
        self._create_filter_buttons(inner)
        
        # Ergebnis-Counter
        self.result_label = tk.Label(
            inner,
            text="",
            font=('Segoe UI', 9),
            bg='white',
            fg='gray'
        )
        self.result_label.pack(side=tk.RIGHT, padx=10)
        
        return search_frame
    
    def _create_filter_buttons(self, parent: tk.Widget):
        """Erstellt Filter-Buttons"""
        filter_frame = self.gui.create_frame(parent, bg='white', relief=tk.FLAT)
        filter_frame.pack(side=tk.LEFT, padx=10)
        
        self.filter_category = tk.StringVar(value='all')
        
        categories = [
            ('Alle', 'all', '📋'),
            ('Licht', 'light', '💡'),
            ('Temperatur', 'temperature', '🌡️'),
            ('Sensoren', 'gauge', '📊')
        ]
        
        for name, cat_id, icon in categories:
            btn = tk.Button(
                filter_frame,
                text=f"{icon} {name}",
                font=('Segoe UI', 9),
                bg='#e0e0e0' if cat_id != 'all' else self.gui.colors['primary'],
                fg='black' if cat_id != 'all' else 'white',
                relief=tk.FLAT,
                cursor='hand2',
                padx=10,
                pady=5,
                command=lambda c=cat_id: self.set_category(c)
            )
            btn.pack(side=tk.LEFT, padx=2)
            
            self.filter_buttons[cat_id] = btn
    
    def set_category(self, category: str):
        """Setzt Filter-Kategorie"""
        self.filter_category.set(category)
        
        # Update Button-Styles
        for cat_id, btn in self.filter_buttons.items():
            if cat_id == category:
                btn.config(bg=self.gui.colors['primary'], fg='white')
            else:
                btn.config(bg='#e0e0e0', fg='black')
        
        # Trigger Filter
        self._trigger_filter()
    
    def register_filter_callback(self, callback: Callable):
        """Registriert Callback für Filter-Änderungen"""
        self.on_filter_change = callback
    
    def _trigger_filter(self):
        """Triggert Filter-Callback"""
        if self.on_filter_change:
            search_text = self.search_var.get() if self.search_var else ""
            category = self.filter_category.get() if self.filter_category else "all"
            
            # Placeholder ignorieren
            if search_text == "Suche Cards... (Name, Typ, Variable)":
                search_text = ""
            
            self.on_filter_change(search_text.lower(), category)
    
    def update_result_count(self, visible: int, total: int):
        """Aktualisiert Ergebnis-Counter"""
        if self.result_label:
            if visible < total:
                self.result_label.config(text=f"{visible} von {total} Cards")
            else:
                self.result_label.config(text="")
    
    def get_search_text(self) -> str:
        """Gibt Suchtext zurück"""
        text = self.search_var.get() if self.search_var else ""
        if text == "Suche Cards... (Name, Typ, Variable)":
            return ""
        return text.lower()
    
    def get_category(self) -> str:
        """Gibt aktive Kategorie zurück"""
        return self.filter_category.get() if self.filter_category else "all"
    
    def clear_filters(self):
        """Setzt alle Filter zurück"""
        if self.search_var:
            self.search_var.set("")
        self.set_category('all')
    
    def shutdown(self):
        """Aufräumen"""
        pass


def register(module_manager):
    """Registriert Modul"""
    module_manager.register_module(
        SearchFilter.NAME,
        SearchFilter.VERSION,
        SearchFilter.DESCRIPTION,
        SearchFilter,
        author=SearchFilter.AUTHOR,
        dependencies=SearchFilter.DEPENDENCIES
    )
