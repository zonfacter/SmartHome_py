"""
Light Plugin v2.1.0
Mit Status-Feedback & farbigem Button

🆕 v2.1.0: 
- Button ändert Farbe je nach Status
- Grün = Ein, Grau = Aus
- Live-Update vom PLC
"""

from module_manager import BaseModule
from typing import Any, Dict
import tkinter as tk


class Light(BaseModule):
    """Light Plugin mit Status-Feedback"""
    
    NAME = "light"
    VERSION = "2.1.0"
    DESCRIPTION = "Licht-Steuerung mit Status-Feedback"
    AUTHOR = "TwinCAT Team"
    
    # ⭐ SCHEMA für Card-Editor
    SCHEMA = {
        "input": {
            "type": "plc_variable",
            "label": "Input Variable (Status-Feedback)",
            "description": "PLC-Variable für Status-Rückmeldung (optional aber empfohlen!)",
            "required": False,
            "plc_type": "BOOL",
            "placeholder": "z.B. MAIN.bLichtStatus"
        },
        "output": {
            "type": "plc_variable",
            "label": "Output Variable",
            "description": "PLC-Variable zum Schalten",
            "required": True,
            "plc_type": "BOOL",
            "placeholder": "z.B. MAIN.bLichtAusgang"
        },
        "type": {
            "type": "choice",
            "label": "Schalt-Typ",
            "description": "Toggle = Umschalten, Pulse = Impuls",
            "choices": [
                {"value": "toggle", "label": "Toggle (Umschalten)"},
                {"value": "pulse", "label": "Pulse (Impuls)"}
            ],
            "default": "toggle"
        },
        "pulse_duration": {
            "type": "integer",
            "label": "Impulsdauer (ms)",
            "description": "Dauer des Impulses in Millisekunden",
            "min": 50,
            "max": 5000,
            "default": 200,
            "step": 50,
            "show_if": {"type": "pulse"}
        }
    }
    
    def __init__(self):
        super().__init__()
        self.plc = None
        self.card_widgets = {}  # card_id -> widgets dict
    
    def initialize(self, app_context: Any):
        """Initialisiert Plugin"""
        super().initialize(app_context)
        print(f"  ⚡ {self.NAME} v{self.VERSION} initialisiert")
    
    def create_card_content(self, parent: tk.Widget, card_data: dict):
        """
        Erstellt Card-Inhalt mit Status-Feedback
        
        ⭐ v2.1.0: Button ändert Farbe basierend auf Status!
        """
        card_id = card_data.get('_card_id', 'unknown')
        
        # Icon & Name
        icon = card_data.get('icon', '💡')
        name = card_data.get('name', 'Licht')
        
        tk.Label(
            parent,
            text=f"{icon} {name}",
            font=('Segoe UI', 14, 'bold'),
            bg='#f0f0f0'
        ).pack(pady=10)
        
        # ⭐ BUTTON MIT STATUS-FARBE
        output_var = card_data.get('output')
        input_var = card_data.get('input')
        button_type = card_data.get('type', 'toggle')
        
        btn_text = "Toggle" if button_type == 'toggle' else "Pulse"
        
        # Button
        button = tk.Button(
            parent,
            text=btn_text,
            font=('Segoe UI', 12, 'bold'),
            bg='#757575',  # Start: Grau (Unbekannt)
            fg='white',
            padx=30,
            pady=10,
            activebackground='#616161',
            relief=tk.RAISED,
            borderwidth=2
        )
        button.pack(pady=10)
        
        # Status-Label (optional, zeigt Wert)
        status_label = None
        if input_var:
            status_label = tk.Label(
                parent,
                text="Status: ?",
                font=('Segoe UI', 9),
                bg='#f0f0f0',
                fg='gray'
            )
            status_label.pack(pady=(0, 5))
        
        # Click-Handler
        def on_click():
            if not self.plc or not self.plc.connected:
                print(f"  ⚠️  PLC nicht verbunden!")
                return
            
            if button_type == 'toggle':
                self.plc.toggle_bool(output_var)
                print(f"  🔄 Toggle: {output_var}")
            else:
                duration = card_data.get('pulse_duration', 200)
                self.plc.pulse(output_var, duration)
                print(f"  ⚡ Pulse: {output_var} ({duration}ms)")
        
        button.config(command=on_click)
        
        # Speichere Widgets für Update
        self.card_widgets[card_id] = {
            'button': button,
            'status_label': status_label,
            'input_var': input_var,
            'output_var': output_var,
            'type': button_type
        }
    
    def update_card(self, card_id: str, card_data: dict):
        """
        Aktualisiert Card-Status (⭐ v2.1.0: Färbt Button!)
        
        Wird vom Update-Loop aufgerufen
        """
        if card_id not in self.card_widgets:
            return
        
        widgets = self.card_widgets[card_id]
        input_var = widgets['input_var']
        button = widgets['button']
        status_label = widgets['status_label']
        
        if not input_var or not self.plc or not self.plc.connected:
            # Kein Input oder PLC nicht verbunden
            button.config(bg='#757575')  # Grau
            if status_label:
                status_label.config(text="Status: ?", fg='gray')
            return
        
        # ⭐ Lese Status von PLC (nutze read_by_name!)
        try:
            import pyads
            status = self.plc.read_by_name(input_var, pyads.PLCTYPE_BOOL)
            
            if status:
                # Licht EIN
                button.config(
                    bg='#4CAF50',  # Grün
                    activebackground='#45a049'
                )
                if status_label:
                    status_label.config(text="Status: EIN", fg='#4CAF50')
            else:
                # Licht AUS
                button.config(
                    bg='#757575',  # Grau
                    activebackground='#616161'
                )
                if status_label:
                    status_label.config(text="Status: AUS", fg='#757575')
        
        except Exception as e:
            # Fehler beim Lesen
            button.config(bg='#FF5722')  # Rot = Fehler
            if status_label:
                status_label.config(text="Status: Fehler", fg='#FF5722')
            print(f"  ⚠️  Fehler beim Lesen von {input_var}: {e}")
    
    def get_schema(self) -> Dict:
        """Gibt Schema zurück für Card-Editor"""
        return self.SCHEMA
    
    def shutdown(self):
        """Cleanup"""
        self.card_widgets.clear()


def register(module_manager):
    """Registriert Modul"""
    module_manager.register_module(
        Light.NAME,
        Light.VERSION,
        Light.DESCRIPTION,
        Light,
        author=Light.AUTHOR
    )
