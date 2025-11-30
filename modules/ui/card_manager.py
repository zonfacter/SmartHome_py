"""
Card Manager Module
Version: 2.0.6
Vollständiger Card-Editor mit LIVE Symbol-Browser

📁 SPEICHERORT: modules/ui/card_manager.py

Features:
- Card erstellen/bearbeiten/löschen/duplizieren
- **NEU: Live Symbol-Browser** mit Echtzeit-Werten!
- Live-Updates alle 5 Sekunden (konfigurierbar)
- Typ-Filter (ALL, BOOL, REAL, INT, DINT)
- Plugin-spezifische Felder
- Icon-Auswahl
- Etagen-Auswahl
"""

from module_manager import BaseModule
from typing import Any, Dict, Optional
import tkinter as tk
from tkinter import ttk, messagebox
import random
import string
import pyads  # Für Live-Werte im Symbol-Browser


class CardManager(BaseModule):
    """
    Card-Manager
    
    Features:
    - Card erstellen/bearbeiten/löschen
    - Symbol-Browser mit Suche
    - Plugin-spezifische Felder
    - Icon-Auswahl
    - Etagen-Auswahl
    - Live-Vorschau
    """
    
    NAME = "card_manager"
    VERSION = "2.0.7"
    DESCRIPTION = "Card-Editor & Live Symbol-Browser"
    AUTHOR = "TwinCAT Team"
    DEPENDENCIES = ['gui_manager', 'config_manager', 'symbol_manager']
    
    def __init__(self):
        super().__init__()
        self.gui = None
        self.config = None
        self.symbols = None
        self.app = None
    
    def initialize(self, app_context: Any):
        """Initialisiert Card-Manager"""
        super().initialize(app_context)
        self.app = app_context
        
        # Hole Module
        self.gui = app_context.module_manager.get_module('gui_manager')
        self.config = app_context.module_manager.get_module('config_manager')
        self.symbols = app_context.module_manager.get_module('symbol_manager')
        
        print(f"  ⚡ {self.NAME} v{self.VERSION} initialisiert")
    
    def create_management_tab(self, parent: tk.Widget) -> tk.Frame:
        """Erstellt Card-Verwaltungs-Tab"""
        main_frame = tk.Frame(parent, bg=self.gui.colors['bg'])
        main_frame.pack(fill=tk.BOTH, expand=True)  # WICHTIG: Frame packen!
        
        # Linke Seite - Card-Liste
        left_frame = tk.Frame(main_frame, bg='white', width=350)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, padx=10, pady=10)
        left_frame.pack_propagate(False)
        
        tk.Label(
            left_frame,
            text="Custom Cards",
            font=('Segoe UI', 14, 'bold'),
            bg='white',
            fg=self.gui.colors['primary']
        ).pack(anchor='w', pady=(0, 15))
        
        # Listbox mit Cards
        list_frame = tk.Frame(left_frame, bg='white')
        list_frame.pack(fill=tk.BOTH, expand=True)
        
        scrollbar = tk.Scrollbar(list_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.cards_listbox = tk.Listbox(
            list_frame,
            yscrollcommand=scrollbar.set,
            font=('Segoe UI', 10),
            bg='white',
            selectmode=tk.SINGLE
        )
        self.cards_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.cards_listbox.yview)
        
        # Lade existierende Cards (nur wenn config verfügbar)
        if self.config:
            self.refresh_card_list()
        
        # Buttons
        btn_frame = tk.Frame(left_frame, bg='white')
        btn_frame.pack(fill=tk.X, pady=(15, 0))
        
        self.gui.create_button(
            btn_frame,
            "➕ Neue Card",
            lambda: self.open_card_editor(None),
            style='success'
        ).pack(fill=tk.X, pady=2)
        
        self.gui.create_button(
            btn_frame,
            "✏️ Bearbeiten",
            self.edit_selected_card,
            style='primary'
        ).pack(fill=tk.X, pady=2)
        
        self.gui.create_button(
            btn_frame,
            "📋 Duplizieren",
            self.duplicate_selected_card,
            style='primary'
        ).pack(fill=tk.X, pady=2)
        
        self.gui.create_button(
            btn_frame,
            "🗑️ Löschen",
            self.delete_selected_card,
            style='danger'
        ).pack(fill=tk.X, pady=2)
        
        # Rechte Seite - Info/Statistik
        right_frame = tk.Frame(main_frame, bg=self.gui.colors['bg'])
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        info_card = self.gui.create_frame(right_frame)
        info_card.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        tk.Label(
            info_card,
            text="📊 Statistik",
            font=('Segoe UI', 14, 'bold'),
            bg=self.gui.colors['card_bg'],
            fg=self.gui.colors['primary']
        ).pack(pady=20)
        
        # Card-Count
        custom_lights = self.config.get_custom_lights() if self.config else {}
        
        stats_text = f"""
Gesamt: {len(custom_lights)} Custom Cards

Nach Typ:
  💡 Light: {sum(1 for c in custom_lights.values() if c.get('plugin_type') == 'light')}
  🌡️ Temperature: {sum(1 for c in custom_lights.values() if c.get('plugin_type') == 'temperature')}
  📊 Gauge: {sum(1 for c in custom_lights.values() if c.get('plugin_type') == 'gauge')}
  🌤️ Weather: {sum(1 for c in custom_lights.values() if c.get('plugin_type') == 'weather')}

Nach Etage:
  🏡 Erdgeschoss: {sum(1 for c in custom_lights.values() if '🏡' in c.get('floor', ''))}
  🔼 Obergeschoss: {sum(1 for c in custom_lights.values() if '🔼' in c.get('floor', ''))}
  ⬆️ Dachboden: {sum(1 for c in custom_lights.values() if '⬆️' in c.get('floor', ''))}
"""
        
        tk.Label(
            info_card,
            text=stats_text,
            font=('Segoe UI', 11),
            bg=self.gui.colors['card_bg'],
            fg=self.gui.colors['text_dark'],
            justify='left'
        ).pack(pady=10)
        
        return main_frame
    
    def refresh_card_list(self):
        """Aktualisiert Card-Liste"""
        if not hasattr(self, 'cards_listbox'):
            return
        
        self.cards_listbox.delete(0, tk.END)
        self.card_id_map = {}
        
        if not self.config:
            return
        
        custom_lights = self.config.get_custom_lights()
        
        for card_id, card_data in sorted(custom_lights.items()):
            name = card_data.get('name', 'Unnamed')
            plugin_type = card_data.get('plugin_type', 'light')
            floor = card_data.get('floor', '')
            
            # Icon für Typ
            icons = {'light': '💡', 'temperature': '🌡️', 'gauge': '📊', 'weather': '🌤️'}
            icon = icons.get(plugin_type, '❓')
            
            display_text = f"{icon} {name} ({floor})"
            self.cards_listbox.insert(tk.END, display_text)
            self.card_id_map[display_text] = card_id
    
    def edit_selected_card(self):
        """Bearbeitet ausgewählte Card"""
        selection = self.cards_listbox.curselection()
        if not selection:
            messagebox.showwarning("Keine Auswahl", "Bitte wähle eine Card zum Bearbeiten!")
            return
        
        display_text = self.cards_listbox.get(selection[0])
        card_id = self.card_id_map.get(display_text)
        
        if card_id:
            self.open_card_editor(card_id)
    
    def duplicate_selected_card(self):
        """Dupliziert ausgewählte Card"""
        selection = self.cards_listbox.curselection()
        if not selection:
            messagebox.showwarning("Keine Auswahl", "Bitte wähle eine Card zum Duplizieren!")
            return
        
        display_text = self.cards_listbox.get(selection[0])
        card_id = self.card_id_map.get(display_text)
        
        if card_id and self.config:
            custom_lights = self.config.get_custom_lights()
            if card_id in custom_lights:
                # Kopiere Daten
                new_data = custom_lights[card_id].copy()
                new_data['name'] = f"{new_data.get('name', 'Card')} (Kopie)"
                
                # Neue ID
                new_id = f"Card_{''.join(random.choices(string.ascii_uppercase + string.digits, k=6))}"
                
                # Speichern
                self.config.add_custom_light(new_id, new_data)
                self.refresh_card_list()
                
                messagebox.showinfo("Dupliziert", f"Card '{new_id}' wurde erstellt!")
    
    def delete_selected_card(self):
        """Löscht ausgewählte Card"""
        selection = self.cards_listbox.curselection()
        if not selection:
            messagebox.showwarning("Keine Auswahl", "Bitte wähle eine Card zum Löschen!")
            return
        
        display_text = self.cards_listbox.get(selection[0])
        card_id = self.card_id_map.get(display_text)
        
        if card_id and self.config:
            custom_lights = self.config.get_custom_lights()
            card_name = custom_lights[card_id].get('name', card_id)
            
            if messagebox.askyesno(
                "Löschen bestätigen",
                f"Card '{card_name}' wirklich löschen?\n\nDiese Aktion kann nicht rückgängig gemacht werden!"
            ):
                self.config.delete_custom_light(card_id)
                self.refresh_card_list()
                messagebox.showinfo("Gelöscht", f"Card '{card_name}' wurde gelöscht!")
    
    def open_card_editor(self, card_id: Optional[str]):
        """Öffnet Card-Editor Dialog"""
        # Dialog erstellen
        dialog = tk.Toplevel(self.gui.root)
        dialog.title("Card Editor" if card_id else "Neue Card")
        dialog.geometry("900x800")
        dialog.transient(self.gui.root)
        dialog.grab_set()
        
        # Lade Daten
        if card_id and self.config:
            custom_lights = self.config.get_custom_lights()
            card_data = custom_lights.get(card_id, {}).copy()
            is_new = False
        else:
            # Neue Card - Auto-ID
            card_id = f"Card_{''.join(random.choices(string.ascii_uppercase + string.digits, k=6))}"
            card_data = {
                'name': '',
                'icon': '💡',
                'floor': '🏡 Erdgeschoss',
                'plugin_type': 'light',
                'input': '',
                'output': '',
                'type': 'toggle',
                'pulse_duration': 200
            }
            is_new = True
        
        # Haupt-Frame
        main_frame = tk.Frame(dialog, bg='white', padx=20, pady=20)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Scrollable Container
        canvas = tk.Canvas(main_frame, bg='white')
        scrollbar = tk.Scrollbar(main_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg='white')
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Editor-Felder erstellen
        self._create_editor_fields(
            scrollable_frame,
            card_id,
            card_data,
            is_new,
            dialog
        )
    
    def _create_editor_fields(self, parent, card_id, card_data, is_new, dialog):
        """Erstellt Editor-Felder"""
        row = 0
        
        # === PLUGIN-TYP AUSWAHL ===
        tk.Label(
            parent,
            text="Card-Typ:",
            font=('Segoe UI', 12, 'bold'),
            bg='white',
            fg=self.gui.colors['primary']
        ).grid(row=row, column=0, columnspan=2, sticky='w', pady=(0, 10))
        row += 1
        
        plugin_frame = self.gui.create_frame(parent, bg='white', relief=tk.RAISED, borderwidth=1)
        plugin_frame.grid(row=row, column=0, columnspan=2, sticky='ew', pady=(0, 15))
        row += 1
        
        plugin_var = tk.StringVar(value=card_data.get('plugin_type', 'light'))
        
        # Plugin-Optionen
        plugin_options = [
            ('light', '💡 Licht-Steuerung', 'Toggle/Pulse Licht'),
            ('temperature', '🌡️ Temperatur', 'Temperatur-Anzeige'),
            ('gauge', '📊 Gauge', 'Messgerät mit Bereich'),
            ('weather', '🌤️ Wetter', 'Wetter-Anzeige')
        ]
        
        for plugin_id, plugin_name, plugin_desc in plugin_options:
            rb_frame = tk.Frame(plugin_frame, bg='white')
            rb_frame.pack(fill=tk.X, padx=10, pady=2)
            
            rb = tk.Radiobutton(
                rb_frame,
                text=plugin_name,
                variable=plugin_var,
                value=plugin_id,
                bg='white',
                font=('Segoe UI', 10, 'bold'),
                command=lambda: self._update_plugin_fields(
                    plugin_fields_frame, plugin_var, field_vars
                )
            )
            rb.pack(side=tk.LEFT)
            
            tk.Label(
                rb_frame,
                text=f"({plugin_desc})",
                font=('Segoe UI', 8),
                bg='white',
                fg='gray'
            ).pack(side=tk.LEFT, padx=5)
        
        # Container für Plugin-spezifische Felder
        plugin_fields_frame = tk.Frame(parent, bg='white')
        plugin_fields_frame.grid(row=row, column=0, columnspan=2, sticky='ew', pady=(10, 0))
        row += 1
        
        # Variablen für alle Felder
        field_vars = {
            # Light
            'input': tk.StringVar(value=card_data.get('input', '')),
            'output': tk.StringVar(value=card_data.get('output', '')),
            'type': tk.StringVar(value=card_data.get('type', 'toggle')),
            'pulse_duration': tk.IntVar(value=card_data.get('pulse_duration', 200)),
            # Temperature
            'variable': tk.StringVar(value=card_data.get('variable', '')),
            'unit': tk.StringVar(value=card_data.get('unit', 'celsius')),
            # Gauge
            'min_value': tk.DoubleVar(value=card_data.get('min_value', 0)),
            'max_value': tk.DoubleVar(value=card_data.get('max_value', 100)),
            'var_type': tk.StringVar(value=card_data.get('var_type', 'REAL')),
            # Weather
            'location': tk.StringVar(value=card_data.get('location', 'Haltern am See')),
            'temp_var': tk.StringVar(value=card_data.get('temp_var', '')),
            'humidity_var': tk.StringVar(value=card_data.get('humidity_var', '')),
            'wind_var': tk.StringVar(value=card_data.get('wind_var', '')),
            'api_key': tk.StringVar(value=card_data.get('api_key', ''))
        }
        
        # Initial: Zeige Felder für aktuellen Typ
        self._update_plugin_fields(plugin_fields_frame, plugin_var, field_vars)
        
        # === ALLGEMEINE FELDER ===
        tk.Label(
            parent,
            text="Allgemeine Einstellungen:",
            font=('Segoe UI', 12, 'bold'),
            bg='white',
            fg=self.gui.colors['primary']
        ).grid(row=row, column=0, columnspan=2, sticky='w', pady=(20, 10))
        row += 1
        
        # Card ID
        tk.Label(parent, text="Card ID:", font=('Segoe UI', 10, 'bold'),
                bg='white').grid(row=row, column=0, sticky='w', pady=5)
        
        id_var = tk.StringVar(value=card_id)
        id_entry = tk.Entry(
            parent,
            textvariable=id_var,
            font=('Segoe UI', 10),
            state='readonly' if not is_new else 'normal'
        )
        id_entry.grid(row=row, column=1, sticky='ew', pady=5, padx=(10, 0))
        row += 1
        
        # Name
        tk.Label(parent, text="Name:", font=('Segoe UI', 10, 'bold'),
                bg='white').grid(row=row, column=0, sticky='w', pady=5)
        
        name_var = tk.StringVar(value=card_data.get('name', ''))
        tk.Entry(
            parent,
            textvariable=name_var,
            font=('Segoe UI', 10)
        ).grid(row=row, column=1, sticky='ew', pady=5, padx=(10, 0))
        row += 1
        
        # Icon
        tk.Label(parent, text="Icon:", font=('Segoe UI', 10, 'bold'),
                bg='white').grid(row=row, column=0, sticky='w', pady=5)
        
        icon_frame = tk.Frame(parent, bg='white')
        icon_frame.grid(row=row, column=1, sticky='ew', pady=5, padx=(10, 0))
        
        icon_var = tk.StringVar(value=card_data.get('icon', '💡'))
        
        # Icon-Auswahl
        icons = ['💡', '🌡️', '📊', '🌤️', '🔌', '💧', '🔥', '❄️', '🌙', '⭐']
        for i, icon in enumerate(icons):
            tk.Radiobutton(
                icon_frame,
                text=icon,
                variable=icon_var,
                value=icon,
                bg='white',
                font=('Segoe UI', 14)
            ).grid(row=0, column=i, padx=2)
        row += 1
        
        # Etage
        tk.Label(parent, text="Etage:", font=('Segoe UI', 10, 'bold'),
                bg='white').grid(row=row, column=0, sticky='w', pady=5)
        
        floor_var = tk.StringVar(value=card_data.get('floor', '🏡 Erdgeschoss'))
        
        floor_frame = tk.Frame(parent, bg='white')
        floor_frame.grid(row=row, column=1, sticky='ew', pady=5, padx=(10, 0))
        
        floors = ['🏡 Erdgeschoss', '🔼 Obergeschoss', '⬆️ Dachboden']
        for floor in floors:
            tk.Radiobutton(
                floor_frame,
                text=floor,
                variable=floor_var,
                value=floor,
                bg='white',
                font=('Segoe UI', 9)
            ).pack(side=tk.LEFT, padx=5)
        row += 1
        
        # Grid-Config
        parent.grid_columnconfigure(1, weight=1)
        
        # === BUTTONS ===
        btn_frame = tk.Frame(parent, bg='white')
        btn_frame.grid(row=row, column=0, columnspan=2, sticky='ew', pady=(20, 0))
        
        def save_card():
            """Speichert Card"""
            # Sammle Daten
            new_data = {
                'plugin_type': plugin_var.get(),
                'name': name_var.get(),
                'icon': icon_var.get(),
                'floor': floor_var.get()
            }
            
            # Plugin-spezifische Felder
            plugin_type = plugin_var.get()
            if plugin_type == 'light':
                new_data.update({
                    'input': field_vars['input'].get(),
                    'output': field_vars['output'].get(),
                    'type': field_vars['type'].get(),
                    'pulse_duration': field_vars['pulse_duration'].get()
                })
            elif plugin_type == 'temperature':
                new_data.update({
                    'variable': field_vars['variable'].get(),
                    'unit': field_vars['unit'].get()
                })
            elif plugin_type == 'gauge':
                new_data.update({
                    'variable': field_vars['variable'].get(),
                    'min_value': field_vars['min_value'].get(),
                    'max_value': field_vars['max_value'].get(),
                    'unit': field_vars['unit'].get(),
                    'var_type': field_vars['var_type'].get()
                })
            elif plugin_type == 'weather':
                new_data.update({
                    'location': field_vars['location'].get(),
                    'temp_var': field_vars['temp_var'].get(),
                    'humidity_var': field_vars['humidity_var'].get(),
                    'wind_var': field_vars['wind_var'].get(),
                    'api_key': field_vars['api_key'].get()
                })
            
            # Speichern
            if self.config:
                self.config.add_custom_light(id_var.get(), new_data)
                self.refresh_card_list()
                dialog.destroy()
                messagebox.showinfo("Gespeichert", f"Card '{new_data['name']}' wurde gespeichert!")
        
        self.gui.create_button(
            btn_frame,
            "💾 Speichern",
            save_card,
            style='success'
        ).pack(side=tk.LEFT, padx=5)
        
        self.gui.create_button(
            btn_frame,
            "❌ Abbrechen",
            dialog.destroy,
            style='danger'
        ).pack(side=tk.LEFT, padx=5)
    
    def _update_plugin_fields(self, container, plugin_var, field_vars):
        """Aktualisiert Plugin-spezifische Felder"""
        # Lösche alte Felder
        for widget in container.winfo_children():
            widget.destroy()
        
        plugin_type = plugin_var.get()
        
        tk.Label(
            container,
            text=f"{plugin_type.upper()} Einstellungen:",
            font=('Segoe UI', 11, 'bold'),
            bg='white',
            fg=self.gui.colors['primary']
        ).pack(anchor='w', pady=(0, 10))
        
        # LIGHT PLUGIN
        if plugin_type == 'light':
            self._create_field(container, "Input Variable:", field_vars['input'], True)
            self._create_field(container, "Output Variable:", field_vars['output'], True)
            
            # Type
            f = tk.Frame(container, bg='white')
            f.pack(fill=tk.X, pady=5)
            tk.Label(f, text="Typ:", font=('Segoe UI', 10, 'bold'),
                    bg='white', width=18, anchor='w').pack(side=tk.LEFT)
            tk.Radiobutton(f, text="Toggle", variable=field_vars['type'],
                          value='toggle', bg='white').pack(side=tk.LEFT, padx=5)
            tk.Radiobutton(f, text="Pulse", variable=field_vars['type'],
                          value='pulse', bg='white').pack(side=tk.LEFT, padx=5)
            
            # Pulse Duration
            f = tk.Frame(container, bg='white')
            f.pack(fill=tk.X, pady=5)
            tk.Label(f, text="Impuls-Dauer (ms):", font=('Segoe UI', 10, 'bold'),
                    bg='white', width=18, anchor='w').pack(side=tk.LEFT)
            tk.Spinbox(f, from_=50, to=2000, increment=50,
                      textvariable=field_vars['pulse_duration'],
                      font=('Segoe UI', 10), width=10).pack(side=tk.LEFT, padx=5)
        
        # TEMPERATURE PLUGIN
        elif plugin_type == 'temperature':
            self._create_field(container, "Variable:", field_vars['variable'], True)
            
            # Unit
            f = tk.Frame(container, bg='white')
            f.pack(fill=tk.X, pady=5)
            tk.Label(f, text="Einheit:", font=('Segoe UI', 10, 'bold'),
                    bg='white', width=18, anchor='w').pack(side=tk.LEFT)
            tk.Radiobutton(f, text="°C", variable=field_vars['unit'],
                          value='celsius', bg='white').pack(side=tk.LEFT, padx=5)
            tk.Radiobutton(f, text="°F", variable=field_vars['unit'],
                          value='fahrenheit', bg='white').pack(side=tk.LEFT, padx=5)
        
        # GAUGE PLUGIN
        elif plugin_type == 'gauge':
            self._create_field(container, "Variable:", field_vars['variable'], True)
            
            # Min/Max
            f = tk.Frame(container, bg='white')
            f.pack(fill=tk.X, pady=5)
            tk.Label(f, text="Bereich:", font=('Segoe UI', 10, 'bold'),
                    bg='white', width=18, anchor='w').pack(side=tk.LEFT)
            tk.Label(f, text="Min:", bg='white').pack(side=tk.LEFT, padx=2)
            tk.Entry(f, textvariable=field_vars['min_value'],
                    font=('Segoe UI', 10), width=8).pack(side=tk.LEFT, padx=2)
            tk.Label(f, text="Max:", bg='white').pack(side=tk.LEFT, padx=2)
            tk.Entry(f, textvariable=field_vars['max_value'],
                    font=('Segoe UI', 10), width=8).pack(side=tk.LEFT, padx=2)
            
            self._create_field(container, "Einheit:", field_vars['unit'], False)
            
            # Var Type
            f = tk.Frame(container, bg='white')
            f.pack(fill=tk.X, pady=5)
            tk.Label(f, text="Variablen-Typ:", font=('Segoe UI', 10, 'bold'),
                    bg='white', width=18, anchor='w').pack(side=tk.LEFT)
            for vtype in ['REAL', 'INT', 'DINT']:
                tk.Radiobutton(f, text=vtype, variable=field_vars['var_type'],
                              value=vtype, bg='white').pack(side=tk.LEFT, padx=5)
        
        # WEATHER PLUGIN
        elif plugin_type == 'weather':
            self._create_field(container, "Standort:", field_vars['location'], False)
            self._create_field(container, "Temp Variable:", field_vars['temp_var'], True)
            self._create_field(container, "Feuchte Variable:", field_vars['humidity_var'], True)
            self._create_field(container, "Wind Variable:", field_vars['wind_var'], True)
            
            # API Key
            f = tk.Frame(container, bg='white')
            f.pack(fill=tk.X, pady=5)
            tk.Label(f, text="API Key (opt):", font=('Segoe UI', 10, 'bold'),
                    bg='white', width=18, anchor='w').pack(side=tk.LEFT)
            tk.Entry(f, textvariable=field_vars['api_key'],
                    font=('Segoe UI', 10), show='*').pack(side=tk.LEFT, fill=tk.X,
                                                          expand=True, padx=5)
    
    def _create_field(self, parent, label_text, var, with_search):
        """Hilfsfunktion: Erstellt Feld mit optionalem Symbol-Browser"""
        f = tk.Frame(parent, bg='white')
        f.pack(fill=tk.X, pady=5)
        
        tk.Label(f, text=label_text, font=('Segoe UI', 10, 'bold'),
                bg='white', width=18, anchor='w').pack(side=tk.LEFT)
        
        entry = tk.Entry(f, textvariable=var, font=('Segoe UI', 10))
        entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        if with_search:
            tk.Button(
                f,
                text="🔍",
                command=lambda: self._open_symbol_browser(var),
                relief=tk.FLAT,
                cursor='hand2',
                font=('Segoe UI', 12)
            ).pack(side=tk.LEFT)
    
    def _open_symbol_browser(self, target_var):
        """Öffnet Symbol-Browser mit Live-Updates"""
        # Prüfe Symbol-Manager
        if not self.symbols:
            messagebox.showerror(
                "Symbol-Manager fehlt",
                "Symbol-Manager ist nicht verfügbar!\n\n"
                "Der Symbol-Manager wird benötigt um PLC-Symbole zu durchsuchen."
            )
            return
        
        # Prüfe ob Symbole geladen sind
        symbol_count = len(self.symbols.symbols) if hasattr(self.symbols, 'symbols') else 0
        if symbol_count == 0:
            messagebox.showwarning(
                "Keine Symbole",
                "Es wurden keine PLC-Symbole geladen!\n\n"
                "Mögliche Ursachen:\n"
                "• PLC ist nicht verbunden\n"
                "• Keine Symbole in der PLC\n"
                "• Symbol-Cache ist leer\n\n"
                "Bitte stelle sicher dass die PLC verbunden ist."
            )
            return
        
        # Browser-Dialog
        browser = tk.Toplevel(self.gui.root)
        browser.title(f"Symbol-Browser ({symbol_count} Symbole verfügbar)")
        browser.geometry("900x700")  # Breiter für Werte-Spalte
        browser.transient(self.gui.root)
        browser.grab_set()  # WICHTIG: Modal machen - bleibt im Vordergrund!
        
        # Fokus auf Dialog
        browser.focus_set()
        
        # Live-Update State
        browser.live_update_active = False  # STANDARDMÄSSIG AUS!
        browser.update_interval = 5000  # 5 Sekunden
        browser.max_live_symbols = 100  # MAX 100 Symbole live!
        
        # Header-Frame mit Live-Update Toggle
        header_frame = self.gui.create_frame(browser)
        header_frame.pack(fill=tk.X, padx=10, pady=5)
        
        tk.Label(header_frame, text="🔍 Suche:",
                font=('Segoe UI', 11, 'bold'),
                bg=self.gui.colors['card_bg']).pack(side=tk.LEFT, padx=5)
        
        search_var = tk.StringVar()
        search_entry = tk.Entry(header_frame, textvariable=search_var,
                               font=('Segoe UI', 10))
        search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        search_entry.focus()
        
        # Live-Update Toggle - STANDARDMÄSSIG AUS!
        live_var = tk.BooleanVar(value=False)
        live_check = tk.Checkbutton(
            header_frame,
            text="⚪ Live-Updates (5s, max 100)",
            variable=live_var,
            font=('Segoe UI', 9),
            bg=self.gui.colors['card_bg'],
            command=lambda: setattr(browser, 'live_update_active', live_var.get())
        )
        live_check.pack(side=tk.LEFT, padx=10)
        
        # Typ-Filter Frame
        filter_frame = self.gui.create_frame(browser)
        filter_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # Typ-Filter
        type_var = tk.StringVar(value='ALL')
        tk.Label(filter_frame, text="Typ:", font=('Segoe UI', 10, 'bold'),
                bg=self.gui.colors['card_bg']).pack(side=tk.LEFT, padx=5)
        
        for typ in ['ALL', 'BOOL', 'REAL', 'INT', 'DINT']:
            tk.Radiobutton(filter_frame, text=typ, variable=type_var,
                          value=typ, bg=self.gui.colors['card_bg'],
                          command=lambda: update_results()).pack(side=tk.LEFT, padx=2)
        
        # Ergebnis-Liste mit Wert-Spalte (Treeview für Tabelle)
        list_frame = tk.Frame(browser, bg='white')
        list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Scrollbars
        vsb = tk.Scrollbar(list_frame, orient="vertical")
        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        
        hsb = tk.Scrollbar(list_frame, orient="horizontal")
        hsb.pack(side=tk.BOTTOM, fill=tk.X)
        
        # Treeview für Tabelle
        import tkinter.ttk as ttk
        result_tree = ttk.Treeview(
            list_frame,
            columns=('name', 'type', 'value'),
            show='headings',
            yscrollcommand=vsb.set,
            xscrollcommand=hsb.set
        )
        result_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        vsb.config(command=result_tree.yview)
        hsb.config(command=result_tree.xview)
        
        # Spalten konfigurieren
        result_tree.heading('name', text='Symbol-Name')
        result_tree.heading('type', text='Typ')
        result_tree.heading('value', text='Aktueller Wert')
        
        result_tree.column('name', width=400)
        result_tree.column('type', width=80)
        result_tree.column('value', width=150)
        
        # Hole PLC-Kommunikation für Live-Werte
        plc = self.app.module_manager.get_module('plc_communication') if self.app else None
        
        def read_live_value(symbol_name, symbol_type):
            """Liest Live-Wert vom PLC"""
            if not plc:
                return "---"
            
            try:
                # Bestimme PLCTYPE
                if symbol_type == 'BOOL':
                    value = plc.read_by_name(symbol_name, pyads.PLCTYPE_BOOL)
                    return "TRUE" if value else "FALSE"
                elif symbol_type == 'REAL':
                    value = plc.read_by_name(symbol_name, pyads.PLCTYPE_REAL)
                    return f"{value:.2f}" if value is not None else "---"
                elif symbol_type == 'INT':
                    value = plc.read_by_name(symbol_name, pyads.PLCTYPE_INT)
                    return str(value) if value is not None else "---"
                elif symbol_type == 'DINT':
                    value = plc.read_by_name(symbol_name, pyads.PLCTYPE_DINT)
                    return str(value) if value is not None else "---"
                else:
                    return "---"
            except:
                return "Fehler"
        
        def update_results(*args):
            """Aktualisiert Ergebnis-Liste mit Live-Werten"""
            # Lösche alte Einträge
            for item in result_tree.get_children():
                result_tree.delete(item)
            
            query = search_var.get().lower()
            typ_filter = type_var.get()
            
            # Hole Symbole - ROBUST!
            try:
                if query.strip():
                    symbols = self.symbols.search_symbols(query, limit=500)
                else:
                    # Leer = alle anzeigen (limitiert)
                    if hasattr(self.symbols, 'symbols') and isinstance(self.symbols.symbols, list):
                        symbols = self.symbols.symbols[:500]
                    else:
                        symbols = []
            except Exception as e:
                print(f"  ✗ Fehler beim Laden von Symbolen: {e}")
                symbols = []
            
            count = 0
            live_read_count = 0
            
            for symbol in symbols:
                # Skip wenn symbol kein Dict ist
                if not isinstance(symbol, dict):
                    continue
                
                # Typ-Filter
                symbol_type = symbol.get('type', 'N/A')
                if typ_filter != 'ALL' and symbol_type != typ_filter:
                    continue
                
                symbol_name = symbol.get('name', 'Unbekannt')
                
                # Lese Live-Wert NUR wenn aktiviert UND unter Limit!
                if browser.live_update_active and live_read_count < browser.max_live_symbols:
                    live_value = read_live_value(symbol_name, symbol_type)
                    live_read_count += 1
                else:
                    live_value = "---"
                
                # Füge Zeile hinzu
                result_tree.insert('', 'end', values=(symbol_name, symbol_type, live_value))
                count += 1
            
            # Hinweis bei 0 Ergebnissen
            if count == 0:
                result_tree.insert('', 'end', values=(
                    "--- Keine Symbole gefunden ---",
                    "",
                    ""
                ))
            elif live_read_count >= browser.max_live_symbols:
                # Hinweis dass Limit erreicht
                result_tree.insert('', 'end', values=(
                    f"--- Live-Update Limit erreicht ({browser.max_live_symbols} Symbole) ---",
                    "",
                    "Aktiviere Live-Updates um Werte zu sehen"
                ))
        
        def auto_update():
            """Automatisches Update alle X Sekunden"""
            if browser.winfo_exists() and browser.live_update_active:
                update_results()
                browser.after(browser.update_interval, auto_update)
        
        # Live-Suche
        search_var.trace('w', update_results)
        
        # Initial: Alle anzeigen
        update_results()
        
        # Start Auto-Update
        browser.after(browser.update_interval, auto_update)
        
        # Buttons
        btn_frame = tk.Frame(browser, bg=self.gui.colors['card_bg'])
        btn_frame.pack(fill=tk.X, padx=10, pady=10)
        
        def select_symbol():
            """Übernimmt ausgewähltes Symbol"""
            selection = result_tree.selection()
            if selection:
                item = result_tree.item(selection[0])
                values = item['values']
                if values:
                    symbol_name = values[0]  # Erste Spalte = Name
                    if symbol_name and not symbol_name.startswith('---'):
                        target_var.set(symbol_name)
                        browser.live_update_active = False  # Stoppe Updates
                        browser.destroy()
        
        # Doppelklick zum Auswählen
        result_tree.bind('<Double-1>', lambda e: select_symbol())
        
        self.gui.create_button(btn_frame, "✓ Auswählen", select_symbol,
                             style='success').pack(side=tk.LEFT, padx=5)
        
        def close_browser():
            browser.live_update_active = False  # Stoppe Updates
            browser.destroy()
        
        self.gui.create_button(btn_frame, "✕ Abbrechen", close_browser,
                             style='danger').pack(side=tk.LEFT, padx=5)
        
        # Info-Label
        info_label = tk.Label(
            btn_frame,
            text="💡 Tipp: Doppelklick zum Auswählen | Live-Updates alle 5s",
            font=('Segoe UI', 8),
            fg='gray',
            bg=self.gui.colors['card_bg']
        )
        info_label.pack(side=tk.RIGHT, padx=10)
    
    def shutdown(self):
        """Aufräumen"""
        pass


def register(module_manager):
    """Registriert Modul"""
    module_manager.register_module(
        CardManager.NAME,
        CardManager.VERSION,
        CardManager.DESCRIPTION,
        CardManager,
        author=CardManager.AUTHOR,
        dependencies=CardManager.DEPENDENCIES
    )
