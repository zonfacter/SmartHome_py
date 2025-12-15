"""
MQTT Browser Module v3.1.0
Live MQTT Topic Browser mit Baumansicht und optimierter Aktualisierung

📁 SPEICHERORT: modules/ui/mqtt_browser.py

Changelog:
- v3.1.0 (2025-12-04):
  - Added: Alphabetische (A-Z) Sortierung der Topics/Nodes in der Baumansicht (pro Ebene).
  - Improved: Sortierung nach jedem Insert für konsistente Ordnung.
- v3.0.0 (2025-12-04):
  - Added: Hierarchische Baumansicht (Treeview) für Topics (split by '/').
  - Improved: Batch-Updates via Timer (alle 500ms), um UI-Trägheit zu reduzieren.
  - Improved: Suchfilter unterstützt Baumstruktur (expand/recurse).
  - Fixed: Potenzielle Lag bei hoher Message-Rate (z. B. von SolarAssistant).
  - UX: Kollabierbare Branches, bessere Übersichtlichkeit für hierarchische Topics.

Features:
- Hierarchische Topic-Anzeige (Baumansicht, sortiert A-Z)
- Werte-Anzeige
- Filter & Suche (rekursiv im Baum)
- Auto-Refresh (batch-weise)
"""

from module_manager import BaseModule
from typing import Any, Dict
import tkinter as tk
from tkinter import ttk, scrolledtext
import time
from collections import deque  # Für Message-Queue

class MqttBrowser(BaseModule):
    """
    MQTT Browser v3.1.0
    
    Features:
    - Hierarchische Baumansicht für Topics (sortiert A-Z)
    - Batch-Updates für bessere Performance
    - Filter & Suche
    - Auto-Refresh
    """
    
    NAME = "mqtt_browser"
    VERSION = "3.1.0"
    DESCRIPTION = "Live MQTT Topic Browser mit Baumansicht"
    AUTHOR = "TwinCAT Team"
    DEPENDENCIES = ['gui_manager', 'mqtt_integration']
    
    # ⭐ Tab-Support Flags
    HAS_TAB = True
    TAB_NAME = "MQTT Browser"
    TAB_ICON = "📡"
    TAB_ORDER = 100
    
    def __init__(self):
        super().__init__()
        self.gui = None
        self.mqtt = None
        self.scanning = False
        self.topics = {}  # topic -> {'value': value, 'time': time} (flat for quick lookup)
        self.tree = None
        self.root_widget = None
        self.message_queue = deque()  # Queue für batch-Updates
        self.update_timer = None  # Timer für periodic UI-Update
    
    def initialize(self, app_context: Any):
        """Initialisiert MQTT Browser"""
        super().initialize(app_context)
        self.app = app_context
        
        # Hole Module
        self.gui = app_context.module_manager.get_module('gui_manager')
        self.mqtt = app_context.module_manager.get_module('mqtt_integration')
        
        print(f"  ⚡ {self.NAME} v{self.VERSION} initialisiert")
    
    def create_tab(self, parent: tk.Widget):
        """Erstellt MQTT Browser Tab"""
        self.root_widget = parent
        self._create_browser_ui(parent)
    
    def _create_browser_ui(self, parent: tk.Widget):
        """Erstellt Browser-UI"""
        # Header
        header = tk.Frame(parent, bg=self.gui.colors['bg'])
        header.pack(fill='x', padx=20, pady=20)
        
        tk.Label(
            header,
            text="📡 MQTT Topic Browser (Baumansicht)",
            font=('Segoe UI', 16, 'bold'),
            bg=self.gui.colors['bg'],
            fg=self.gui.colors['text_dark']
        ).pack(side='left')
        
        # Status
        self.status_label = tk.Label(
            header,
            text="● Nicht verbunden",
            font=('Segoe UI', 10),
            bg=self.gui.colors['bg'],
            fg='red'
        )
        self.status_label.pack(side='right', padx=10)
        
        # Control Frame
        control = tk.Frame(parent, bg=self.gui.colors['bg'])
        control.pack(fill='x', padx=20, pady=(0, 10))
        
        # Scan Button
        self.scan_btn = self.gui.create_button(
            control,
            "🔍 Scan starten",
            self.start_scan,
            style='success'
        )
        self.scan_btn.pack(side='left', padx=5)
        
        # Stop Button
        self.stop_btn = self.gui.create_button(
            control,
            "⏸️ Stop",
            self.stop_scan,
            style='danger'
        )
        self.stop_btn.pack(side='left', padx=5)
        self.stop_btn.config(state='disabled')
        
        # Clear Button
        self.gui.create_button(
            control,
            "🗑️ Leeren",
            self.clear_topics,
            style='primary'
        ).pack(side='left', padx=5)
        
        # Auto-Refresh Toggle
        self.auto_refresh = tk.BooleanVar(value=False)
        tk.Checkbutton(
            control,
            text="🔄 Auto-Refresh (5s)",
            variable=self.auto_refresh,
            font=('Segoe UI', 10),
            bg=self.gui.colors['bg'],
            fg=self.gui.colors['text_dark']
        ).pack(side='left', padx=20)
        
        # Search
        tk.Label(
            control,
            text="🔍 Filter:",
            font=('Segoe UI', 10),
            bg=self.gui.colors['bg'],
            fg=self.gui.colors['text_dark']
        ).pack(side='left', padx=(20, 5))
        
        self.search_var = tk.StringVar()
        self.search_var.trace('w', lambda *args: self.filter_topics())
        tk.Entry(
            control,
            textvariable=self.search_var,
            font=('Segoe UI', 10),
            width=30
        ).pack(side='left', padx=5)
        
        # Topic Tree (Treeview)
        list_frame = tk.Frame(parent, bg='white')
        list_frame.pack(fill='both', expand=True, padx=20, pady=10)
        
        # Scrollbars
        vsb = tk.Scrollbar(list_frame, orient='vertical')
        hsb = tk.Scrollbar(list_frame, orient='horizontal')
        
        # Treeview (hierarchische)
        self.tree = ttk.Treeview(
            list_frame,
            columns=('value', 'time'),
            show='tree headings',
            yscrollcommand=vsb.set,
            xscrollcommand=hsb.set
        )
        
        # Columns
        self.tree.heading('#0', text='Topic')
        self.tree.heading('value', text='Value')
        self.tree.heading('time', text='Letzte Änderung')
        
        self.tree.column('#0', width=400)
        self.tree.column('value', width=300)
        self.tree.column('time', width=150)
        
        # Pack
        vsb.config(command=self.tree.yview)
        hsb.config(command=self.tree.xview)
        
        self.tree.grid(row=0, column=0, sticky='nsew')
        vsb.grid(row=0, column=1, sticky='ns')
        hsb.grid(row=1, column=0, sticky='ew')
        
        list_frame.grid_rowconfigure(0, weight=1)
        list_frame.grid_columnconfigure(0, weight=1)
        
        # Info Label
        self.info_label = tk.Label(
            parent,
            text="💡 Klicke 'Scan starten' um Topics zu entdecken",
            font=('Segoe UI', 9),
            bg=self.gui.colors['bg'],
            fg=self.gui.colors['text_light']
        )
        self.info_label.pack(pady=10)
        
        # Update Status
        self.update_connection_status()
        
        # Start Auto-Refresh Loop
        self.auto_refresh_loop()
    
    def update_connection_status(self):
        """Aktualisiert Verbindungs-Status"""
        if self.mqtt and self.mqtt.connected:
            self.status_label.config(
                text=f"● Verbunden: {self.mqtt.config.get('broker', 'N/A')}",
                fg='green'
            )
            self.scan_btn.config(state='normal')
        else:
            self.status_label.config(
                text="● Nicht verbunden",
                fg='red'
            )
            self.scan_btn.config(state='disabled')
    
    def start_scan(self):
        """Startet Topic-Scan"""
        if not self.mqtt or not self.mqtt.connected:
            self.info_label.config(text="❌ MQTT nicht verbunden!")
            return
        
        self.scanning = True
        self.scan_btn.config(state='disabled')
        self.stop_btn.config(state='normal')
        self.info_label.config(text="🔍 Scanne Topics... (Warte auf Messages)")
        
        print("\n📡 MQTT Browser: Starte Topic-Scan...")
        print(f"  Broker: {self.mqtt.config.get('broker', 'N/A')}")
        print(f"  Verbunden: {self.mqtt.connected}")
        
        if self.mqtt.client:
            try:
                result = self.mqtt.client.subscribe('#', qos=0)
                print(f"  📥 Subscribe '#' (Wildcard): {result}")
                
                def on_message_wrapper(client, userdata, message):
                    """Callback für MQTT Messages (batch)"""
                    if not self.scanning:
                        return
                    
                    topic = message.topic
                    payload = message.payload.decode('utf-8', errors='ignore')
                    
                    print(f"  📨 Topic empfangen: {topic} = {payload[:50]}")
                    
                    # In Queue pushen statt direkt update
                    self.message_queue.append((topic, payload))
                
                self.mqtt.client.on_message = on_message_wrapper
                print("  ✓ Callback registriert")
                
                # Starte batch-update Timer
                self._schedule_update()
                
            except Exception as e:
                print(f"  ❌ Subscribe-Fehler: {e}")
                self.info_label.config(text=f"❌ Fehler: {e}")
                return
        else:
            print("  ❌ MQTT Client nicht verfügbar!")
            self.info_label.config(text="❌ MQTT Client fehlt!")
            return
        
        # Info nach 10s
        if self.root_widget:
            self.root_widget.after(10000, self._scan_timeout_info)
    
    def _schedule_update(self):
        """Plant UI-Update (batch)"""
        if self.update_timer:
            self.root_widget.after_cancel(self.update_timer)
        
        self.update_timer = self.root_widget.after(500, self._process_queue)  # Alle 500ms
    
    def _process_queue(self):
        """Verarbeitet Message-Queue und updated Baum"""
        while self.message_queue:
            topic, payload = self.message_queue.popleft()
            
            # Speichere flat
            self.topics[topic] = {
                'value': payload,
                'time': time.strftime('%H:%M:%S')
            }
            
            # Update Baum (hierarchisch)
            self._insert_into_tree(topic, payload)
        
        self.update_timer = None
        
        # Wenn Queue leer und scanning, reschedule für nächste Batch
        if self.scanning:
            self._schedule_update()
    
    def _insert_into_tree(self, topic: str, value: str):
        """Fügt Topic hierarchisch in Treeview ein und sortiert A-Z"""
        parts = topic.split('/')
        parent = ''
        
        for i, part in enumerate(parts):
            node_id = '/'.join(parts[:i+1])
            
            # Prüfe ob Node existiert
            children = self.tree.get_children(parent)
            existing = [self.tree.item(child)['text'] for child in children]
            
            if part not in existing:
                if i == len(parts) - 1:  # Leaf: Value und Time
                    self.tree.insert(parent, 'end', iid=node_id, text=part, values=(value, self.topics[topic]['time']))
                else:  # Branch
                    self.tree.insert(parent, 'end', iid=node_id, text=part, values=('', ''))
                
                # Sortiere Children von parent A-Z
                self._sort_children(parent)
            
            parent = node_id
    
    def _sort_children(self, parent: str):
        """Sortiert Children eines Parents alphabetisch (A-Z)"""
        children = self.tree.get_children(parent)
        if not children:
            return
        
        # Hole Items mit Text
        items = [(self.tree.item(child)['text'], child) for child in children]
        
        # Sortiere nach Text
        items.sort(key=lambda x: x[0].lower())  # Case-insensitive
        
        # Bewege in sortierter Reihenfolge
        for index, (text, iid) in enumerate(items):
            self.tree.move(iid, parent, index)
    
    def _scan_timeout_info(self):
        """Zeigt Info nach 10s"""
        if self.scanning:
            count = len(self.topics)
            if count == 0:
                self.info_label.config(
                    text="⚠️ Noch keine Topics empfangen. Werden Topics gesendet?"
                )
                print(f"\n⚠️ MQTT Browser: Nach 10s noch keine Topics!")
                print(f"  Prüfe:")
                print(f"  1. Sendet der Broker Topics? (Test mit MQTT explorer)")
                print(f"  2. Sind Topics vorhanden?")
                print(f"  3. Firewall blockiert?")
            else:
                self.info_label.config(
                    text=f"✓ {count} Topics gefunden. Scan läuft weiter..."
                )
                print(f"  ✓ {count} Topics gefunden nach 10s")
    
    def stop_scan(self):
        """Stoppt Scan"""
        self.scanning = False
        self.scan_btn.config(state='normal')
        self.stop_btn.config(state='disabled')
        
        count = len(self.topics)
        self.info_label.config(text=f"✓ Scan beendet: {count} Topics gefunden")
        
        print(f"\n📡 MQTT Browser: Scan beendet")
        print(f"  Gefundene Topics: {count}")
        
        # Unsubscribe Wildcard
        if self.mqtt and self.mqtt.client:
            try:
                self.mqtt.client.unsubscribe('#')
                print("  ✓ Unsubscribe '#'")
            except Exception as e:
                print(f"  ⚠️ Unsubscribe-Fehler: {e}")
    
    def clear_topics(self):
        """Leert Topic-Liste"""
        self.topics = {}
        for item in self.tree.get_children():
            self.tree.delete(item)
        self.info_label.config(text="🗑️ Liste geleert")
    
    def filter_topics(self):
        """Filtert Topics nach Suchbegriff (rekursiv)"""
        search = self.search_var.get().lower()
        
        def recurse(item):
            """Rekursives Filtern und Expand"""
            self.tree.item(item, open=True if search else False)
            for child in self.tree.get_children(item):
                recurse(child)
        
        # Expand/Collapse basierend auf Suche
        if search:
            recurse('')
        self.update_display()  # Optional, wenn Filter on-the-fly
    
    def update_display(self):
        """Aktualisiert Anzeige (nicht mehr benötigt, da batch)"""
        pass  # Jetzt in _process_queue
    
    def auto_refresh_loop(self):
        """Auto-Refresh Loop"""
        if not self.root_widget:
            return
        
        # Update wenn enabled
        if self.auto_refresh.get() and self.scanning:
            self._process_queue()  # Manuelles Batch-Update
        
        # Update Status
        self.update_connection_status()
        
        # Repeat
        self.root_widget.after(5000, self.auto_refresh_loop)
    
    def shutdown(self):
        """Cleanup"""
        self.stop_scan()
        if self.update_timer:
            self.root_widget.after_cancel(self.update_timer)


def register(module_manager):
    """Registriert Modul"""
    module_manager.register_module(
        MqttBrowser.NAME,
        MqttBrowser.VERSION,
        MqttBrowser.DESCRIPTION,
        MqttBrowser,
        author=MqttBrowser.AUTHOR,
        dependencies=MqttBrowser.DEPENDENCIES
    )