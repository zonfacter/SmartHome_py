"""
GUI Manager Module
Version: 1.0.0
Verwaltet das komplette GUI-Framework
"""

from module_manager import BaseModule
from typing import Any, Dict, Callable
import tkinter as tk
from tkinter import ttk


class GUIManager(BaseModule):
    """
    GUI-Manager
    
    Funktionen:
    - Hauptfenster-Verwaltung
    - Theme-System
    - Notebook/Tabs
    - Event-System
    """
    
    NAME = "gui_manager"
    VERSION = "1.0.0"
    DESCRIPTION = "GUI Framework & Theme-System"
    AUTHOR = "TwinCAT Team"
    
    def __init__(self):
        super().__init__()
        self.root = None
        self.notebook = None
        self.themes = {}
        self.current_theme = 'blue'
        self.colors = {}
        self.event_handlers = {}
        
    def initialize(self, app_context: Any):
        """Initialisiert GUI"""
        super().initialize(app_context)
        self.app = app_context
        print(f"  ⚡ {self.NAME} v{self.VERSION} initialisiert")
    
    def create_window(self, title: str, width: int = 1920, height: int = 1040) -> tk.Tk:
        """Erstellt Hauptfenster"""
        self.root = tk.Tk()
        self.root.title(title)
        self.root.geometry(f"{width}x{height}+0+0")
        self.root.state('zoomed')
        self.root.configure(bg='white')
        
        return self.root
    
    def define_themes(self):
        """Definiert verfügbare Themes"""
        self.themes = {
            'blue': {
                'primary': '#2196F3',
                'success': '#4CAF50',
                'danger': '#F44336',
                'warning': '#FF9800',
                'bg': '#FAFAFA',
                'card_bg': 'white',
                'text_dark': '#212121',
                'text_light': '#757575'
            },
            'dark': {
                'primary': '#1976D2',
                'success': '#388E3C',
                'danger': '#D32F2F',
                'warning': '#F57C00',
                'bg': '#303030',
                'card_bg': '#424242',
                'text_dark': '#FFFFFF',
                'text_light': '#B0B0B0'
            },
            'green': {
                'primary': '#4CAF50',
                'success': '#8BC34A',
                'danger': '#F44336',
                'warning': '#FF9800',
                'bg': '#F1F8F4',
                'card_bg': 'white',
                'text_dark': '#1B5E20',
                'text_light': '#66BB6A'
            }
        }
        
        self.apply_theme(self.current_theme)
    
    def apply_theme(self, theme_name: str):
        """Wendet Theme an"""
        if theme_name in self.themes:
            self.colors = self.themes[theme_name]
            self.current_theme = theme_name
            
            # Update Root-BG
            if self.root:
                self.root.configure(bg=self.colors['bg'])
            
            # Fire Event
            self.trigger_event('theme_changed', theme_name)
    
    def get_color(self, color_name: str) -> str:
        """Holt Farbe aus aktuellem Theme"""
        return self.colors.get(color_name, '#000000')
    
    def create_notebook(self, parent: tk.Widget) -> ttk.Notebook:
        """Erstellt Notebook für Tabs"""
        style = ttk.Style()
        style.configure('TNotebook', background=self.colors['bg'])
        style.configure('TNotebook.Tab', padding=[20, 10], font=('Segoe UI', 11))
        
        self.notebook = ttk.Notebook(parent)
        return self.notebook
    
    def add_tab(self, name: str, icon: str = "") -> tk.Frame:
        """Fügt Tab hinzu"""
        if not self.notebook:
            return None
        
        tab_frame = tk.Frame(self.notebook, bg=self.colors['bg'])
        self.notebook.add(tab_frame, text=f"{icon} {name}" if icon else name)
        
        return tab_frame
    
    def create_frame(self, parent: tk.Widget, **kwargs) -> tk.Frame:
        """Erstellt styled Frame"""
        defaults = {
            'bg': self.colors['card_bg'],
            'relief': tk.RAISED,
            'borderwidth': 1
        }
        defaults.update(kwargs)
        
        return tk.Frame(parent, **defaults)
    
    def create_button(self, parent: tk.Widget, text: str, command: Callable,
                     style: str = 'primary', **kwargs) -> tk.Button:
        """Erstellt styled Button"""
        defaults = {
            'bg': self.colors.get(style, self.colors['primary']),
            'fg': 'white',
            'font': ('Segoe UI', 10, 'bold'),
            'relief': tk.FLAT,
            'cursor': 'hand2',
            'padx': 15,
            'pady': 8
        }
        defaults.update(kwargs)
        
        btn = tk.Button(parent, text=text, command=command, **defaults)
        
        # Hover-Effekt
        def on_enter(e):
            btn['bg'] = self._darken_color(defaults['bg'])
        def on_leave(e):
            btn['bg'] = defaults['bg']
        
        btn.bind('<Enter>', on_enter)
        btn.bind('<Leave>', on_leave)
        
        return btn
    
    def _darken_color(self, hex_color: str, factor: float = 0.8) -> str:
        """Verdunkelt Farbe"""
        hex_color = hex_color.lstrip('#')
        rgb = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
        dark_rgb = tuple(int(c * factor) for c in rgb)
        return f"#{dark_rgb[0]:02x}{dark_rgb[1]:02x}{dark_rgb[2]:02x}"
    
    def register_event(self, event_name: str, handler: Callable):
        """Registriert Event-Handler"""
        if event_name not in self.event_handlers:
            self.event_handlers[event_name] = []
        self.event_handlers[event_name].append(handler)
    
    def trigger_event(self, event_name: str, *args, **kwargs):
        """Triggert Event"""
        if event_name in self.event_handlers:
            for handler in self.event_handlers[event_name]:
                try:
                    handler(*args, **kwargs)
                except Exception as e:
                    print(f"  ✗ Event-Handler Fehler ({event_name}): {e}")
    
    def show_message(self, title: str, message: str, type: str = 'info'):
        """Zeigt Message-Box"""
        from tkinter import messagebox
        
        if type == 'info':
            messagebox.showinfo(title, message)
        elif type == 'warning':
            messagebox.showwarning(title, message)
        elif type == 'error':
            messagebox.showerror(title, message)
    
    def get_root(self) -> tk.Tk:
        """Gibt Root-Window zurück"""
        return self.root
    
    def run(self):
        """Startet GUI-Loop"""
        if self.root:
            self.root.mainloop()
    
    def shutdown(self):
        """Beendet GUI"""
        if self.root:
            self.root.quit()


def register(module_manager):
    """Registriert Modul"""
    module_manager.register_module(
        GUIManager.NAME,
        GUIManager.VERSION,
        GUIManager.DESCRIPTION,
        GUIManager,
        author=GUIManager.AUTHOR
    )
