"""
Light Plugin
Version: 1.0.0
Licht-Steuerungs-Plugin für Toggle/Pulse
"""

from typing import Dict, Any
import tkinter as tk


class LightPlugin:
    """Light Card Plugin"""
    
    NAME = "light"
    VERSION = "1.0.0"
    DESCRIPTION = "Licht-Steuerung (Toggle/Pulse)"
    ICON = "💡"
    
    def __init__(self):
        self.plc = None
    
    def initialize(self, plc_module):
        """Initialisiert Plugin mit PLC-Modul"""
        self.plc = plc_module
    
    def create_card(self, parent: tk.Widget, card_id: str, config: Dict, colors: Dict) -> Dict:
        """
        Erstellt Light-Card
        
        Returns:
            Dict mit Card-Widgets
        """
        import pyads
        
        # Card Frame
        card = tk.Frame(parent, bg=colors['card_bg'], relief=tk.RAISED, borderwidth=1, cursor='hand2')
        
        # Content
        content = tk.Frame(card, bg=colors['card_bg'])
        content.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Drag Handle (oben)
        drag_handle = tk.Frame(content, bg=colors['card_bg'], relief=tk.FLAT, cursor='fleur')
        drag_handle.pack(fill=tk.X, pady=(0, 10))
        
        drag_label = tk.Label(
            drag_handle,
            text="⋮⋮⋮",
            font=('Segoe UI', 8),
            bg=colors['card_bg'],
            fg=colors.get('text_light', '#999'),
            cursor='fleur'
        )
        drag_label.pack()
        
        # Header
        header = tk.Frame(content, bg=colors['card_bg'])
        header.pack(fill=tk.X)
        
        # Icon
        icon = tk.Label(header, text=config.get('icon', self.ICON),
                       font=('Segoe UI', 32), bg=colors['card_bg'])
        icon.pack(side=tk.LEFT)
        
        # Name
        name = tk.Label(header, text=config.get('name', 'Light'),
                       font=('Segoe UI', 14, 'bold'),
                       bg=colors['card_bg'], fg=colors['text_dark'])
        name.pack(side=tk.LEFT, padx=15)
        
        # Status Canvas
        status_frame = tk.Frame(content, bg=colors['card_bg'])
        status_frame.pack(pady=20)
        
        status_canvas = tk.Canvas(status_frame, width=100, height=100,
                                 bg=colors['card_bg'], highlightthickness=0)
        status_canvas.pack()
        
        circle = status_canvas.create_oval(15, 15, 85, 85, fill='gray', outline='')
        
        # Status Text
        status_text = tk.Label(content, text="AUS",
                              font=('Segoe UI', 12, 'bold'),
                              bg=colors['card_bg'], fg=colors['text_light'])
        status_text.pack()
        
        # Button
        button_type = config.get('type', 'toggle')
        button_text = "Toggle" if button_type == 'toggle' else "Pulse"
        
        def on_click():
            output_var = config.get('output')
            
            if not output_var:
                return
            
            if not self.plc:
                return
            
            if not self.plc.connected:
                return
            
            button_type = config.get('type', 'toggle')
            
            if button_type == 'toggle':
                self.plc.toggle_bool(output_var)
            else:
                duration = config.get('pulse_duration', 200)
                self.plc.pulse(output_var, duration)
        
        button = tk.Button(content, text=button_text,
                          font=('Segoe UI', 13, 'bold'),
                          bg=colors['primary'], fg='white',
                          relief=tk.FLAT, cursor='hand2',
                          padx=30, pady=12,
                          command=on_click)
        button.pack(pady=15, fill=tk.X)
        
        # Hover-Effekt
        def on_enter(e):
            button['bg'] = '#1976D2'
        def on_leave(e):
            button['bg'] = colors['primary']
        
        button.bind("<Enter>", on_enter)
        button.bind("<Leave>", on_leave)
        
        return {
            'frame': card,
            'status_canvas': status_canvas,
            'status_circle': circle,
            'status_text': status_text,
            'button': button,
            'drag_handle': drag_handle  # Für Drag & Drop
        }
    
    def update_display(self, widgets: Dict, value: Any, colors: Dict):
        """Aktualisiert Anzeige"""
        color = colors['success'] if value else 'gray'
        text = "EIN" if value else "AUS"
        
        widgets['status_canvas'].itemconfig(widgets['status_circle'], fill=color)
        widgets['status_text'].config(text=text)
    
    def get_config_fields(self) -> list:
        """Gibt Konfigurations-Felder zurück"""
        return [
            {'name': 'input', 'type': 'variable', 'label': 'Input Variable'},
            {'name': 'output', 'type': 'variable', 'label': 'Output Variable'},
            {'name': 'type', 'type': 'choice', 'label': 'Button-Typ',
             'choices': ['toggle', 'pulse']},
            {'name': 'pulse_duration', 'type': 'number', 'label': 'Impuls-Dauer (ms)',
             'min': 50, 'max': 2000, 'default': 200}
        ]


def register(module_manager):
    """Registriert Plugin"""
    # Plugins verwenden module_manager.register_module statt register_plugin
    module_manager.register_module(
        LightPlugin.NAME,
        LightPlugin.VERSION,
        LightPlugin.DESCRIPTION,
        LightPlugin
    )
