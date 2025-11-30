"""
TwinCAT Smart Home Control v2.0.4
Vollständig modulare Haussteuerung mit ALLEN Features

📁 SPEICHERORT: Haussteuerung_v2.py (Root-Verzeichnis)

⚠️ WICHTIG: Diese Datei muss im Root-Verzeichnis liegen!
          Der modules/ Ordner muss im gleichen Verzeichnis sein!

Ordner-Struktur:
    Haussteuerung_v2.py          <- Diese Datei
    module_manager.py
    config.json
    modules/
        core/
        ui/
        integrations/
        plugins/

Features:
- Modulares System (17 Module)
- Status-Leiste (PLC, Uhrzeit, Sonne, Mond)
- Card-Manager (Erstellen, Bearbeiten, Löschen)
- Symbol-Browser
- Drag & Drop (Grid-Snapping, Multi-Select)
- Live-Updates (Smart-Update)
- Tab-Manager
- Theme-System (3 Themes)
"""

import os
import sys
import tkinter as tk
from tkinter import messagebox
import pyads  # Für PLC-Port Konstanten

# Module System
from module_manager import ModuleManager


class SmartHomeApp:
    """
    TwinCAT Smart Home v2.0
    
    Vollständig modulare Architektur
    """
    
    VERSION = "2.2.6"
    NAME = "TwinCAT Smart Home"
    BUILD_DATE = "2025-11-30"
    
    def __init__(self):
        self.print_banner()
        
        # Module Manager
        self.module_manager = ModuleManager(modules_dir='modules')
        
        # Module laden
        self.load_all_modules()
        
        # Status
        print(self.module_manager.get_status_summary())
        
        # Module initialisieren
        self.initialize_modules()
        
        # GUI aufbauen
        self.build_gui()
        
        # Update-Loop starten
        self.start_update_loop()
    
    def print_banner(self):
        """Startup-Banner"""
        print("=" * 70)
        print(f"  {self.NAME} v{self.VERSION}")
        print(f"  Build: {self.BUILD_DATE}")
        print(f"  Vollständig Modular")
        print("=" * 70)
    
    def load_all_modules(self):
        """Lädt alle Module"""
        print("\n📦 Module Manager v1.0.0 gestartet")
        
        # Core
        print("\n📦 Lade Core-Module...")
        self.module_manager.load_module_from_file('modules/core/plc_communication.py')
        self.module_manager.load_module_from_file('modules/core/config_manager.py')
        self.module_manager.load_module_from_file('modules/core/symbol_manager.py')
        self.module_manager.load_module_from_file('modules/core/update_loop.py')
        
        # UI
        print("\n🎨 Lade UI-Module...")
        self.module_manager.load_module_from_file('modules/ui/gui_manager.py')
        self.module_manager.load_module_from_file('modules/ui/status_bar.py')
        self.module_manager.load_module_from_file('modules/ui/card_manager.py')
        self.module_manager.load_module_from_file('modules/ui/card_renderer.py')
        self.module_manager.load_module_from_file('modules/ui/search_filter.py')
        self.module_manager.load_module_from_file('modules/ui/context_menu.py')
        self.module_manager.load_module_from_file('modules/ui/drag_drop.py')
        self.module_manager.load_module_from_file('modules/ui/tab_manager.py')
        
        # Integrations
        print("\n🔌 Lade Integration-Module...")
        if os.path.exists('modules/integrations/modbus_module.py'):
            self.module_manager.load_module_from_file('modules/integrations/modbus_module.py')
        if os.path.exists('modules/integrations/mqtt_module.py'):
            self.module_manager.load_module_from_file('modules/integrations/mqtt_module.py')
        if os.path.exists('modules/integrations/rtsp_module.py'):
            self.module_manager.load_module_from_file('modules/integrations/rtsp_module.py')
        
        # Plugins
        print("\n🧩 Lade Plugin-Module...")
        plugin_dir = 'modules/plugins'
        if os.path.exists(plugin_dir):
            for filename in os.listdir(plugin_dir):
                if filename.endswith('_plugin.py'):
                    self.module_manager.load_module_from_file(
                        os.path.join(plugin_dir, filename)
                    )
    
    def initialize_modules(self):
        """Initialisiert alle Module"""
        print("\n⚙️  Initialisiere Module...")
        
        # Hole wichtige Module
        self.plc = self.module_manager.get_module('plc_communication')
        self.gui = self.module_manager.get_module('gui_manager')
        self.config = self.module_manager.get_module('config_manager')
        self.status_bar = self.module_manager.get_module('status_bar')
        self.card_manager = self.module_manager.get_module('card_manager')
        self.cards = self.module_manager.get_module('card_renderer')
        self.update_loop = self.module_manager.get_module('update_loop')
        self.tab_manager = self.module_manager.get_module('tab_manager')
        
        # Initialisiere ALLE Module
        for name, info in self.module_manager.get_all_modules().items():
            if info.module_object and hasattr(info.module_object, 'initialize'):
                try:
                    info.module_object.initialize(self)
                except Exception as e:
                    print(f"  ✗ Fehler bei {name}: {e}")
        
        # WICHTIG: PLC VERBINDEN!
        if self.plc:
            # Konfiguration aus config.json laden (falls vorhanden)
            ams_net_id = '192.168.2.162.1.1'  # Default
            port = pyads.PORT_TC2PLC1  # Default TC2 (Port 801)!
            
            if self.config:
                plc_config = self.config.get_config_value('plc', None)
                if plc_config and isinstance(plc_config, dict):
                    ams_net_id = plc_config.get('ams_net_id', ams_net_id)
                    port = plc_config.get('port', port)
                    print(f"  ℹ️  PLC-Config aus config.json geladen")
                else:
                    print(f"  ℹ️  Nutze Default PLC-Config (TC2)")
            
            # PLC konfigurieren
            self.plc.configure(ams_net_id, port)
            print(f"  ℹ️  PLC-Config: {ams_net_id}:{port} (TC2)")
            
            # Verbindung herstellen
            success = self.plc.connect()
            
            if not success:
                print("  ⚠️  WARNUNG: PLC-Verbindung fehlgeschlagen!")
                print("  💡 Prüfe: TwinCAT 2 läuft? AMS Net ID korrekt?")
                print(f"  💡 Versuche: {ams_net_id}:{port} (TC2 = Port 801)")
            
            # PLC-Referenz an Plugins übergeben
            self._inject_plc_to_plugins()
        
        # MQTT verbinden (falls konfiguriert)
        self.mqtt = self.module_manager.get_module('mqtt_integration')
        if self.mqtt:
            # Lade MQTT-Config
            if self.config:
                mqtt_config = self.config.get_config_value('mqtt', None)
                if mqtt_config and isinstance(mqtt_config, dict):
                    broker = mqtt_config.get('broker', 'localhost')
                    port = mqtt_config.get('port', 1883)
                    username = mqtt_config.get('username', None)
                    password = mqtt_config.get('password', None)
                    
                    # Konfiguriere und verbinde
                    self.mqtt.configure(broker, port, username, password)
                    success = self.mqtt.connect()
                    
                    if success:
                        print(f"  ✓ MQTT wird verbunden: {broker}:{port}")
                        
                        # Abonniere Topics aus allen SolarAssistant Cards
                        self._subscribe_mqtt_topics()
                    else:
                        print(f"  ⚠️  MQTT-Verbindung fehlgeschlagen!")
                else:
                    print(f"  ℹ️  Keine MQTT-Config gefunden")
        
        # Finalisiere
        self.finalize_initialization()
    
    def _inject_plc_to_plugins(self):
        """Gibt PLC-Referenz an alle Plugins"""
        if not self.plc:
            return
        
        # Hole alle Plugin-Module
        for name, info in self.module_manager.get_all_modules().items():
            if '_plugin' in name or name in ['light', 'temperature', 'gauge', 'weather']:
                plugin = info.module_object
                if plugin and hasattr(plugin, 'plc'):
                    plugin.plc = self.plc
                    print(f"  ✓ PLC-Referenz an {name} übergeben")
    
    def _subscribe_mqtt_topics(self):
        """Abonniert MQTT-Topics aus allen SolarAssistant Cards"""
        if not self.mqtt or not self.config:
            return
        
        # Hole alle Cards
        custom_lights = self.config.get_custom_lights()
        topics_to_subscribe = set()
        
        # Sammle alle Topics
        for card_id, card_data in custom_lights.items():
            if card_data.get('plugin_type') == 'solarassistant':
                topics = card_data.get('topics', {})
                for topic_name, topic_path in topics.items():
                    if topic_path:  # Nur wenn Topic definiert
                        topics_to_subscribe.add(topic_path)
        
        # Abonniere alle Topics
        for topic in topics_to_subscribe:
            self.mqtt.subscribe(topic)
            print(f"    📥 MQTT Subscribe: {topic}")
    
    def finalize_initialization(self):
        """Finalisiert Initialisierung"""
        # GUI-Themes
        if self.gui:
            self.gui.define_themes()
    
    def build_gui(self):
        """Baut GUI auf"""
        if not self.gui:
            print("❌ GUI-Manager nicht geladen!")
            return
        
        print("\n🏗️  Baue GUI...")
        
        # Hauptfenster
        self.root = self.gui.create_window(f"{self.NAME} v{self.VERSION}")
        
        # Haupt-Container
        main_container = tk.Frame(self.root, bg=self.gui.colors['bg'])
        main_container.pack(fill='both', expand=True)
        
        # Status-Leiste oben
        if self.status_bar:
            status = self.status_bar.create_status_bar(main_container)
            status.pack(side='top', fill='x')
        
        # Content-Container
        content_container = tk.Frame(main_container, bg=self.gui.colors['bg'])
        content_container.pack(fill='both', expand=True, padx=20, pady=20)
        
        # Notebook für Tabs
        self.notebook = self.gui.create_notebook(content_container)
        self.notebook.pack(fill='both', expand=True)
        
        # Tab-Manager setzen
        if self.tab_manager:
            self.tab_manager.set_notebook(self.notebook)
        
        # Tabs erstellen
        self.create_tabs()
        
        # Control Panel unten
        self.create_control_panel(content_container)
        
        # Window-Close
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
    
    def create_tabs(self):
        """Erstellt alle Tabs"""
        # Etagen-Tabs - über Tab-Manager (NICHT speichern, sind Standard!)
        if self.tab_manager:
            self.tab_manager.add_tab("Erdgeschoss", "🏡", 
                                     lambda parent: self.create_floor_content(parent, "🏡 Erdgeschoss"),
                                     skip_save=True)  # Standard-Tab, nicht speichern!
            self.tab_manager.add_tab("Obergeschoss", "🔼",
                                     lambda parent: self.create_floor_content(parent, "🔼 Obergeschoss"),
                                     skip_save=True)  # Standard-Tab, nicht speichern!
            self.tab_manager.add_tab("Dachboden", "⬆️",
                                     lambda parent: self.create_floor_content(parent, "⬆️ Dachboden"),
                                     skip_save=True)  # Standard-Tab, nicht speichern!
            
            # Custom Tabs werden automatisch in tab_manager.set_notebook() geladen
        
        # Card-Management Tab
        if self.card_manager:
            mgmt_frame = self.gui.add_tab("⚙️ Card-Verwaltung")
            content = self.card_manager.create_management_tab(mgmt_frame)
        
        # Tab-Manager Tab
        if self.tab_manager:
            tab_mgmt_frame = self.gui.add_tab("📑 Tab-Manager")
            
            tk.Button(
                tab_mgmt_frame,
                text="📑 Tabs verwalten",
                font=('Segoe UI', 14, 'bold'),
                bg=self.gui.colors['primary'],
                fg='white',
                command=self.tab_manager.create_management_dialog,
                padx=30,
                pady=15
            ).pack(pady=50)
    
    def create_floor_content(self, parent, floor_name: str):
        """Erstellt Inhalt für Etagen-Tab"""
        if not self.cards:
            return
        
        # Container für Cards
        container = self.gui.create_frame(parent, bg=self.gui.colors['bg'], relief='flat')
        container.pack(fill='both', expand=True, padx=20, pady=20)
        
        # Grid-Config
        for i in range(3):
            container.grid_columnconfigure(i, weight=1, minsize=350)
        
        # Lade Cards für diese Etage
        if self.config:
            custom_lights = self.config.get_custom_lights()
            
            row = 0
            col = 0
            
            for card_id, card_data in custom_lights.items():
                if card_data.get('floor') == floor_name:
                    # Erstelle Card
                    card = self.cards.create_card(container, card_id, card_data)
                    card.grid(row=row, column=col, padx=10, pady=10, sticky='nsew')
                    
                    col += 1
                    if col >= 3:
                        col = 0
                        row += 1
    
    def create_control_panel(self, parent):
        """Erstellt Control Panel"""
        panel = self.gui.create_frame(parent)
        panel.pack(fill='x', pady=(10, 0))
        
        inner = self.gui.create_frame(panel, relief='flat')
        inner.pack(fill='x', padx=15, pady=15)
        
        # Titel
        tk.Label(
            inner,
            text="Globale Steuerung",
            font=('Segoe UI', 11, 'bold'),
            bg=self.gui.colors['card_bg']
        ).pack(side='left', padx=10)
        
        # Buttons
        btn_frame = self.gui.create_frame(inner, relief='flat')
        btn_frame.pack(side='right')
        
        # Reconnect PLC
        self.gui.create_button(
            btn_frame,
            "🔄 Reconnect",
            self.reconnect_plc,
            style='warning'
        ).pack(side='left', padx=5)
        
        # Reload GUI
        self.gui.create_button(
            btn_frame,
            "🔄 Reload",
            self.reload_gui,
            style='warning'
        ).pack(side='left', padx=5)
        
        # Module-Info
        self.gui.create_button(
            btn_frame,
            "📦 Module",
            self.show_module_info,
            style='primary'
        ).pack(side='left', padx=5)
        
        # Einstellungen
        self.gui.create_button(
            btn_frame,
            "⚙️ Einstellungen",
            self.show_settings,
            style='primary'
        ).pack(side='left', padx=5)
    
    def start_update_loop(self):
        """Startet Update-Loop"""
        if self.update_loop:
            # Lade gespeicherte Performance-Settings
            interval = 1.0  # Default
            
            if self.config:
                config_data = self.config.config
                perf_settings = config_data.get('performance', {})
                interval = perf_settings.get('update_interval', 1.0)
                
                if interval != 1.0:
                    print(f"  ℹ️  Lade Performance-Settings: {interval}s Intervall")
            
            self.update_loop.start(interval=interval)
    
    def reconnect_plc(self):
        """Reconnect PLC"""
        if self.plc:
            success = self.plc.reconnect()
            if success:
                self.gui.show_message("Verbunden", "PLC erfolgreich verbunden!", "info")
            else:
                self.gui.show_message("Fehler", "PLC-Verbindung fehlgeschlagen!", "error")
    
    def reload_gui(self):
        """Lädt GUI neu"""
        if self.gui.show_message("Reload bestätigen", 
            "GUI neu laden? Ungespeicherte Änderungen gehen verloren!", "warning"):
            # Restart app
            python = sys.executable
            os.execl(python, python, *sys.argv)
    
    def show_module_info(self):
        """Zeigt Module-Info"""
        from tkinter import scrolledtext
        
        # Prüfe ob Dialog bereits offen
        if hasattr(self, '_module_dialog') and self._module_dialog and self._module_dialog.winfo_exists():
            self._module_dialog.lift()
            return
        
        dialog = tk.Toplevel(self.root)
        dialog.title("📦 Geladene Module")
        dialog.geometry("700x500")
        self._module_dialog = dialog
        
        # Cleanup bei Close
        def on_close():
            self._module_dialog = None
            dialog.destroy()
        
        dialog.protocol("WM_DELETE_WINDOW", on_close)
        
        text_widget = scrolledtext.ScrolledText(dialog, font=('Courier', 10))
        text_widget.pack(fill='both', expand=True, padx=10, pady=10)
        text_widget.insert('1.0', self.module_manager.get_status_summary())
        text_widget.config(state='disabled')
    
    def show_settings(self):
        """Zeigt Einstellungen"""
        from tkinter import ttk
        
        # Prüfe ob Dialog bereits offen
        if hasattr(self, '_settings_dialog') and self._settings_dialog and self._settings_dialog.winfo_exists():
            self._settings_dialog.lift()
            return
        
        dialog = tk.Toplevel(self.root)
        dialog.title("⚙️ Einstellungen")
        dialog.geometry("600x400")
        self._settings_dialog = dialog
        
        # Cleanup bei Close
        def on_close():
            self._settings_dialog = None
            dialog.destroy()
        
        dialog.protocol("WM_DELETE_WINDOW", on_close)
        
        # Notebook
        settings_nb = ttk.Notebook(dialog)
        settings_nb.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Theme-Tab
        theme_frame = tk.Frame(settings_nb)
        settings_nb.add(theme_frame, text="🎨 Theme")
        
        tk.Label(theme_frame, text="Wähle Theme:",
                font=('Segoe UI', 12, 'bold')).pack(pady=20)
        
        def apply_theme_and_close(theme_name):
            """Theme anwenden und Dialog schließen"""
            if self.gui:
                self.gui.apply_theme(theme_name)
                # Speichere Theme
                if self.config:
                    self.config.current_theme = theme_name  # Update Objekt
                    self.config.config['theme'] = theme_name  # Update Dict
                    self.config.save_config()
            messagebox.showinfo("Theme geändert", f"Theme '{theme_name}' wurde aktiviert!\n\nBitte starte die App neu für vollständige Anwendung.")
        
        # Theme-Buttons Frame
        theme_btn_frame = tk.Frame(theme_frame)
        theme_btn_frame.pack(pady=10)
        
        for theme in ['blue', 'dark', 'green']:
            tk.Button(
                theme_btn_frame,
                text=f"Theme: {theme.capitalize()}",
                command=lambda t=theme: apply_theme_and_close(t),
                font=('Segoe UI', 10),
                padx=20,
                pady=10,
                bg={'blue': '#2196F3', 'dark': '#212121', 'green': '#4CAF50'}[theme],
                fg='white'
            ).pack(pady=5, fill=tk.X, padx=20)
        
        # Theme-Vorschau
        tk.Label(theme_frame, text="\n📝 Hinweis:",
                font=('Segoe UI', 10, 'bold')).pack()
        tk.Label(theme_frame, 
                text="Theme-Änderungen werden nach Neustart aktiv.\n"
                     "Die Farben können später in der config.json angepasst werden.",
                font=('Segoe UI', 9),
                fg='gray').pack(pady=5)
        
        # PLC-Tab
        plc_frame = tk.Frame(settings_nb)
        settings_nb.add(plc_frame, text="🔧 PLC")
        
        tk.Label(plc_frame, text="PLC-Konfiguration",
                font=('Segoe UI', 12, 'bold')).pack(pady=20)
        
        if self.plc:
            status = self.plc.get_connection_status()
            info = f"""
Status: {'✓ Verbunden' if status['connected'] else '✗ Getrennt'}
AMS Net ID: {status['ams_net_id']}
Fehler: {status['consecutive_errors']}
Cache: {status['cached_variables']} Variablen
"""
            tk.Label(plc_frame, text=info, justify='left').pack()
        
        # Symbol-Download Button
        def download_symbols():
            if not self.plc or not self.plc.connected:
                messagebox.showerror("Fehler", "PLC nicht verbunden!")
                return
            
            symbols = self.module_manager.get_module('symbol_manager')
            if not symbols:
                messagebox.showerror("Fehler", "Symbol-Manager nicht gefunden!")
                return
            
            # Zeige Progress
            progress_win = tk.Toplevel(dialog)
            progress_win.title("Symbol-Download")
            progress_win.geometry("400x150")
            progress_win.transient(dialog)
            
            tk.Label(progress_win, text="📥 Lade Symbole von PLC...",
                    font=('Segoe UI', 12, 'bold')).pack(pady=20)
            
            progress_label = tk.Label(progress_win, text="Bitte warten...",
                                     font=('Segoe UI', 10))
            progress_label.pack(pady=10)
            
            def do_download():
                success = symbols.download_from_plc(self.plc)
                progress_win.destroy()
                
                if success:
                    count = symbols.get_symbol_count()
                    messagebox.showinfo("Erfolg", 
                        f"✓ {count} Symbole geladen und gespeichert!\n\n"
                        f"Cache-Datei:\n{symbols.cache_file}")
                else:
                    messagebox.showerror("Fehler", 
                        "Fehler beim Laden der Symbole!\n\n"
                        "Prüfe Console für Details.")
            
            # Starte Download in Thread
            import threading
            threading.Thread(target=do_download, daemon=True).start()
        
        tk.Button(
            plc_frame,
            text="📥 Symbole von PLC laden",
            command=download_symbols,
            font=('Segoe UI', 11, 'bold'),
            bg='#2196F3',
            fg='white',
            padx=30,
            pady=10
        ).pack(pady=20)
        
        tk.Label(plc_frame, 
                text="💡 Lädt alle PLC-Symbole und speichert sie im Cache.\n"
                     "Danach sind sie im Symbol-Browser verfügbar.",
                font=('Segoe UI', 9),
                fg='gray').pack(pady=5)
        
        # Performance-Tab (NEU!)
        perf_frame = tk.Frame(settings_nb)
        settings_nb.add(perf_frame, text="⚡ Performance")
        
        tk.Label(perf_frame, text="Performance-Einstellungen",
                font=('Segoe UI', 12, 'bold')).pack(pady=20)
        
        # Update-Loop Intervall
        update_frame = tk.Frame(perf_frame)
        update_frame.pack(fill=tk.X, padx=40, pady=10)
        
        tk.Label(update_frame, text="Live-Update Intervall:",
                font=('Segoe UI', 10, 'bold')).grid(row=0, column=0, sticky='w', pady=5)
        
        current_interval = self.update_loop.update_interval if self.update_loop else 1.0
        interval_var = tk.DoubleVar(value=current_interval)
        
        tk.Label(update_frame, text="Schnell (0.2s)").grid(row=1, column=0, sticky='w')
        interval_scale = tk.Scale(
            update_frame,
            from_=0.2,
            to=5.0,
            resolution=0.1,
            orient=tk.HORIZONTAL,
            variable=interval_var,
            length=300
        )
        interval_scale.grid(row=1, column=1, padx=10)
        tk.Label(update_frame, text="Langsam (5.0s)").grid(row=1, column=2, sticky='w')
        
        current_label = tk.Label(update_frame, text=f"Aktuell: {current_interval}s",
                                font=('Segoe UI', 9, 'bold'))
        current_label.grid(row=2, column=1, pady=5)
        
        def update_label(*args):
            current_label.config(text=f"Aktuell: {interval_var.get():.1f}s")
        
        interval_var.trace('w', update_label)
        
        # Symbol-Browser Live-Update Limit
        symbol_frame = tk.Frame(perf_frame)
        symbol_frame.pack(fill=tk.X, padx=40, pady=10)
        
        tk.Label(symbol_frame, text="Symbol-Browser Live-Limit:",
                font=('Segoe UI', 10, 'bold')).grid(row=0, column=0, sticky='w', pady=5)
        
        # Lade aus Config
        saved_limit = 100  # Default
        if self.config:
            perf_settings = self.config.config.get('performance', {})
            saved_limit = perf_settings.get('symbol_browser_limit', 100)
        
        limit_var = tk.IntVar(value=saved_limit)
        
        tk.Label(symbol_frame, text="10 Symbole").grid(row=1, column=0, sticky='w')
        limit_scale = tk.Scale(
            symbol_frame,
            from_=10,
            to=500,
            resolution=10,
            orient=tk.HORIZONTAL,
            variable=limit_var,
            length=300
        )
        limit_scale.grid(row=1, column=1, padx=10)
        tk.Label(symbol_frame, text="500 Symbole").grid(row=1, column=2, sticky='w')
        
        limit_label = tk.Label(symbol_frame, text=f"Max: {limit_var.get()} Symbole",
                              font=('Segoe UI', 9, 'bold'))
        limit_label.grid(row=2, column=1, pady=5)
        
        def update_limit_label(*args):
            limit_label.config(text=f"Max: {limit_var.get()} Symbole")
        
        limit_var.trace('w', update_limit_label)
        
        # Anwenden-Button
        def apply_performance():
            if self.update_loop:
                new_interval = interval_var.get()
                new_limit = limit_var.get()
                
                # Wende Einstellungen an
                self.update_loop.update_interval = new_interval
                
                # Restart Loop mit neuem Intervall
                self.update_loop.stop()
                self.update_loop.start(interval=new_interval)
                
                # WICHTIG: Speichere in Config!
                if self.config:
                    # Hole aktuelle Config
                    config_data = self.config.config
                    
                    # Erstelle/Update Performance-Sektion
                    if 'performance' not in config_data:
                        config_data['performance'] = {}
                    
                    config_data['performance']['update_interval'] = new_interval
                    config_data['performance']['symbol_browser_limit'] = new_limit
                    
                    # Speichere
                    self.config.save_config()
                
                messagebox.showinfo("Performance", 
                    f"✓ Live-Update Intervall: {new_interval}s\n"
                    f"✓ Symbol-Browser Limit: {new_limit} Symbole\n\n"
                    "Einstellungen gespeichert und aktiv!")
        
        tk.Button(
            perf_frame,
            text="✓ Anwenden",
            command=apply_performance,
            font=('Segoe UI', 11, 'bold'),
            bg='#4CAF50',
            fg='white',
            padx=30,
            pady=10
        ).pack(pady=20)
        
        # Hinweis
        tk.Label(perf_frame, 
                text="💡 Tipp: Für schnelle Reaktionszeit: 0.2s Intervall\n"
                     "Für weniger CPU-Last: 2.0s+ Intervall",
                font=('Segoe UI', 9),
                fg='gray').pack(pady=10)
        
        # MQTT-Tab (NEU!)
        mqtt_frame = tk.Frame(settings_nb)
        settings_nb.add(mqtt_frame, text="📡 MQTT")
        
        tk.Label(mqtt_frame, text="MQTT-Konfiguration",
                font=('Segoe UI', 12, 'bold')).pack(pady=20)
        
        # Status
        if self.mqtt:
            status_text = "✓ Verbunden" if self.mqtt.connected else "✗ Nicht verbunden"
            status_color = '#4CAF50' if self.mqtt.connected else '#f44336'
            
            tk.Label(mqtt_frame, text=f"Status: {status_text}",
                    font=('Segoe UI', 11, 'bold'),
                    fg=status_color).pack(pady=10)
            
            if self.mqtt.connected:
                broker_info = f"Broker: {self.mqtt.config['broker']}:{self.mqtt.config['port']}"
                tk.Label(mqtt_frame, text=broker_info,
                        font=('Segoe UI', 10)).pack()
        
        # Config-Frame
        config_frame = tk.Frame(mqtt_frame, relief=tk.RAISED, borderwidth=1)
        config_frame.pack(fill=tk.X, padx=40, pady=20)
        
        # Broker
        tk.Label(config_frame, text="Broker:", font=('Segoe UI', 10, 'bold')).grid(
            row=0, column=0, sticky='w', padx=10, pady=5)
        broker_var = tk.StringVar(
            value=self.config.get_config_value('mqtt', {}).get('broker', 'localhost') if self.config else 'localhost'
        )
        tk.Entry(config_frame, textvariable=broker_var, width=30).grid(
            row=0, column=1, padx=10, pady=5)
        
        # Port
        tk.Label(config_frame, text="Port:", font=('Segoe UI', 10, 'bold')).grid(
            row=1, column=0, sticky='w', padx=10, pady=5)
        port_var = tk.IntVar(
            value=self.config.get_config_value('mqtt', {}).get('port', 1883) if self.config else 1883
        )
        tk.Spinbox(config_frame, from_=1, to=65535, textvariable=port_var, width=28).grid(
            row=1, column=1, padx=10, pady=5)
        
        # Username (optional)
        tk.Label(config_frame, text="Username (opt):", font=('Segoe UI', 10, 'bold')).grid(
            row=2, column=0, sticky='w', padx=10, pady=5)
        username_var = tk.StringVar(
            value=self.config.get_config_value('mqtt', {}).get('username', '') if self.config else ''
        )
        tk.Entry(config_frame, textvariable=username_var, width=30).grid(
            row=2, column=1, padx=10, pady=5)
        
        # Password (optional)
        tk.Label(config_frame, text="Password (opt):", font=('Segoe UI', 10, 'bold')).grid(
            row=3, column=0, sticky='w', padx=10, pady=5)
        password_var = tk.StringVar(
            value=self.config.get_config_value('mqtt', {}).get('password', '') if self.config else ''
        )
        tk.Entry(config_frame, textvariable=password_var, width=30, show='*').grid(
            row=3, column=1, padx=10, pady=5)
        
        # Buttons
        btn_frame = tk.Frame(mqtt_frame)
        btn_frame.pack(pady=20)
        
        def save_mqtt_config():
            if self.config:
                # Speichere Config
                config_data = self.config.config
                config_data['mqtt'] = {
                    'broker': broker_var.get(),
                    'port': port_var.get(),
                    'username': username_var.get() if username_var.get() else None,
                    'password': password_var.get() if password_var.get() else None
                }
                self.config.save_config()
                messagebox.showinfo("Gespeichert", 
                    "MQTT-Konfiguration gespeichert!\n\n"
                    "Starte App neu für Anwendung.")
        
        def test_mqtt_connection():
            # Hole MQTT-Modul (falls nicht schon vorhanden)
            mqtt = self.mqtt
            if not mqtt:
                mqtt = self.module_manager.get_module('mqtt_integration')
            
            if not mqtt:
                messagebox.showerror("Fehler", 
                    "MQTT-Modul nicht geladen!\n\n"
                    "Prüfe:\n"
                    "1. Console-Output für 'mqtt_integration'\n"
                    "2. Module-Status (📦 Module)\n"
                    "3. Ist paho-mqtt installiert?\n"
                    "   pip install paho-mqtt --break-system-packages\n\n"
                    "Starte App neu nach Installation!")
                return
            
            # Prüfe ob paho-mqtt verfügbar ist
            try:
                import paho.mqtt.client as mqtt_client
                print(f"  ✓ paho-mqtt ist verfügbar")
            except ImportError:
                messagebox.showerror("Fehler", 
                    "paho-mqtt nicht installiert!\n\n"
                    "Installiere mit:\n"
                    "pip install paho-mqtt --break-system-packages\n\n"
                    "Dann App neu starten!")
                return
            
            # Teste Verbindung
            try:
                print(f"\n🔌 Teste MQTT-Verbindung...")
                print(f"  Broker: {broker_var.get()}")
                print(f"  Port: {port_var.get()}")
                
                mqtt.disconnect()
                mqtt.configure(
                    broker_var.get(),
                    port_var.get(),
                    username_var.get() if username_var.get() else None,
                    password_var.get() if password_var.get() else None
                )
                
                success = mqtt.connect()
                
                if success:
                    print(f"  ✓ MQTT-Verbindung erfolgreich!")
                    messagebox.showinfo("Erfolg", "✓ MQTT-Verbindung erfolgreich!")
                    # Speichere für zukünftige Nutzung
                    self.mqtt = mqtt
                else:
                    print(f"  ✗ MQTT-Verbindung fehlgeschlagen!")
                    messagebox.showerror("Fehler", 
                        "✗ MQTT-Verbindung fehlgeschlagen!\n\n"
                        "Prüfe:\n"
                        "1. Broker-Adresse korrekt?\n"
                        "2. Port korrekt? (Standard: 1883)\n"
                        "3. Broker läuft?\n"
                        "4. Firewall?\n\n"
                        "Siehe Console für Details.")
            except Exception as e:
                print(f"  ✗ Fehler beim Testen: {e}")
                import traceback
                traceback.print_exc()
                messagebox.showerror("Fehler", 
                    f"Fehler beim Testen:\n{e}\n\n"
                    "Siehe Console für Details.")
        
        tk.Button(btn_frame, text="💾 Speichern", command=save_mqtt_config,
                 font=('Segoe UI', 10, 'bold'), bg='#4CAF50', fg='white',
                 padx=20, pady=8).pack(side=tk.LEFT, padx=5)
        
        tk.Button(btn_frame, text="🔌 Verbindung testen", command=test_mqtt_connection,
                 font=('Segoe UI', 10, 'bold'), bg='#2196F3', fg='white',
                 padx=20, pady=8).pack(side=tk.LEFT, padx=5)
        
        # Hinweis
        tk.Label(mqtt_frame, 
                text="💡 Tipp: Für SolarAssistant Cards MQTT-Broker konfigurieren\n"
                     "Topics werden in den Card-Einstellungen festgelegt.",
                font=('Segoe UI', 9),
                fg='gray').pack(pady=10)
        
        # Info-Tab
        info_frame = tk.Frame(settings_nb)
        settings_nb.add(info_frame, text="ℹ️ Info")
        
        info = f"""
{self.NAME} v{self.VERSION}
Build: {self.BUILD_DATE}

Module: {len(self.module_manager.get_all_modules())}
Cards: {len(self.config.get_custom_lights()) if self.config else 0}
"""
        tk.Label(info_frame, text=info, font=('Segoe UI', 10),
                justify='left').pack(pady=20)
        
        # Close
        tk.Button(dialog, text="Schließen",
                 command=on_close).pack(pady=10)
    
    def on_closing(self):
        """Beim Schließen"""
        print("\n🛑 Beende Anwendung...")
        
        # Shutdown Module
        for name, info in self.module_manager.get_all_modules().items():
            if info.module_object and hasattr(info.module_object, 'shutdown'):
                try:
                    info.module_object.shutdown()
                except Exception as e:
                    print(f"  ⚠️  Fehler bei {name}: {e}")
        
        self.root.destroy()
        print("✓ Beendet")
    
    def run(self):
        """Startet App"""
        print("\n🚀 Starte GUI...")
        print("=" * 70)
        
        if self.gui:
            self.gui.run()
        else:
            print("❌ Keine GUI verfügbar!")


def main():
    """Haupteinstiegspunkt"""
    try:
        app = SmartHomeApp()
        app.run()
    except KeyboardInterrupt:
        print("\n\n⚠️  Abbruch durch Benutzer")
    except Exception as e:
        print(f"\n\n❌ Kritischer Fehler: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()
