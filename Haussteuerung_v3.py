"""
TwinCAT Smart Home v3.1.0
ID-BASIERTE TAB-ARCHITEKTUR

Version: v3.1.0
Build: 2024-12-04

🆕 NEU in v3.1.0:
- Tab-IDs statt Namen (TabID_XXXXXX)
- Keine Emoji-Probleme mehr!
- Tab-Sortierung möglich
- Automatische Migration alter Configs
"""

import tkinter as tk
from tkinter import ttk, messagebox
from module_manager import ModuleManager


class SmartHomeApp:
    """TwinCAT Smart Home v3.1.0 - ID-basierte Tab-Architektur"""
    
    VERSION = "3.1.0"
    NAME = "TwinCAT Smart Home"
    BUILD_DATE = "2024-12-04"
    
    def __init__(self):
        print("=" * 70)
        print(f"  {self.NAME} v{self.VERSION}")
        print(f"  Build: {self.BUILD_DATE}")
        print(f"  Auto-Discovery System")
        print("=" * 70)
        
        # Module Manager
        self.module_manager = ModuleManager()
        
        # Module References
        self.gui = None
        self.plc = None
        self.config = None
        self.symbols = None
        self.update_loop = None
        self.cards = None
        self.mqtt = None
        self.tab_manager = None
        self.card_manager = None
        
        # GUI Components
        self.root = None
        self.notebook = None
    
    def run(self):
        """Hauptfunktion"""
        try:
            # 1. Lade Module (AUTO-DISCOVERY!)
            self.load_modules()
            
            # 2. Initialisiere Module
            self.initialize_modules()
            
            # 3. Verbinde zu PLC
            self.connect_plc()
            
            # 4. Finalize (Themes definieren!)
            self.finalize_initialization()
            
            # 5. Baue GUI (NACH Themes!)
            self.build_gui()
            
            # 6. Erstelle Tabs
            self.create_tabs()
            
            # 7. Lade und render Cards
            self.load_and_render_cards()
            
            # 8. Starte Update-Loop
            self.start_update_loop()
            
            # 9. Starte GUI
            print("\n🚀 Starte GUI...")
            print("=" * 70)
            print()
            self.root.mainloop()
            
        except Exception as e:
            print(f"\n✗ Fehler: {e}")
            import traceback
            traceback.print_exc()
        finally:
            self.shutdown()
    
    def load_modules(self):
        """⭐ AUTO-DISCOVERY - Scannt automatisch modules/"""
        self.module_manager.auto_discover_modules('modules')
        self.module_manager.print_status()
    
    def initialize_modules(self):
        """Initialisiert alle geladenen Module"""
        print("\n⚙️  Initialisiere Module...")
        self.module_manager.initialize_all_modules(self)
        
        # Hole wichtige Module
        self.gui = self.module_manager.get_module('gui_manager')
        self.plc = self.module_manager.get_module('plc_communication')
        self.config = self.module_manager.get_module('config_manager')
        self.symbols = self.module_manager.get_module('symbol_manager')
        self.update_loop = self.module_manager.get_module('update_loop')
        self.cards = self.module_manager.get_module('card_renderer')
        self.mqtt = self.module_manager.get_module('mqtt_integration')
        self.tab_manager = self.module_manager.get_module('tab_manager')
        self.card_manager = self.module_manager.get_module('card_manager')
        
        # ⭐ WICHTIG: Gib PLC-Referenz an alle Plugins!
        self._inject_plc_to_plugins()
    
    def _inject_plc_to_plugins(self):
        """⭐ Gibt PLC-Referenz an alle Plugins (WICHTIG für Toggle/Pulse!)"""
        if not self.plc:
            return
        
        print("\n📌 Übergebe PLC-Referenz an Plugins...")
        
        # Hole alle Plugin-Module (v2.0.0 API: modules dict mit instance)
        for name, module_info in self.module_manager.modules.items():
            # Prüfe ob es ein Plugin ist
            if any(x in name for x in ['_plugin', 'light', 'temperature', 'gauge', 'weather', 'solarassistant']):
                # Hole Instanz vom ModuleInfo
                plugin = module_info.instance if hasattr(module_info, 'instance') else None
                if not plugin:
                    # Falls noch keine Instanz, erstelle sie
                    plugin = self.module_manager.get_module(name)
                
                if plugin and hasattr(plugin, 'plc'):
                    plugin.plc = self.plc
                    print(f"  ✓ PLC-Referenz an {name} übergeben")

    
    def connect_plc(self):
        """Verbindet zu PLC und lädt Symbole"""
        if not self.plc:
            print("\n⚠️  PLC-Modul nicht verfügbar!")
            return
        
        print("\n🔌 Verbinde zu PLC...")
        
        # PLC-Verbindung
        if self.plc.connect():
            print("  ✓ PLC verbunden")
            
            # Symbole laden
            if self.symbols:
                print("  📥 Lade Symbole...")
                try:
                    if hasattr(self.symbols, 'download_from_plc'):
                        self.symbols.download_from_plc(self.plc)
                except Exception as e:
                    print(f"  ℹ️  Symbol-Download fehlgeschlagen, verwende Cache: {e}")
        else:
            print("  ⚠️  PLC-Verbindung fehlgeschlagen - Offline-Modus")
        
        # MQTT verbinden (falls verfügbar und konfiguriert)
        if self.mqtt and hasattr(self.mqtt, 'mqtt_available') and self.mqtt.mqtt_available:
            mqtt_config = self.config.get_config_value('mqtt', {})
            if mqtt_config:
                broker = mqtt_config.get('broker', mqtt_config.get('host', '192.168.2.244'))
                port = mqtt_config.get('port', 1883)
                username = mqtt_config.get('username')
                password = mqtt_config.get('password')
                
                print(f"\n🔌 Verbinde zu MQTT: {broker}:{port}")
                try:
                    # WICHTIG: ERST configure(), DANN connect()!
                    self.mqtt.configure(broker, port, username, password)
                    if self.mqtt.connect():
                        print(f"  ✓ MQTT verbunden: {broker}")
                except Exception as e:
                    print(f"  ⚠️  MQTT-Verbindung fehlgeschlagen: {e}")
    
    def finalize_initialization(self):
        """
        Finalisiert Initialisierung
        WICHTIG: Muss VOR build_gui() aufgerufen werden!
        """
        # GUI-Themes definieren (MUSS vor build_gui() passieren!)
        if self.gui:
            self.gui.define_themes()
            print("  ✓ Themes definiert")
    
    def build_gui(self):
        """Baut GUI auf (NACH Themes!)"""
        if not self.gui:
            print("\n❌ GUI-Modul nicht verfügbar!")
            return
        
        print("\n🖼️  Baue GUI...")
        
        # Erstelle Fenster
        self.root = self.gui.create_window(
            title=f"{self.NAME} v{self.VERSION}",
            width=1920,
            height=1040
        )
        
        # JETZT ist gui.colors verfügbar (durch define_themes())!
        main_container = tk.Frame(self.root, bg=self.gui.colors['bg'])
        main_container.pack(fill='both', expand=True)
        
        # Status-Bar (oben)
        if self.module_manager.get_module('status_bar'):
            status_bar = self.module_manager.get_module('status_bar')
            status_frame = tk.Frame(main_container, bg=self.gui.colors['bg'])
            status_frame.pack(fill='x', padx=10, pady=(10, 0))
            status_bar.create_status_bar(status_frame)
            print("  ✓ Status-Bar erstellt")
        
        # Content Container
        content_container = tk.Frame(main_container, bg=self.gui.colors['bg'])
        content_container.pack(fill='both', expand=True, padx=20, pady=20)
        
        # Notebook für Tabs
        self.notebook = self.gui.create_notebook(content_container)
        self.notebook.pack(fill='both', expand=True)
        
        # ⭐ v3.1.0: Notebook-Referenz wird in create_tabs() gesetzt!
        # (TabManager v3.0 braucht kein set_notebook() mehr)
        
        # Control Panel (unten)
        self.create_control_panel(content_container)
        
        # Window-Close Handler
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        print("  ✓ GUI aufgebaut")
    
    def create_control_panel(self, parent):
        """Erstellt Control Panel mit Buttons"""
        panel = tk.Frame(parent, bg=self.gui.colors['bg'])
        panel.pack(fill='x', pady=(20, 0))
        
        # Buttons
        self.gui.create_button(
            panel,
            "🔄 Reconnect",
            self.reconnect_plc,
            style='primary'
        ).pack(side='left', padx=5)
        
        self.gui.create_button(
            panel,
            "🔄 Reload GUI",
            self.reload_gui,
            style='primary'
        ).pack(side='left', padx=5)
        
        self.gui.create_button(
            panel,
            "📦 Module",
            self.show_module_info,
            style='primary'
        ).pack(side='left', padx=5)
        
        self.gui.create_button(
            panel,
            "⚙️ Einstellungen",
            self.show_settings,
            style='primary'
        ).pack(side='left', padx=5)
        
        print("  ✓ Control Panel erstellt")
    
    def reconnect_plc(self):
        """Reconnect zu PLC"""
        if self.plc:
            self.plc.disconnect()
            if self.plc.connect():
                messagebox.showinfo("Erfolg", "✓ PLC neu verbunden!")
            else:
                messagebox.showerror("Fehler", "✗ PLC-Verbindung fehlgeschlagen!")
    
    def reload_gui(self):
        """Lädt GUI neu"""
        if messagebox.askyesno("Reload", "GUI neu laden?\n\nUngespeicherte Änderungen gehen verloren!"):
            import sys
            import os
            python = sys.executable
            os.execl(python, python, *sys.argv)
    
    def show_module_info(self):
        """Zeigt Module-Info"""
        from tkinter import scrolledtext
        
        dialog = tk.Toplevel(self.root)
        dialog.title("📦 Module")
        dialog.geometry("700x500")
        
        text = scrolledtext.ScrolledText(dialog, font=('Courier', 10))
        text.pack(fill='both', expand=True, padx=10, pady=10)
        text.insert('1.0', self.module_manager.get_status_summary())
        text.config(state='disabled')
    
    def show_settings(self):
        """Zeigt Einstellungen-Dialog"""
        from tkinter import ttk, messagebox
        
        dialog = tk.Toplevel(self.root)
        dialog.title("⚙️ Einstellungen")
        dialog.geometry("800x600")
        dialog.transient(self.root)
        
        # Notebook für Tabs
        settings_nb = ttk.Notebook(dialog)
        settings_nb.pack(fill='both', expand=True, padx=10, pady=10)
        
        # ═══════════════════════════════════════
        # MQTT TAB
        # ═══════════════════════════════════════
        mqtt_frame = tk.Frame(settings_nb, bg='white')
        settings_nb.add(mqtt_frame, text="📡 MQTT")
        
        tk.Label(mqtt_frame, text="MQTT-Konfiguration",
                font=('Segoe UI', 14, 'bold'), bg='white').pack(pady=20)
        
        # Status anzeigen
        if self.mqtt:
            status_text = "✓ Verbunden" if self.mqtt.connected else "✗ Nicht verbunden"
            status_color = '#4CAF50' if self.mqtt.connected else '#f44336'
            
            tk.Label(mqtt_frame, text=f"Status: {status_text}",
                    font=('Segoe UI', 11, 'bold'),
                    fg=status_color, bg='white').pack(pady=10)
            
            if self.mqtt.connected:
                broker_info = f"Broker: {self.mqtt.config.get('broker', 'N/A')}:{self.mqtt.config.get('port', 'N/A')}"
                tk.Label(mqtt_frame, text=broker_info,
                        font=('Segoe UI', 10), bg='white').pack()
        
        # Config-Frame
        config_frame = tk.Frame(mqtt_frame, relief=tk.RAISED, borderwidth=2, bg='white')
        config_frame.pack(fill=tk.X, padx=40, pady=20)
        
        # Broker
        tk.Label(config_frame, text="Broker:", font=('Segoe UI', 10, 'bold'),
                bg='white').grid(row=0, column=0, sticky='w', padx=10, pady=10)
        broker_var = tk.StringVar(
            value=self.config.get_config_value('mqtt', {}).get('broker', '192.168.2.244') if self.config else '192.168.2.244'
        )
        tk.Entry(config_frame, textvariable=broker_var, width=30,
                font=('Segoe UI', 10)).grid(row=0, column=1, padx=10, pady=10)
        
        # Port
        tk.Label(config_frame, text="Port:", font=('Segoe UI', 10, 'bold'),
                bg='white').grid(row=1, column=0, sticky='w', padx=10, pady=10)
        port_var = tk.IntVar(
            value=self.config.get_config_value('mqtt', {}).get('port', 1883) if self.config else 1883
        )
        tk.Spinbox(config_frame, from_=1, to=65535, textvariable=port_var, width=28,
                  font=('Segoe UI', 10)).grid(row=1, column=1, padx=10, pady=10)
        
        # Username (optional)
        tk.Label(config_frame, text="Username (optional):", font=('Segoe UI', 10, 'bold'),
                bg='white').grid(row=2, column=0, sticky='w', padx=10, pady=10)
        username_var = tk.StringVar(
            value=self.config.get_config_value('mqtt', {}).get('username', '') if self.config else ''
        )
        tk.Entry(config_frame, textvariable=username_var, width=30,
                font=('Segoe UI', 10)).grid(row=2, column=1, padx=10, pady=10)
        
        # Password (optional)
        tk.Label(config_frame, text="Password (optional):", font=('Segoe UI', 10, 'bold'),
                bg='white').grid(row=3, column=0, sticky='w', padx=10, pady=10)
        password_var = tk.StringVar(
            value=self.config.get_config_value('mqtt', {}).get('password', '') if self.config else ''
        )
        tk.Entry(config_frame, textvariable=password_var, width=30, show='*',
                font=('Segoe UI', 10)).grid(row=3, column=1, padx=10, pady=10)
        
        # Buttons
        btn_frame = tk.Frame(mqtt_frame, bg='white')
        btn_frame.pack(pady=20)
        
        def save_mqtt_config():
            """Speichert MQTT-Config"""
            if self.config:
                config_data = self.config.config
                config_data['mqtt'] = {
                    'broker': broker_var.get(),
                    'port': port_var.get(),
                    'username': username_var.get() if username_var.get() else None,
                    'password': password_var.get() if password_var.get() else None
                }
                self.config.save_config()
                messagebox.showinfo("Gespeichert", 
                    "✓ MQTT-Konfiguration gespeichert!\n\n"
                    "Starte App neu damit Änderungen wirksam werden.")
        
        tk.Button(btn_frame, text="💾 Speichern", command=save_mqtt_config,
                 font=('Segoe UI', 11, 'bold'), bg='#4CAF50', fg='white',
                 padx=30, pady=10).pack(side='left', padx=5)
        
        tk.Button(btn_frame, text="✕ Schließen", command=dialog.destroy,
                 font=('Segoe UI', 11, 'bold'), bg='#757575', fg='white',
                 padx=30, pady=10).pack(side='left', padx=5)
        
        # Info
        tk.Label(mqtt_frame, 
                text="💡 Tipp: Lasse Username/Password leer wenn keine Authentifizierung benötigt wird.",
                font=('Segoe UI', 9), fg='gray', bg='white').pack(pady=20)
        
        # ═══════════════════════════════════════
        # PLC TAB
        # ═══════════════════════════════════════
        plc_frame = tk.Frame(settings_nb, bg='white')
        settings_nb.add(plc_frame, text="🔧 PLC")
        
        tk.Label(plc_frame, text="PLC-Konfiguration",
                font=('Segoe UI', 14, 'bold'), bg='white').pack(pady=20)
        
        # Status
        if self.plc:
            status_text = "✓ Verbunden" if self.plc.connected else "✗ Nicht verbunden"
            status_color = '#4CAF50' if self.plc.connected else '#f44336'
            
            tk.Label(plc_frame, text=f"Status: {status_text}",
                    font=('Segoe UI', 11, 'bold'),
                    fg=status_color, bg='white').pack(pady=10)
        
        # Config-Frame
        plc_config_frame = tk.Frame(plc_frame, relief=tk.RAISED, borderwidth=2, bg='white')
        plc_config_frame.pack(fill=tk.X, padx=40, pady=20)
        
        # AMS Net ID
        tk.Label(plc_config_frame, text="AMS Net ID:", font=('Segoe UI', 10, 'bold'),
                bg='white').grid(row=0, column=0, sticky='w', padx=10, pady=10)
        ams_net_id_var = tk.StringVar(
            value=self.config.get_config_value('plc', {}).get('ams_net_id', '192.168.2.162.1.1') if self.config else '192.168.2.162.1.1'
        )
        tk.Entry(plc_config_frame, textvariable=ams_net_id_var, width=30,
                font=('Segoe UI', 10)).grid(row=0, column=1, padx=10, pady=10)
        
        # Port
        tk.Label(plc_config_frame, text="Port:", font=('Segoe UI', 10, 'bold'),
                bg='white').grid(row=1, column=0, sticky='w', padx=10, pady=10)
        port_var = tk.IntVar(
            value=self.config.get_config_value('plc', {}).get('port', 851) if self.config else 851
        )
        tk.Spinbox(plc_config_frame, from_=801, to=861, textvariable=port_var, width=28,
                  font=('Segoe UI', 10)).grid(row=1, column=1, padx=10, pady=10)
        
        tk.Label(plc_config_frame, text="(851=TC3, 801=TC2)",
                font=('Segoe UI', 8), fg='gray', bg='white').grid(row=1, column=2, padx=5)
        
        # Buttons
        plc_btn_frame = tk.Frame(plc_frame, bg='white')
        plc_btn_frame.pack(pady=20)
        
        def save_plc_config():
            """Speichert PLC-Config"""
            if self.config:
                config_data = self.config.config
                config_data['plc'] = {
                    'ams_net_id': ams_net_id_var.get(),
                    'port': port_var.get()
                }
                self.config.save_config()
                messagebox.showinfo("Gespeichert", 
                    "✓ PLC-Konfiguration gespeichert!\n\n"
                    "Starte App neu damit Änderungen wirksam werden.")
        
        def download_symbols():
            """Lädt alle Symbole von PLC"""
            if not self.plc or not self.plc.connected:
                messagebox.showerror("Fehler", "PLC nicht verbunden!")
                return
            
            if not self.symbols:
                messagebox.showerror("Fehler", "Symbol-Manager nicht verfügbar!")
                return
            
            # Progress Dialog
            progress = tk.Toplevel(dialog)
            progress.title("Symbol-Download")
            progress.geometry("400x150")
            progress.transient(dialog)
            
            tk.Label(progress, text="📥 Lade Symbole von PLC...",
                    font=('Segoe UI', 12, 'bold')).pack(pady=20)
            
            status_label = tk.Label(progress, text="Bitte warten...",
                                   font=('Segoe UI', 10))
            status_label.pack(pady=10)
            
            def do_download():
                try:
                    status_label.config(text="Verbinde zu PLC...")
                    progress.update()
                    
                    if hasattr(self.symbols, 'download_from_plc'):
                        status_label.config(text="Lade Symbole... (kann 10-30s dauern)")
                        progress.update()
                        
                        self.symbols.download_from_plc(self.plc)
                        
                        count = len(self.symbols.symbols) if hasattr(self.symbols, 'symbols') else 0
                        
                        progress.destroy()
                        messagebox.showinfo("Erfolg", 
                            f"✓ Symbol-Download erfolgreich!\n\n"
                            f"{count} Symbole geladen und gespeichert.")
                    else:
                        progress.destroy()
                        messagebox.showerror("Fehler", "download_from_plc() Methode fehlt!")
                        
                except Exception as e:
                    progress.destroy()
                    messagebox.showerror("Fehler", f"Symbol-Download fehlgeschlagen:\n\n{e}")
            
            # Start in Thread
            import threading
            threading.Thread(target=do_download, daemon=True).start()
        
        tk.Button(plc_btn_frame, text="💾 Speichern", command=save_plc_config,
                 font=('Segoe UI', 11, 'bold'), bg='#4CAF50', fg='white',
                 padx=30, pady=10).pack(side='left', padx=5)
        
        tk.Button(plc_btn_frame, text="📥 Symbole laden", command=download_symbols,
                 font=('Segoe UI', 11, 'bold'), bg='#2196F3', fg='white',
                 padx=30, pady=10).pack(side='left', padx=5)
        
        tk.Button(plc_btn_frame, text="✕ Schließen", command=dialog.destroy,
                 font=('Segoe UI', 11, 'bold'), bg='#757575', fg='white',
                 padx=30, pady=10).pack(side='left', padx=5)
        
        # Info
        info_text = """
💡 Tipps:
• AMS Net ID: IP-Adresse des PLC-Systems + .1.1
• TC3: Port 851 (Runtime 1) / 852 (Runtime 2)
• TC2: Port 801
• Symbole laden: Lädt alle PLC-Variablen für Symbol-Browser
"""
        tk.Label(plc_frame, text=info_text,
                font=('Segoe UI', 9), fg='gray', bg='white',
                justify='left').pack(pady=20)
        
        # ═══════════════════════════════════════
        # THEME TAB
        # ═══════════════════════════════════════
        theme_frame = tk.Frame(settings_nb, bg='white')
        settings_nb.add(theme_frame, text="🎨 Theme")
        
        tk.Label(theme_frame, text="Theme auswählen",
                font=('Segoe UI', 14, 'bold'), bg='white').pack(pady=20)
        
        def apply_theme(theme_name):
            if self.config:
                self.config.config['theme'] = theme_name
                self.config.save_config()
                messagebox.showinfo("Gespeichert",
                    f"✓ Theme '{theme_name}' gespeichert!\n\n"
                    "Starte App neu damit Theme aktiv wird.")
        
        for theme in ['blue', 'dark', 'green']:
            tk.Button(
                theme_frame,
                text=f"Theme: {theme.capitalize()}",
                command=lambda t=theme: apply_theme(t),
                font=('Segoe UI', 11, 'bold'),
                padx=40, pady=15,
                bg={'blue': '#2196F3', 'dark': '#212121', 'green': '#4CAF50'}[theme],
                fg='white'
            ).pack(pady=10, fill=tk.X, padx=50)

    
    def create_tabs(self):
        """Erstellt alle Tabs (⭐ v3.1.0: ID-basiert!)"""
        print("\n📑 Erstelle Tabs...")
        
        # ⭐ v3.1.0: Tabs werden vom TabManager v3.0 verwaltet!
        # TabManager erstellt System-Tabs automatisch beim Initialize
        # und speichert sie mit eindeutigen Tab-IDs
        
        if self.tab_manager:
            # Setze Notebook-Referenz (wichtig für tab_manager)
            self.tab_manager.notebook = self.notebook
            
            # Hole alle Tabs sortiert nach Order
            all_tabs = self.tab_manager.get_all_tabs(sorted_by_order=True)
            
            print(f"  🔍 Lade {len(all_tabs)} Tabs aus Config...")
            
            for tab_data in all_tabs:
                tab_id = tab_data['id']
                name = tab_data['name']
                icon = tab_data.get('icon', '📄')
                is_system = tab_data.get('is_system', False)
                
                # Erstelle Tab in GUI
                tab_frame = tk.Frame(self.notebook, bg=self.gui.colors['bg'])
                self.notebook.add(tab_frame, text=f"{icon} {name}")
                
                # Speichere Widget-Referenz (WICHTIG für Card-Rendering!)
                self.tab_manager.tab_widgets[tab_id] = tab_frame
                
                # Erstelle Floor-Content (Container für Cards)
                self.create_floor_content(tab_frame, tab_id)
                
                system_marker = " [System]" if is_system else ""
                print(f"  ✓ Tab erstellt: {icon} {name} (ID: {tab_id}){system_marker}")
        
        # ⭐ MQTT Browser Tab
        mqtt_browser = self.module_manager.get_module('mqtt_browser')
        if mqtt_browser and hasattr(mqtt_browser, 'create_tab'):
            try:
                tab_frame = tk.Frame(self.notebook, bg=self.gui.colors['bg'])
                self.notebook.add(tab_frame, text="📡 MQTT Browser")
                mqtt_browser.create_tab(tab_frame)
                print("  ✓ MQTT Browser Tab erstellt")
            except Exception as e:
                print(f"  ⚠️  MQTT Browser Tab Fehler: {e}")
                import traceback
                traceback.print_exc()
        
        # Management Tabs
        if self.card_manager:
            mgmt_frame = self.gui.add_tab("Card-Verwaltung")
            self.card_manager.create_management_tab(mgmt_frame)
            print("  ✓ Card-Verwaltung Tab erstellt")
        
        if self.tab_manager:
            tab_mgmt_frame = self.gui.add_tab("Tab-Manager")
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
            print("  ✓ Tab-Manager Tab erstellt")
        
        print("  ✓ Tabs erstellt")
    
    def create_floor_content(self, parent, tab_id: str):
        """
        Erstellt Inhalt für Tab (⭐ v3.1.0: Nutzt Tab-ID!)
        
        Args:
            parent: Parent Widget
            tab_id: Eindeutige Tab-ID (z.B. 'TabID_a1b2c3')
        """
        if not self.cards:
            print(f"  ⚠️  CardRenderer nicht verfügbar für {tab_id}")
            return
        
        # Container für Cards
        container = tk.Frame(parent, bg=self.gui.colors['bg'])
        container.pack(fill='both', expand=True, padx=20, pady=20)
        
        # Grid-Config
        for i in range(3):
            container.grid_columnconfigure(i, weight=1, minsize=350)
        
        # ⭐ Speichere Frame-Referenz mit TAB-ID (nicht Name!)
        self.cards.tab_frames[tab_id] = container
        print(f"  🔍 Frame gespeichert für Tab-ID: {tab_id}")
    
    def load_and_render_cards(self):
        """
        Lädt und rendert alle Cards (⭐ v3.1.0: ID-basiert!)
        
        Migration:
        - Alte Cards mit 'floor' → automatisch zu 'tab_id'
        - Tab-Manager hat Name→ID Mapping
        """
        if not self.config or not self.cards:
            return
        
        print("\n🃏 Lade Cards...")
        
        # Lade Custom Lights aus Config
        custom_lights = self.config.get_custom_lights()
        print(f"  ℹ️  Custom Lights: {len(custom_lights)}")
        
        # ⭐ v3.1.0: Migration von alten 'floor' zu 'tab_id'
        migration_needed = False
        for card_id, card_data in custom_lights.items():
            # Hat Card schon tab_id?
            if 'tab_id' not in card_data and 'floor' in card_data:
                migration_needed = True
                break
        
        if migration_needed and self.tab_manager:
            print("  🔄 Migriere alte Cards (floor → tab_id)...")
            self.tab_manager._migrate_old_configs()
            # Reload nach Migration
            custom_lights = self.config.get_custom_lights()
        
        # Render jede Card
        rendered_count = 0
        failed_count = 0
        
        for card_id, card_data in custom_lights.items():
            # ⭐ Hole Tab-ID (v3.1.0)
            tab_id = card_data.get('tab_id')
            
            if not tab_id:
                print(f"  ⚠️  Card '{card_data.get('name', card_id)}' hat keine tab_id! Überspringe...")
                failed_count += 1
                continue
            
            # Hole Frame für diese Tab
            parent = self.cards.get_tab_frame(tab_id)
            
            if parent:
                try:
                    # Erstelle Card
                    frame = self.cards.create_card(parent, card_id, card_data)
                    if frame:
                        # Hole Tab-Name für Debug-Output
                        tab_data = self.tab_manager.get_tab_by_id(tab_id) if self.tab_manager else None
                        tab_display = f"{tab_data['icon']} {tab_data['name']}" if tab_data else tab_id
                        
                        print(f"  ✓ {card_data.get('name', card_id)} in {tab_display}")
                        rendered_count += 1
                except Exception as e:
                    print(f"  ⚠️  Fehler bei Card {card_id}: {e}")
                    failed_count += 1
                    import traceback
                    traceback.print_exc()
            else:
                # Tab nicht gefunden - Debug-Info
                tab_data = self.tab_manager.get_tab_by_id(tab_id) if self.tab_manager else None
                if tab_data:
                    tab_name = f"{tab_data['icon']} {tab_data['name']}"
                else:
                    tab_name = f"ID: {tab_id}"
                
                print(f"  ⚠️  Tab nicht gefunden: {tab_name}")
                print(f"      Card: {card_data.get('name', card_id)}")
                print(f"      💡 Verfügbare Tab-IDs: {list(self.cards.tab_frames.keys())[:5]}...")
                failed_count += 1
        
        # Update Grid für alle Tabs
        print(f"\n🔧 Update Grid-Layouts...")
        for tab_id in self.cards.tab_frames.keys():
            print(f"  🔧 Grid-Update für Tab-ID: {tab_id}")
            self.cards.update_grid_layout(tab_id)
        
        print(f"  ✓ {rendered_count}/{len(custom_lights)} Cards gerendert" +
              (f" ({failed_count} Fehler)" if failed_count > 0 else ""))
    
    def start_update_loop(self):
        """Startet Update-Loop"""
        if self.update_loop:
            print("\n▶️  Starte Update-Loop...")
            self.update_loop.start()
        
        # ⭐ Starte Status-Bar Updates
        status_bar = self.module_manager.get_module('status_bar')
        if status_bar and hasattr(status_bar, 'start_updates'):
            status_bar.start_updates()
            print("  ▶️ Status-Bar Updates gestartet")

    
    def on_closing(self):
        """Beim Schließen"""
        if messagebox.askokcancel("Beenden", "Anwendung wirklich beenden?"):
            self.root.quit()
    
    def shutdown(self):
        """Shutdown"""
        print("\n🛑 Beende Anwendung...")
        
        # Stop Update-Loop
        if self.update_loop:
            self.update_loop.stop()
        
        # PLC trennen
        if self.plc:
            self.plc.disconnect()
            print("  ✓ PLC getrennt")
        
        # Config speichern
        if self.config:
            self.config.save_config()
            print("  ✓ Config gespeichert")
        
        # Symbol-Cache speichern
        if self.symbols:
            self.symbols.save_cache()
            print("  ✓ Symbol-Cache gespeichert")
        
        # Tabs speichern
        if self.tab_manager and hasattr(self.tab_manager, '_save_tabs'):
            self.tab_manager._save_tabs()
            print("  ✓ Tabs gespeichert")
        
        # MQTT trennen
        if self.mqtt and hasattr(self.mqtt, 'connected') and self.mqtt.connected:
            if hasattr(self.mqtt, 'disconnect'):
                self.mqtt.disconnect()
                print("  ✓ MQTT getrennt")
        
        # RTSP trennen
        rtsp = self.module_manager.get_module('rtsp_integration')
        if rtsp and hasattr(rtsp, 'stop_all_streams'):
            rtsp.stop_all_streams()
            print("  ✓ RTSP Streams gestoppt")
        
        print("✓ Beendet")


def main():
    """Main Entry Point"""
    try:
        app = SmartHomeApp()
        app.run()
    except KeyboardInterrupt:
        print("\n\n⚠️  Abbruch durch Benutzer")
    except Exception as e:
        print(f"\n✗ Kritischer Fehler: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()
