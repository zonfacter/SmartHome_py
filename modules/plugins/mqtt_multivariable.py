"""
MQTT Multi-Variable Plugin v1.0.0
Zeigt bis zu 12 MQTT-Variablen in einer Card

Features:
- Bis zu 12 MQTT Topics
- Auto-Resize basierend auf Anzahl
- Scale: Small/Medium/Large
- Topic-Browser Integration
"""

from module_manager import BaseModule
from typing import Any, Dict
import tkinter as tk
from tkinter import ttk


class MqttMultiVariable(BaseModule):
    """MQTT Multi-Variable Plugin"""
    
    NAME = "mqtt_multivariable"
    VERSION = "1.0.0"
    DESCRIPTION = "Multi-Variable MQTT Display"
    AUTHOR = "TwinCAT Team"
    
    # ⭐ SCHEMA mit dynamischen Variablen
    SCHEMA = {
        "scale": {
            "type": "choice",
            "label": "Card-Größe",
            "description": "Skalierung der Card",
            "choices": [
                {"value": "small", "label": "Klein (kompakt)"},
                {"value": "medium", "label": "Mittel (standard)"},
                {"value": "large", "label": "Groß (übersichtlich)"}
            ],
            "default": "medium"
        },
        "layout": {
            "type": "choice",
            "label": "Layout",
            "description": "Anordnung der Variablen",
            "choices": [
                {"value": "vertical", "label": "Vertikal (untereinander)"},
                {"value": "grid", "label": "Grid (2 Spalten)"},
                {"value": "compact", "label": "Kompakt (3 Spalten)"}
            ],
            "default": "vertical"
        },
        "variables": {
            "type": "mqtt_variable_list",
            "label": "MQTT Variablen (max 12)",
            "description": "Liste der anzuzeigenden MQTT Topics",
            "min_items": 1,
            "max_items": 12,
            "item_schema": {
                "topic": {
                    "type": "mqtt_topic",
                    "label": "MQTT Topic",
                    "required": True
                },
                "label": {
                    "type": "string",
                    "label": "Anzeige-Name",
                    "required": True,
                    "placeholder": "z.B. PV-Leistung"
                },
                "unit": {
                    "type": "string",
                    "label": "Einheit",
                    "required": False,
                    "placeholder": "z.B. W, kW, %"
                },
                "decimals": {
                    "type": "integer",
                    "label": "Nachkommastellen",
                    "min": 0,
                    "max": 3,
                    "default": 1
                }
            }
        }
    }
    
    def __init__(self):
        super().__init__()
        self.mqtt = None
        self.card_widgets = {}
    
    def initialize(self, app_context: Any):
        """Initialisiert Plugin"""
        super().initialize(app_context)
        self.app = app_context
        self.mqtt = app_context.module_manager.get_module('mqtt_integration')
        print(f"  ⚡ {self.NAME} v{self.VERSION} initialisiert")
    
    def create_card_content(self, parent: tk.Widget, card_data: dict):
        """
        Erstellt Card-Inhalt mit dynamischer Anzahl Variablen
        
        ⭐ Passt Größe automatisch an!
        """
        card_id = card_data.get('_card_id', 'unknown')
        icon = card_data.get('icon', '📊')
        name = card_data.get('name', 'MQTT Monitor')
        scale = card_data.get('scale', 'medium')
        layout = card_data.get('layout', 'vertical')
        variables = card_data.get('variables', [])
        
        # Header
        header = tk.Frame(parent, bg='#f0f0f0')
        header.pack(fill='x', padx=5, pady=5)
        
        tk.Label(
            header,
            text=f"{icon} {name}",
            font=self._get_header_font(scale),
            bg='#f0f0f0'
        ).pack(side='left')
        
        # Info-Label (Anzahl Variablen)
        tk.Label(
            header,
            text=f"{len(variables)} Werte",
            font=('Segoe UI', 8),
            bg='#f0f0f0',
            fg='gray'
        ).pack(side='right')
        
        # Separator
        ttk.Separator(parent, orient='horizontal').pack(fill='x', padx=5, pady=2)
        
        # Content-Frame mit Layout
        content = tk.Frame(parent, bg='#f0f0f0')
        content.pack(fill='both', expand=True, padx=5, pady=5)
        
        # Erstelle Variablen-Widgets
        var_widgets = []
        
        for idx, var_config in enumerate(variables[:12]):  # Max 12
            widget = self._create_variable_widget(
                content, 
                var_config, 
                scale, 
                layout,
                idx
            )
            if widget:
                var_widgets.append(widget)
        
        # Speichere für Updates
        self.card_widgets[card_id] = {
            'variables': var_widgets,
            'config': variables
        }
        
        # Subscribe MQTT Topics
        if self.mqtt:
            for var_config in variables:
                topic = var_config.get('topic')
                if topic:
                    self.mqtt.subscribe(topic)
    
    def _create_variable_widget(self, parent, var_config, scale, layout, index):
        """Erstellt Widget für eine Variable"""
        topic = var_config.get('topic')
        label = var_config.get('label', topic)
        unit = var_config.get('unit', '')
        decimals = var_config.get('decimals', 1)
        
        # Frame für Variable
        var_frame = tk.Frame(parent, bg='white', relief=tk.RAISED, borderwidth=1)
        
        # Grid-Position basierend auf Layout
        if layout == 'vertical':
            var_frame.grid(row=index, column=0, sticky='ew', padx=2, pady=2)
            parent.grid_columnconfigure(0, weight=1)
        elif layout == 'grid':
            row = index // 2
            col = index % 2
            var_frame.grid(row=row, column=col, sticky='ew', padx=2, pady=2)
            parent.grid_columnconfigure(0, weight=1)
            parent.grid_columnconfigure(1, weight=1)
        else:  # compact
            row = index // 3
            col = index % 3
            var_frame.grid(row=row, column=col, sticky='ew', padx=2, pady=2)
            parent.grid_columnconfigure(0, weight=1)
            parent.grid_columnconfigure(1, weight=1)
            parent.grid_columnconfigure(2, weight=1)
        
        # Label
        label_font = self._get_label_font(scale)
        tk.Label(
            var_frame,
            text=label,
            font=label_font,
            bg='white',
            anchor='w'
        ).pack(side='left', padx=5, pady=2)
        
        # Value
        value_font = self._get_value_font(scale)
        value_label = tk.Label(
            var_frame,
            text="--",
            font=value_font,
            bg='white',
            fg='#2196F3',
            anchor='e'
        )
        value_label.pack(side='right', padx=5, pady=2)
        
        return {
            'frame': var_frame,
            'label': label,
            'value_label': value_label,
            'topic': topic,
            'unit': unit,
            'decimals': decimals
        }
    
    def _get_header_font(self, scale):
        """Gibt Header-Font basierend auf Scale"""
        sizes = {'small': 10, 'medium': 14, 'large': 18}
        return ('Segoe UI', sizes.get(scale, 14), 'bold')
    
    def _get_label_font(self, scale):
        """Gibt Label-Font basierend auf Scale"""
        sizes = {'small': 8, 'medium': 10, 'large': 12}
        return ('Segoe UI', sizes.get(scale, 10))
    
    def _get_value_font(self, scale):
        """Gibt Value-Font basierend auf Scale"""
        sizes = {'small': 10, 'medium': 12, 'large': 16}
        return ('Segoe UI', sizes.get(scale, 12), 'bold')
    
    def update_card(self, card_id: str, card_data: dict):
        """Aktualisiert alle Variablen"""
        if card_id not in self.card_widgets:
            return
        
        widgets = self.card_widgets[card_id]
        
        if not self.mqtt:
            return
        
        # Update jede Variable
        for var_widget in widgets['variables']:
            topic = var_widget['topic']
            unit = var_widget['unit']
            decimals = var_widget['decimals']
            value_label = var_widget['value_label']
            
            # Hole Wert von MQTT
            value = self.mqtt.get_value(topic)
            
            if value is not None:
                # Formatiere Wert
                try:
                    if isinstance(value, (int, float)):
                        formatted = f"{value:.{decimals}f}"
                    else:
                        formatted = str(value)
                    
                    # Mit Einheit
                    display = f"{formatted} {unit}".strip()
                    value_label.config(text=display, fg='#4CAF50')
                except:
                    value_label.config(text=str(value), fg='#FF9800')
            else:
                value_label.config(text="--", fg='gray')
    
    def get_schema(self) -> Dict:
        """Gibt Schema zurück"""
        return self.SCHEMA
    
    def shutdown(self):
        """Cleanup"""
        self.card_widgets.clear()


def register(module_manager):
    """Registriert Modul"""
    module_manager.register_module(
        MqttMultiVariable.NAME,
        MqttMultiVariable.VERSION,
        MqttMultiVariable.DESCRIPTION,
        MqttMultiVariable,
        author=MqttMultiVariable.AUTHOR
    )
