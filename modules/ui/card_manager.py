"""
Card Manager v3.3.1
Dynamische Eingabemasken + MQTT + robustes ID-Mapping

📁 SPEICHERORT: modules/ui/card_manager.py

🆕 v3.3.1 KRITISCHER FIX:
- Robustes Card-ID Mapping (direkte Liste!)
- Plugin-Check & Markierung
- Fixes Index-Versatz Bug ("Flur" öffnete "PV")

🆕 v3.3.0:
- MQTT Topic-Browser 📡
- Dynamische Variablen-Listen (bis 12)

🆕 v3.2.0:
- Dynamische Felder aus Plugin-Schema
- Symbol-Browser für PLC-Variablen
- Conditional Fields (show_if)
"""

from module_manager import BaseModule
from typing import Any, Dict
import tkinter as tk
from tkinter import ttk, messagebox
import random
import string


class CardManager(BaseModule):
    """
    Card Manager v3.3.1
    
    ⭐ v3.3.1: Robustes Card-ID Mapping!
    - Direkte ID-Liste statt Text-Mapping
    - Plugin-Check & Markierung
    - Fixes Index-Versatz Bug
    
    ⭐ v3.3.0: MQTT Features!
    - MQTT Topic-Browser
    - Dynamische Variablen-Listen
    
    ⭐ v3.2.0: Schema-basierte Eingabemasken!
    - Liest Schema von Plugins
    - Generiert Felder dynamisch
    - Symbol-Browser für PLC-Variablen
    """
    
    NAME = "card_manager"
    VERSION = "3.3.1"
    DESCRIPTION = "Schema-basierter Card-Editor (Index-Fix)"
    AUTHOR = "TwinCAT Team"
    DEPENDENCIES = ['gui_manager', 'config_manager']
    
    def __init__(self):
        super().__init__()
        self.gui = None
        self.config = None
        self.app = None
        self.symbol_manager = None
        
        # ⭐ v3.3.1: Robustes ID-Mapping
        self.card_ids = []  # Direkte ID-Liste parallel zur Listbox!
        self.available_plugins = {}  # Plugin-Check
    
    def initialize(self, app_context: Any):
        """Initialisiert Card-Manager"""
        super().initialize(app_context)
        self.app = app_context
        
        # Hole Module
        self.gui = app_context.module_manager.get_module('gui_manager')
        self.config = app_context.module_manager.get_module('config_manager')
        self.symbol_manager = app_context.module_manager.get_module('symbol_manager')
        
        # ⭐ v3.3.1: Scanne verfügbare Plugins
        self._scan_available_plugins()
        
        print(f"  ⚡ {self.NAME} v{self.VERSION} initialisiert")
    
    def _scan_available_plugins(self):
        """⭐ v3.3.1: Scannt welche Plugins verfügbar sind"""
        all_modules = self.app.module_manager.get_all_modules()
        
        # Finde alle Plugins
        for name, info in all_modules.items():
            module = info.module_object
            if module and hasattr(module, 'create_card_content'):
                self.available_plugins[name] = True
        
        print(f"     📦 {len(self.available_plugins)} Plugins verfügbar")
    
    def create_management_tab(self, parent: tk.Widget):
        """Erstellt Card-Verwaltungs-Tab"""
        # Main Frame
        main_frame = tk.Frame(parent, bg=self.gui.colors['bg'])
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Header
        header = tk.Frame(main_frame, bg=self.gui.colors['bg'])
        header.pack(fill='x', pady=(0, 20))
        
        tk.Label(
            header,
            text="⚙️ Card-Verwaltung v3.2",
            font=('Segoe UI', 16, 'bold'),
            bg=self.gui.colors['bg'],
            fg=self.gui.colors['text_dark']
        ).pack(side='left')
        
        # Neue Card Button
        self.gui.create_button(
            header,
            "➕ Neue Card",
            lambda: self.open_card_editor(),
            style='success'
        ).pack(side='right', padx=5)
        
        # Card-Liste
        list_frame = tk.Frame(main_frame, bg='white', relief=tk.RAISED, borderwidth=2)
        list_frame.pack(fill='both', expand=True)
        
        # Scrollbar
        scrollbar = tk.Scrollbar(list_frame)
        scrollbar.pack(side='right', fill='y')
        
        # Listbox
        self.card_listbox = tk.Listbox(
            list_frame,
            yscrollcommand=scrollbar.set,
            font=('Segoe UI', 11),
            bg='white',
            selectmode=tk.SINGLE
        )
        self.card_listbox.pack(side='left', fill='both', expand=True)
        scrollbar.config(command=self.card_listbox.yview)
        
        # Lade Cards
        self.refresh_card_list()
        
        # Buttons
        btn_frame = tk.Frame(main_frame, bg=self.gui.colors['bg'])
        btn_frame.pack(fill='x', pady=(10, 0))
        
        self.gui.create_button(
            btn_frame,
            "✏️ Bearbeiten",
            self.edit_selected_card,
            style='primary'
        ).pack(side='left', padx=5)
        
        self.gui.create_button(
            btn_frame,
            "📋 Duplizieren",
            self.duplicate_selected_card,
            style='primary'
        ).pack(side='left', padx=5)
        
        self.gui.create_button(
            btn_frame,
            "🗑️ Löschen",
            self.delete_selected_card,
            style='danger'
        ).pack(side='left', padx=5)
        
        # Statistik
        stats_frame = tk.Frame(main_frame, bg=self.gui.colors['bg'])
        stats_frame.pack(fill='x', pady=(10, 0))
        
        self.stats_label = tk.Label(
            stats_frame,
            text="",
            font=('Segoe UI', 9),
            bg=self.gui.colors['bg'],
            fg=self.gui.colors['text_light']
        )
        self.stats_label.pack()
        
        self.update_stats()
    
    def refresh_card_list(self):
        """
        ⭐ v3.3.1: Aktualisiert Card-Liste mit direktem ID-Mapping
        """
        self.card_listbox.delete(0, 'end')
        self.card_ids = []  # ⭐ Reset!
        
        if not self.config:
            return
        
        # Hole Cards
        custom_lights = self.config.get_custom_lights()
        
        # Hole TabManager für Tab-Namen
        tab_manager = self.app.module_manager.get_module('tab_manager')
        
        # ⭐ Sort nach Namen (nicht ID!)
        sorted_cards = sorted(
            custom_lights.items(),
            key=lambda x: x[1].get('name', '').lower()
        )
        
        for card_id, card_data in sorted_cards:
            icon = card_data.get('icon', '💡')
            name = card_data.get('name', card_id)
            plugin_type = card_data.get('plugin_type', 'light')
            
            # ⭐ v3.3.1: Prüfe ob Plugin verfügbar
            if plugin_type not in self.available_plugins:
                icon = '⚠️'
                name = f"{name} [Plugin fehlt!]"
            
            # Hole Tab-Name von tab_id
            tab_id = card_data.get('tab_id', '')
            tab_name = 'N/A'
            
            if tab_manager and tab_id:
                tab_data = tab_manager.get_tab_by_id(tab_id)
                if tab_data:
                    tab_icon = tab_data.get('icon', '')
                    tab_name = f"{tab_icon} {tab_data['name']}"
            
            display = f"{icon} {name} → {tab_name}"
            
            # ⭐ v3.3.1: Füge zu Listbox UND ID-Liste hinzu
            self.card_listbox.insert('end', display)
            self.card_ids.append(card_id)  # ← Gleicher Index!
        
        print(f"  🔄 Card-Liste aktualisiert: {len(self.card_ids)} Cards")
    
    def update_stats(self):
        """Aktualisiert Statistik"""
        if not self.config:
            return
        
        custom_lights = self.config.get_custom_lights()
        total = len(custom_lights)
        
        # Zähle nach Plugin-Typ
        by_type = {}
        for card_data in custom_lights.values():
            plugin_type = card_data.get('plugin_type', 'unknown')
            by_type[plugin_type] = by_type.get(plugin_type, 0) + 1
        
        stats = f"📊 Gesamt: {total} Cards"
        for ptype, count in sorted(by_type.items()):
            stats += f" | {ptype}: {count}"
        
        self.stats_label.config(text=stats)
    
    def edit_selected_card(self):
        """Bearbeitet ausgewählte Card"""
        selection = self.card_listbox.curselection()
        if not selection:
            messagebox.showwarning("Fehler", "Bitte Card auswählen!")
            return
        
        idx = selection[0]
        custom_lights = self.config.get_custom_lights()
        card_id = list(custom_lights.keys())[idx]
        card_data = custom_lights[card_id]
        
        self.open_card_editor(card_id, card_data)
    
    def duplicate_selected_card(self):
        """Dupliziert ausgewählte Card"""
        selection = self.card_listbox.curselection()
        if not selection:
            messagebox.showwarning("Fehler", "Bitte Card auswählen!")
            return
        
        idx = selection[0]
        custom_lights = self.config.get_custom_lights()
        card_id = list(custom_lights.keys())[idx]
        card_data = custom_lights[card_id].copy()
        
        # Neue ID
        new_id = f"Card_{''.join(random.choices(string.ascii_uppercase + string.digits, k=6))}"
        card_data['name'] = f"{card_data.get('name', 'Card')} (Kopie)"
        
        # Speichern
        custom_lights[new_id] = card_data
        self.config.save_config()
        
        self.refresh_card_list()
        self.update_stats()
        messagebox.showinfo("Erfolg", "Card dupliziert!")
    
    def delete_selected_card(self):
        """Löscht ausgewählte Card"""
        selection = self.card_listbox.curselection()
        if not selection:
            messagebox.showwarning("Fehler", "Bitte Card auswählen!")
            return
        
        idx = selection[0]
        custom_lights = self.config.get_custom_lights()
        card_id = list(custom_lights.keys())[idx]
        card_name = custom_lights[card_id].get('name', card_id)
        
        if messagebox.askyesno("Löschen", f"Card '{card_name}' wirklich löschen?"):
            del custom_lights[card_id]
            self.config.save_config()
            
            self.refresh_card_list()
            self.update_stats()
            messagebox.showinfo("Erfolg", "Card gelöscht!")
    
    def open_symbol_browser(self, variable_var: tk.StringVar, plc_type: str = None):
        """
        Öffnet Symbol-Browser
        
        Args:
            variable_var: StringVar die aktualisiert werden soll
            plc_type: Optional PLC-Typ Filter (BOOL, REAL, INT, ...)
        """
        if not self.symbol_manager:
            messagebox.showerror("Fehler", "Symbol-Manager nicht verfügbar!")
            return
        
        # Dialog
        dialog = tk.Toplevel()
        dialog.title("🔍 Symbol-Browser")
        dialog.geometry("800x600")
        
        # Header
        header = tk.Frame(dialog, bg='white')
        header.pack(fill='x', padx=10, pady=10)
        
        tk.Label(header, text="🔍 Symbol-Browser",
                font=('Segoe UI', 14, 'bold'), bg='white').pack(side='left')
        
        if plc_type:
            tk.Label(header, text=f"Filter: {plc_type}",
                    font=('Segoe UI', 10), bg='white', fg='gray').pack(side='right')
        
        # Suche
        search_frame = tk.Frame(dialog, bg='white')
        search_frame.pack(fill='x', padx=10, pady=(0, 10))
        
        tk.Label(search_frame, text="Suche:", font=('Segoe UI', 10),
                bg='white').pack(side='left', padx=5)
        
        search_var = tk.StringVar()
        search_entry = tk.Entry(search_frame, textvariable=search_var,
                               font=('Segoe UI', 10), width=50)
        search_entry.pack(side='left', padx=5, fill='x', expand=True)
        
        # Liste
        list_frame = tk.Frame(dialog, bg='white')
        list_frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        scrollbar = tk.Scrollbar(list_frame)
        scrollbar.pack(side='right', fill='y')
        
        symbol_listbox = tk.Listbox(
            list_frame,
            yscrollcommand=scrollbar.set,
            font=('Consolas', 10),
            bg='white'
        )
        symbol_listbox.pack(side='left', fill='both', expand=True)
        scrollbar.config(command=symbol_listbox.yview)
        
        def update_list():
            """Aktualisiert Symbol-Liste"""
            symbol_listbox.delete(0, 'end')
            search = search_var.get().lower()
            
            # Hole Symbole
            symbols = self.symbol_manager.search_symbols(search) if search else []
            
            if not search:
                # Zeige Info
                symbol_listbox.insert('end', "💡 Gib Suchbegriff ein...")
                return
            
            # Filtere nach Typ
            if plc_type:
                symbols = [s for s in symbols if s.get('type', '') == plc_type]
            
            # Zeige Symbole
            for symbol in symbols[:500]:  # Max 500
                name = symbol.get('name', '')
                stype = symbol.get('type', '')
                display = f"{name:<60} {stype}"
                symbol_listbox.insert('end', display)
            
            if not symbols:
                symbol_listbox.insert('end', "❌ Keine Symbole gefunden")
        
        # Live-Suche
        search_var.trace('w', lambda *args: update_list())
        
        # Buttons
        btn_frame = tk.Frame(dialog, bg='white')
        btn_frame.pack(fill='x', padx=10, pady=10)
        
        def select_symbol():
            """Wählt Symbol aus"""
            selection = symbol_listbox.curselection()
            if not selection:
                return
            
            text = symbol_listbox.get(selection[0])
            if text.startswith('💡') or text.startswith('❌'):
                return
            
            # Extrahiere Symbol-Name
            symbol_name = text.split()[0]
            variable_var.set(symbol_name)
            dialog.destroy()
        
        tk.Button(btn_frame, text="✓ Auswählen", command=select_symbol,
                 font=('Segoe UI', 11, 'bold'), bg='#4CAF50', fg='white',
                 padx=30, pady=10).pack(side='left', padx=5)
        
        tk.Button(btn_frame, text="✕ Abbrechen", command=dialog.destroy,
                 font=('Segoe UI', 11, 'bold'), bg='#757575', fg='white',
                 padx=30, pady=10).pack(side='left', padx=5)
        
        # Doppelklick = Auswählen
        symbol_listbox.bind('<Double-1>', lambda e: select_symbol())
    
    def open_mqtt_topic_browser(self, topic_var: tk.StringVar):
        """
        Öffnet MQTT Topic-Browser
        
        Args:
            topic_var: StringVar die aktualisiert werden soll
        """
        mqtt = self.app.module_manager.get_module('mqtt_integration')
        
        if not mqtt:
            messagebox.showerror("Fehler", "MQTT nicht verfügbar!")
            return
        
        # Dialog
        dialog = tk.Toplevel()
        dialog.title("📡 MQTT Topic-Browser")
        dialog.geometry("800x600")
        
        # Header
        header = tk.Frame(dialog, bg='white')
        header.pack(fill='x', padx=10, pady=10)
        
        tk.Label(header, text="📡 MQTT Topic-Browser",
                font=('Segoe UI', 14, 'bold'), bg='white').pack(side='left')
        
        # Info
        if mqtt.connected:
            tk.Label(header, text=f"✓ Verbunden: {mqtt.config.get('broker', 'N/A')}",
                    font=('Segoe UI', 10), bg='white', fg='green').pack(side='right')
        else:
            tk.Label(header, text="⚠️ Nicht verbunden",
                    font=('Segoe UI', 10), bg='white', fg='red').pack(side='right')
        
        # Suche
        search_frame = tk.Frame(dialog, bg='white')
        search_frame.pack(fill='x', padx=10, pady=(0, 10))
        
        tk.Label(search_frame, text="Filter:", font=('Segoe UI', 10),
                bg='white').pack(side='left', padx=5)
        
        search_var = tk.StringVar()
        search_entry = tk.Entry(search_frame, textvariable=search_var,
                               font=('Segoe UI', 10), width=50)
        search_entry.pack(side='left', padx=5, fill='x', expand=True)
        
        # Liste
        list_frame = tk.Frame(dialog, bg='white')
        list_frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        scrollbar = tk.Scrollbar(list_frame)
        scrollbar.pack(side='right', fill='y')
        
        topic_listbox = tk.Listbox(
            list_frame,
            yscrollcommand=scrollbar.set,
            font=('Consolas', 10),
            bg='white'
        )
        topic_listbox.pack(side='left', fill='both', expand=True)
        scrollbar.config(command=topic_listbox.yview)
        
        def update_list():
            """Aktualisiert Topic-Liste"""
            topic_listbox.delete(0, 'end')
            search = search_var.get().lower()
            
            # Hole alle gecachten Topics
            all_values = mqtt.get_all_values()
            
            if not all_values:
                topic_listbox.insert('end', "ℹ️ Keine Topics empfangen")
                topic_listbox.insert('end', "💡 Tipp: Warte bis MQTT Daten empfängt")
                return
            
            # Filtere Topics
            topics = []
            for topic, value in all_values.items():
                if not search or search in topic.lower():
                    topics.append((topic, value))
            
            # Sortiere
            topics.sort()
            
            # Zeige Topics
            for topic, value in topics[:500]:
                # Formatiere Wert
                if isinstance(value, (int, float)):
                    val_str = f"{value:.2f}" if isinstance(value, float) else str(value)
                else:
                    val_str = str(value)[:20]
                
                display = f"{topic:<50} = {val_str}"
                topic_listbox.insert('end', display)
            
            if not topics:
                topic_listbox.insert('end', "❌ Keine Topics gefunden")
        
        # Live-Update
        search_var.trace('w', lambda *args: update_list())
        
        # Initial update
        update_list()
        
        # Auto-Refresh alle 2 Sekunden
        def auto_refresh():
            if dialog.winfo_exists():
                update_list()
                dialog.after(2000, auto_refresh)
        
        auto_refresh()
        
        # Buttons
        btn_frame = tk.Frame(dialog, bg='white')
        btn_frame.pack(fill='x', padx=10, pady=10)
        
        def select_topic():
            """Wählt Topic aus"""
            selection = topic_listbox.curselection()
            if not selection:
                return
            
            text = topic_listbox.get(selection[0])
            if text.startswith('ℹ️') or text.startswith('💡') or text.startswith('❌'):
                return
            
            # Extrahiere Topic
            topic = text.split('=')[0].strip()
            topic_var.set(topic)
            dialog.destroy()
        
        tk.Button(btn_frame, text="✓ Auswählen", command=select_topic,
                 font=('Segoe UI', 11, 'bold'), bg='#4CAF50', fg='white',
                 padx=30, pady=10).pack(side='left', padx=5)
        
        tk.Button(btn_frame, text="🔄 Aktualisieren", command=update_list,
                 font=('Segoe UI', 11, 'bold'), bg='#2196F3', fg='white',
                 padx=30, pady=10).pack(side='left', padx=5)
        
        tk.Button(btn_frame, text="✕ Abbrechen", command=dialog.destroy,
                 font=('Segoe UI', 11, 'bold'), bg='#757575', fg='white',
                 padx=30, pady=10).pack(side='left', padx=5)
        
        # Doppelklick = Auswählen
        topic_listbox.bind('<Double-1>', lambda e: select_topic())
    
    def _create_mqtt_variable_list(self, parent, start_row, field_name, field_spec, card_data, field_vars):
        """
        Erstellt dynamische Variablen-Liste (bis zu 12 Items)
        
        ⭐ MEGA FEATURE: Dynamisch Variablen hinzufügen/entfernen!
        """
        min_items = field_spec.get('min_items', 1)
        max_items = field_spec.get('max_items', 12)
        item_schema = field_spec.get('item_schema', {})
        
        # Existierende Variablen aus card_data
        existing_vars = card_data.get(field_name, [])
        
        # Container
        list_container = tk.Frame(parent, bg='white')
        list_container.grid(row=start_row, column=0, columnspan=3, sticky='ew', pady=10)
        
        # Header
        header_frame = tk.Frame(list_container, bg='white')
        header_frame.pack(fill='x')
        
        tk.Label(header_frame, text="📊 MQTT Variablen (max 12)",
                font=('Segoe UI', 11, 'bold'), bg='white').pack(side='left')
        
        count_label = tk.Label(header_frame, text=f"{len(existing_vars)}/12",
                              font=('Segoe UI', 10), bg='white', fg='gray')
        count_label.pack(side='right')
        
        # Scrollable Variable-Liste
        canvas = tk.Canvas(list_container, bg='white', height=300)
        scrollbar = tk.Scrollbar(list_container, orient='vertical', command=canvas.yview)
        variables_frame = tk.Frame(canvas, bg='white')
        
        variables_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=variables_frame, anchor='nw')
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')
        
        # Liste für Variable-Widgets
        variable_widgets = []
        
        def create_variable_widget(var_data=None, index=None):
            """Erstellt Widget für eine Variable"""
            # Frame für Variable
            var_frame = tk.Frame(variables_frame, bg='#f5f5f5', relief=tk.RAISED, borderwidth=1)
            var_frame.pack(fill='x', padx=5, pady=5)
            
            # Header (Nummer + Delete)
            var_header = tk.Frame(var_frame, bg='#e0e0e0')
            var_header.pack(fill='x')
            
            tk.Label(var_header, text=f"Variable #{len(variable_widgets)+1}",
                    font=('Segoe UI', 9, 'bold'), bg='#e0e0e0').pack(side='left', padx=5, pady=2)
            
            # Delete Button
            delete_btn = tk.Button(var_header, text="🗑️", 
                                   command=lambda: delete_variable(var_frame),
                                   bg='#e0e0e0', relief=tk.FLAT)
            delete_btn.pack(side='right', padx=5)
            
            # Fields
            fields_frame = tk.Frame(var_frame, bg='#f5f5f5')
            fields_frame.pack(fill='x', padx=5, pady=5)
            
            var_fields = {}
            field_row = 0
            
            for sub_field_name, sub_field_spec in item_schema.items():
                sub_field_type = sub_field_spec.get('type')
                sub_label = sub_field_spec.get('label', sub_field_name)
                
                # Label
                tk.Label(fields_frame, text=f"{sub_label}:",
                        font=('Segoe UI', 9), bg='#f5f5f5').grid(
                    row=field_row, column=0, sticky='w', padx=5, pady=2)
                
                # Field
                if sub_field_type == 'mqtt_topic':
                    # MQTT Topic mit Browser
                    value = var_data.get(sub_field_name, '') if var_data else ''
                    var = tk.StringVar(value=value)
                    
                    entry_frame = tk.Frame(fields_frame, bg='#f5f5f5')
                    entry_frame.grid(row=field_row, column=1, sticky='ew', padx=5, pady=2)
                    
                    entry = tk.Entry(entry_frame, textvariable=var, font=('Segoe UI', 9), width=30)
                    entry.pack(side='left', padx=(0, 5))
                    
                    tk.Button(entry_frame, text="📡",
                             command=lambda v=var: self.open_mqtt_topic_browser(v),
                             font=('Segoe UI', 8)).pack(side='left')
                    
                    var_fields[sub_field_name] = var
                
                elif sub_field_type == 'integer':
                    # Integer
                    value = var_data.get(sub_field_name, sub_field_spec.get('default', 0)) if var_data else sub_field_spec.get('default', 0)
                    var = tk.IntVar(value=value)
                    
                    min_val = sub_field_spec.get('min', 0)
                    max_val = sub_field_spec.get('max', 999)
                    
                    tk.Spinbox(fields_frame, textvariable=var,
                              from_=min_val, to=max_val, font=('Segoe UI', 9), width=10).grid(
                        row=field_row, column=1, sticky='w', padx=5, pady=2)
                    
                    var_fields[sub_field_name] = var
                
                else:
                    # String
                    value = var_data.get(sub_field_name, '') if var_data else ''
                    var = tk.StringVar(value=value)
                    
                    tk.Entry(fields_frame, textvariable=var, font=('Segoe UI', 9), width=30).grid(
                        row=field_row, column=1, sticky='ew', padx=5, pady=2)
                    
                    var_fields[sub_field_name] = var
                
                field_row += 1
            
            fields_frame.grid_columnconfigure(1, weight=1)
            
            # Speichere Widget
            widget_data = {
                'frame': var_frame,
                'fields': var_fields
            }
            variable_widgets.append(widget_data)
            
            # Update Count
            count_label.config(text=f"{len(variable_widgets)}/{max_items}")
            
            return widget_data
        
        def delete_variable(frame):
            """Löscht Variable"""
            # Finde Widget
            for i, widget in enumerate(variable_widgets):
                if widget['frame'] == frame:
                    frame.destroy()
                    variable_widgets.pop(i)
                    break
            
            # Update Nummern
            for i, widget in enumerate(variable_widgets):
                # Update Header-Label
                for child in widget['frame'].winfo_children():
                    if isinstance(child, tk.Frame):
                        for label in child.winfo_children():
                            if isinstance(label, tk.Label) and label.cget('text').startswith('Variable #'):
                                label.config(text=f"Variable #{i+1}")
                                break
                        break
            
            # Update Count
            count_label.config(text=f"{len(variable_widgets)}/{max_items}")
        
        def add_variable():
            """Fügt neue Variable hinzu"""
            if len(variable_widgets) >= max_items:
                messagebox.showwarning("Limit", f"Maximal {max_items} Variablen erlaubt!")
                return
            
            create_variable_widget()
        
        # Lade existierende Variablen
        for var_data in existing_vars:
            create_variable_widget(var_data)
        
        # Mindestens min_items
        while len(variable_widgets) < min_items:
            create_variable_widget()
        
        # Add Button
        add_btn = tk.Button(list_container, text="➕ Variable hinzufügen",
                           command=add_variable, font=('Segoe UI', 10),
                           bg='#4CAF50', fg='white', padx=20, pady=5)
        add_btn.pack(pady=5)
        
        # Speichere Referenz für späteren Zugriff
        field_vars[field_name] = variable_widgets
        """
        Öffnet MQTT Topic-Browser
        
        Args:
            topic_var: StringVar die aktualisiert werden soll
        """
        mqtt = self.app.module_manager.get_module('mqtt_integration')
        
        if not mqtt:
            messagebox.showerror("Fehler", "MQTT nicht verfügbar!")
            return
        
        # Dialog
        dialog = tk.Toplevel()
        dialog.title("📡 MQTT Topic-Browser")
        dialog.geometry("800x600")
        
        # Header
        header = tk.Frame(dialog, bg='white')
        header.pack(fill='x', padx=10, pady=10)
        
        tk.Label(header, text="📡 MQTT Topic-Browser",
                font=('Segoe UI', 14, 'bold'), bg='white').pack(side='left')
        
        # Info
        if mqtt.connected:
            tk.Label(header, text=f"✓ Verbunden: {mqtt.config.get('broker', 'N/A')}",
                    font=('Segoe UI', 10), bg='white', fg='green').pack(side='right')
        else:
            tk.Label(header, text="⚠️ Nicht verbunden",
                    font=('Segoe UI', 10), bg='white', fg='red').pack(side='right')
        
        # Suche
        search_frame = tk.Frame(dialog, bg='white')
        search_frame.pack(fill='x', padx=10, pady=(0, 10))
        
        tk.Label(search_frame, text="Filter:", font=('Segoe UI', 10),
                bg='white').pack(side='left', padx=5)
        
        search_var = tk.StringVar()
        search_entry = tk.Entry(search_frame, textvariable=search_var,
                               font=('Segoe UI', 10), width=50)
        search_entry.pack(side='left', padx=5, fill='x', expand=True)
        
        # Liste
        list_frame = tk.Frame(dialog, bg='white')
        list_frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        scrollbar = tk.Scrollbar(list_frame)
        scrollbar.pack(side='right', fill='y')
        
        topic_listbox = tk.Listbox(
            list_frame,
            yscrollcommand=scrollbar.set,
            font=('Consolas', 10),
            bg='white'
        )
        topic_listbox.pack(side='left', fill='both', expand=True)
        scrollbar.config(command=topic_listbox.yview)
        
        def update_list():
            """Aktualisiert Topic-Liste"""
            topic_listbox.delete(0, 'end')
            search = search_var.get().lower()
            
            # Hole alle gecachten Topics
            all_values = mqtt.get_all_values()
            
            if not all_values:
                topic_listbox.insert('end', "ℹ️ Keine Topics empfangen")
                topic_listbox.insert('end', "💡 Tipp: Warte bis MQTT Daten empfängt")
                return
            
            # Filtere Topics
            topics = []
            for topic, value in all_values.items():
                if not search or search in topic.lower():
                    topics.append((topic, value))
            
            # Sortiere
            topics.sort()
            
            # Zeige Topics
            for topic, value in topics[:500]:
                # Formatiere Wert
                if isinstance(value, (int, float)):
                    val_str = f"{value:.2f}" if isinstance(value, float) else str(value)
                else:
                    val_str = str(value)[:20]
                
                display = f"{topic:<50} = {val_str}"
                topic_listbox.insert('end', display)
            
            if not topics:
                topic_listbox.insert('end', "❌ Keine Topics gefunden")
        
        # Live-Update
        search_var.trace('w', lambda *args: update_list())
        
        # Initial update
        update_list()
        
        # Auto-Refresh alle 2 Sekunden
        def auto_refresh():
            if dialog.winfo_exists():
                update_list()
                dialog.after(2000, auto_refresh)
        
        auto_refresh()
        
        # Buttons
        btn_frame = tk.Frame(dialog, bg='white')
        btn_frame.pack(fill='x', padx=10, pady=10)
        
        def select_topic():
            """Wählt Topic aus"""
            selection = topic_listbox.curselection()
            if not selection:
                return
            
            text = topic_listbox.get(selection[0])
            if text.startswith('ℹ️') or text.startswith('💡') or text.startswith('❌'):
                return
            
            # Extrahiere Topic
            topic = text.split('=')[0].strip()
            topic_var.set(topic)
            dialog.destroy()
        
        tk.Button(btn_frame, text="✓ Auswählen", command=select_topic,
                 font=('Segoe UI', 11, 'bold'), bg='#4CAF50', fg='white',
                 padx=30, pady=10).pack(side='left', padx=5)
        
        tk.Button(btn_frame, text="🔄 Aktualisieren", command=update_list,
                 font=('Segoe UI', 11, 'bold'), bg='#2196F3', fg='white',
                 padx=30, pady=10).pack(side='left', padx=5)
        
        tk.Button(btn_frame, text="✕ Abbrechen", command=dialog.destroy,
                 font=('Segoe UI', 11, 'bold'), bg='#757575', fg='white',
                 padx=30, pady=10).pack(side='left', padx=5)
        
        # Doppelklick = Auswählen
        topic_listbox.bind('<Double-1>', lambda e: select_topic())
    
    def open_card_editor(self, card_id: str = None, card_data: dict = None):
        """
        Öffnet Card-Editor mit dynamischen Feldern
        
        Args:
            card_id: Existierende Card-ID oder None für neue Card
            card_data: Existierende Card-Daten oder None
        """
        is_new = card_id is None
        
        if is_new:
            card_id = f"Card_{''.join(random.choices(string.ascii_uppercase + string.digits, k=6))}"
            card_data = {
                'name': 'Neue Card',
                'icon': '💡',
                'tab_id': None,
                'plugin_type': 'light'
            }
        
        # Dialog
        dialog = tk.Toplevel()
        dialog.title("Card Editor" if not is_new else "Neue Card")
        dialog.geometry("700x800")
        
        # Scrollable Frame
        canvas = tk.Canvas(dialog, bg='white')
        scrollbar = tk.Scrollbar(dialog, orient='vertical', command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg='white')
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor='nw')
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')
        
        # ═══════════════════════════════════════
        # STANDARD-FELDER
        # ═══════════════════════════════════════
        row = 0
        
        # Card-ID
        tk.Label(scrollable_frame, text="Card-ID:", font=('Segoe UI', 10, 'bold'),
                bg='white').grid(row=row, column=0, sticky='w', padx=10, pady=5)
        tk.Label(scrollable_frame, text=card_id, font=('Segoe UI', 10),
                bg='white', fg='gray').grid(row=row, column=1, sticky='w', padx=10, pady=5)
        row += 1
        
        # Name
        tk.Label(scrollable_frame, text="Name:", font=('Segoe UI', 10, 'bold'),
                bg='white').grid(row=row, column=0, sticky='w', padx=10, pady=5)
        name_var = tk.StringVar(value=card_data.get('name', ''))
        tk.Entry(scrollable_frame, textvariable=name_var, width=50,
                font=('Segoe UI', 10)).grid(row=row, column=1, columnspan=2, sticky='ew', padx=10, pady=5)
        row += 1
        
        # Icon
        tk.Label(scrollable_frame, text="Icon:", font=('Segoe UI', 10, 'bold'),
                bg='white').grid(row=row, column=0, sticky='w', padx=10, pady=5)
        
        icon_frame = tk.Frame(scrollable_frame, bg='white')
        icon_frame.grid(row=row, column=1, columnspan=2, sticky='ew', padx=10, pady=5)
        
        icon_var = tk.StringVar(value=card_data.get('icon', '💡'))
        
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
        
        # Tab (Dropdown)
        tk.Label(scrollable_frame, text="Tab:", font=('Segoe UI', 10, 'bold'),
                bg='white').grid(row=row, column=0, sticky='w', padx=10, pady=5)
        
        # Hole Tabs vom TabManager
        tab_manager = self.app.module_manager.get_module('tab_manager')
        tab_choices = []
        tab_id_map = {}
        
        if tab_manager:
            for tab_data in tab_manager.get_all_tabs(sorted_by_order=True):
                tid = tab_data['id']
                icon = tab_data.get('icon', '')
                name = tab_data['name']
                display = f"{icon} {name}" if icon else name
                
                tab_choices.append(display)
                tab_id_map[display] = tid
        
        # Aktueller Tab
        current_tab_id = card_data.get('tab_id')
        current_display = ''
        
        if current_tab_id and tab_manager:
            tab_data = tab_manager.get_tab_by_id(current_tab_id)
            if tab_data:
                icon = tab_data.get('icon', '')
                name = tab_data['name']
                current_display = f"{icon} {name}" if icon else name
        
        tab_var = tk.StringVar(value=current_display)
        tab_dropdown = ttk.Combobox(
            scrollable_frame,
            textvariable=tab_var,
            values=tab_choices,
            state='readonly',
            font=('Segoe UI', 10),
            width=47
        )
        tab_dropdown.grid(row=row, column=1, columnspan=2, sticky='ew', padx=10, pady=5)
        row += 1
        
        # Plugin-Typ
        tk.Label(scrollable_frame, text="Plugin-Typ:", font=('Segoe UI', 10, 'bold'),
                bg='white').grid(row=row, column=0, sticky='w', padx=10, pady=5)
        
        plugin_var = tk.StringVar(value=card_data.get('plugin_type', 'light'))
        
        plugin_frame = tk.Frame(scrollable_frame, bg='white')
        plugin_frame.grid(row=row, column=1, columnspan=2, sticky='ew', padx=10, pady=5)
        
        plugins = ['light', 'temperature', 'gauge', 'weather', 'solarassistant']
        for i, plugin in enumerate(plugins):
            tk.Radiobutton(
                plugin_frame,
                text=plugin.capitalize(),
                variable=plugin_var,
                value=plugin,
                bg='white',
                font=('Segoe UI', 9)
            ).grid(row=0, column=i, padx=5)
        row += 1
        
        # Separator
        ttk.Separator(scrollable_frame, orient='horizontal').grid(
            row=row, column=0, columnspan=3, sticky='ew', padx=10, pady=15)
        row += 1
        
        # ═══════════════════════════════════════
        # DYNAMISCHE PLUGIN-FELDER
        # ═══════════════════════════════════════
        
        tk.Label(scrollable_frame, text="⚙️ Plugin-Konfiguration",
                font=('Segoe UI', 12, 'bold'), bg='white').grid(
            row=row, column=0, columnspan=3, sticky='w', padx=10, pady=5)
        row += 1
        
        # Container für dynamische Felder
        dynamic_fields_frame = tk.Frame(scrollable_frame, bg='white')
        dynamic_fields_frame.grid(row=row, column=0, columnspan=3, sticky='ew', padx=10)
        row += 1
        
        # Vars für dynamische Felder
        field_vars = {}
        
        def rebuild_dynamic_fields():
            """Baut Plugin-Felder neu (wenn Plugin-Typ ändert)"""
            # Clear
            for widget in dynamic_fields_frame.winfo_children():
                widget.destroy()
            
            field_vars.clear()
            
            # Hole Plugin
            plugin_type = plugin_var.get()
            plugin = self.app.module_manager.get_module(plugin_type)
            
            if not plugin or not hasattr(plugin, 'get_schema'):
                tk.Label(dynamic_fields_frame, text="⚠️ Plugin hat kein Schema",
                        font=('Segoe UI', 10), bg='white', fg='gray').pack()
                return
            
            # Hole Schema
            schema = plugin.get_schema()
            
            field_row = 0
            for field_name, field_spec in schema.items():
                field_type = field_spec.get('type')
                label = field_spec.get('label', field_name)
                description = field_spec.get('description', '')
                required = field_spec.get('required', False)
                
                # Label
                label_text = f"{label}{'*' if required else ''}:"
                tk.Label(dynamic_fields_frame, text=label_text,
                        font=('Segoe UI', 10, 'bold'), bg='white').grid(
                    row=field_row, column=0, sticky='w', pady=5)
                
                # Field
                if field_type == 'plc_variable':
                    # PLC-Variable mit Symbol-Browser
                    var = tk.StringVar(value=card_data.get(field_name, field_spec.get('placeholder', '')))
                    field_vars[field_name] = var
                    
                    entry_frame = tk.Frame(dynamic_fields_frame, bg='white')
                    entry_frame.grid(row=field_row, column=1, sticky='ew', pady=5)
                    
                    entry = tk.Entry(entry_frame, textvariable=var,
                                    font=('Segoe UI', 10), width=35)
                    entry.pack(side='left', padx=(0, 5))
                    
                    # ⭐ SYMBOL-BROWSER BUTTON!
                    plc_type = field_spec.get('plc_type')
                    tk.Button(entry_frame, text="🔍",
                             command=lambda v=var, t=plc_type: self.open_symbol_browser(v, t),
                             font=('Segoe UI', 10),
                             padx=10).pack(side='left')
                
                elif field_type == 'choice':
                    # Choice (Radio oder Dropdown)
                    var = tk.StringVar(value=card_data.get(field_name, field_spec.get('default', '')))
                    field_vars[field_name] = var
                    
                    choices = field_spec.get('choices', [])
                    
                    choice_frame = tk.Frame(dynamic_fields_frame, bg='white')
                    choice_frame.grid(row=field_row, column=1, sticky='ew', pady=5)
                    
                    for i, choice in enumerate(choices):
                        if isinstance(choice, dict):
                            value = choice['value']
                            label = choice['label']
                        else:
                            value = label = choice
                        
                        tk.Radiobutton(
                            choice_frame,
                            text=label,
                            variable=var,
                            value=value,
                            bg='white',
                            font=('Segoe UI', 9)
                        ).grid(row=0, column=i, padx=5)
                
                elif field_type == 'integer':
                    # Integer (Spinbox)
                    var = tk.IntVar(value=card_data.get(field_name, field_spec.get('default', 0)))
                    field_vars[field_name] = var
                    
                    min_val = field_spec.get('min', 0)
                    max_val = field_spec.get('max', 9999)
                    step = field_spec.get('step', 1)
                    
                    tk.Spinbox(dynamic_fields_frame, textvariable=var,
                              from_=min_val, to=max_val, increment=step,
                              font=('Segoe UI', 10), width=20).grid(
                        row=field_row, column=1, sticky='w', pady=5)
                
                elif field_type == 'float':
                    # Float (Entry mit Validation)
                    var = tk.DoubleVar(value=card_data.get(field_name, field_spec.get('default', 0.0)))
                    field_vars[field_name] = var
                    
                    tk.Entry(dynamic_fields_frame, textvariable=var,
                            font=('Segoe UI', 10), width=20).grid(
                        row=field_row, column=1, sticky='w', pady=5)
                
                elif field_type == 'boolean':
                    # Boolean (Checkbutton)
                    var = tk.BooleanVar(value=card_data.get(field_name, field_spec.get('default', False)))
                    field_vars[field_name] = var
                    
                    tk.Checkbutton(dynamic_fields_frame, variable=var,
                                  bg='white', font=('Segoe UI', 10)).grid(
                        row=field_row, column=1, sticky='w', pady=5)
                
                elif field_type == 'password':
                    # Password (Entry mit show='*')
                    var = tk.StringVar(value=card_data.get(field_name, ''))
                    field_vars[field_name] = var
                    
                    tk.Entry(dynamic_fields_frame, textvariable=var, show='*',
                            font=('Segoe UI', 10), width=40).grid(
                        row=field_row, column=1, sticky='ew', pady=5)
                
                elif field_type == 'mqtt_topic':
                    # MQTT Topic mit Browser
                    var = tk.StringVar(value=card_data.get(field_name, field_spec.get('placeholder', '')))
                    field_vars[field_name] = var
                    
                    entry_frame = tk.Frame(dynamic_fields_frame, bg='white')
                    entry_frame.grid(row=field_row, column=1, sticky='ew', pady=5)
                    
                    entry = tk.Entry(entry_frame, textvariable=var,
                                    font=('Segoe UI', 10), width=35)
                    entry.pack(side='left', padx=(0, 5))
                    
                    # ⭐ MQTT TOPIC-BROWSER BUTTON!
                    tk.Button(entry_frame, text="📡",
                             command=lambda v=var: self.open_mqtt_topic_browser(v),
                             font=('Segoe UI', 10),
                             padx=10).pack(side='left')
                
                elif field_type == 'mqtt_variable_list':
                    # ⭐ DYNAMISCHE VARIABLEN-LISTE!
                    self._create_mqtt_variable_list(
                        dynamic_fields_frame,
                        field_row,
                        field_name,
                        field_spec,
                        card_data,
                        field_vars
                    )
                    field_row += 10  # Reserve Platz
                
                else:
                    # String (Entry)
                    var = tk.StringVar(value=card_data.get(field_name, ''))
                    field_vars[field_name] = var
                    
                    tk.Entry(dynamic_fields_frame, textvariable=var,
                            font=('Segoe UI', 10), width=40).grid(
                        row=field_row, column=1, sticky='ew', pady=5)
                
                field_row += 1
                
                # Description
                if description:
                    tk.Label(dynamic_fields_frame, text=f"💡 {description}",
                            font=('Segoe UI', 8), bg='white', fg='gray').grid(
                        row=field_row, column=1, sticky='w', pady=(0, 5))
                    field_row += 1
        
        # Initial build
        rebuild_dynamic_fields()
        
        # Rebuild wenn Plugin ändert
        plugin_var.trace('w', lambda *args: rebuild_dynamic_fields())
        
        # ═══════════════════════════════════════
        # SAVE BUTTON
        # ═══════════════════════════════════════
        
        btn_frame = tk.Frame(scrollable_frame, bg='white')
        btn_frame.grid(row=row, column=0, columnspan=3, pady=20)
        
        def save_card():
            """Speichert Card"""
            # Hole Tab-ID
            selected_display = tab_var.get()
            selected_tab_id = tab_id_map.get(selected_display)
            
            if not selected_tab_id:
                messagebox.showerror("Fehler", "Bitte Tab auswählen!")
                return
            
            # Update Card-Daten
            card_data['name'] = name_var.get()
            card_data['icon'] = icon_var.get()
            card_data['tab_id'] = selected_tab_id
            card_data['plugin_type'] = plugin_var.get()
            
            # Dynamische Felder
            for field_name, var in field_vars.items():
                if isinstance(var, list):
                    # ⭐ MQTT Variable-Liste!
                    variables = []
                    for widget_data in var:
                        var_dict = {}
                        for sub_field_name, sub_var in widget_data['fields'].items():
                            var_dict[sub_field_name] = sub_var.get()
                        variables.append(var_dict)
                    card_data[field_name] = variables
                else:
                    # Normale Felder
                    card_data[field_name] = var.get()
            
            # Speichern
            custom_lights = self.config.get_custom_lights()
            custom_lights[card_id] = card_data
            self.config.save_config()
            
            dialog.destroy()
            self.refresh_card_list()
            self.update_stats()
            
            messagebox.showinfo("Erfolg", 
                "✓ Card gespeichert!\n\n"
                "Starte App neu um Card zu sehen.")
        
        tk.Button(btn_frame, text="💾 Speichern", command=save_card,
                 font=('Segoe UI', 11, 'bold'), bg='#4CAF50', fg='white',
                 padx=30, pady=10).pack(side='left', padx=5)
        
        tk.Button(btn_frame, text="✕ Abbrechen", command=dialog.destroy,
                 font=('Segoe UI', 11, 'bold'), bg='#757575', fg='white',
                 padx=30, pady=10).pack(side='left', padx=5)
    
    def shutdown(self):
        """Cleanup"""
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
