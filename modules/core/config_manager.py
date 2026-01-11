"""
Configuration Manager Module
Version: 1.0.0
Verwaltet alle Konfigurationsdateien und Backups
"""

from module_manager import BaseModule
from typing import Any, Dict, Optional
import json
import os
from datetime import datetime
import shutil


class ConfigManager(BaseModule):
    """
    Konfigurations-Manager
    
    Funktionen:
    - Config laden/speichern (JSON)
    - Automatische Backups
    - Versionierung & Migration
    - Custom Lights/Cards verwalten
    """
    
    NAME = "config_manager"
    VERSION = "1.0.0"
    DESCRIPTION = "Konfigurations-Verwaltung & Backups"
    AUTHOR = "TwinCAT Team"
    
    def __init__(self):
        super().__init__()

        # WICHTIG: Pfade SOFORT initialisieren (Race-Condition-Fix)
        # Setze Basis-Pfade bereits hier, NICHT erst in initialize()
        # Windows: Nutzt den Ordner, in dem das Projekt liegt
        # Linux: ~/.config/twincat_smarthome
        if os.name == 'nt':  # Windows
            # Nutzt den Ordner, in dem das Projekt liegt
            docs = os.getcwd()
            base_config_dir = os.path.join(docs, "TwinCAT_SmartHome")
        else:  # Linux/Mac
            base_config_dir = os.path.join(os.path.expanduser("~"), ".config", "twincat_smarthome")

        # Garantiere absoluten Pfad (NIEMALS None!)
        self.config_dir = os.path.abspath(base_config_dir)
        self.config_file = os.path.join(self.config_dir, "twincat_config.json")
        self.layout_file = os.path.join(self.config_dir, "twincat_layout.json")
        self.backup_dir = os.path.join(self.config_dir, "backups")

        # Erstelle Verzeichnisse sofort (falls noch nicht vorhanden)
        os.makedirs(self.config_dir, exist_ok=True)
        os.makedirs(self.backup_dir, exist_ok=True)

        self.config = {}
        self.layout = {}
        self.custom_lights = {}
        self.current_theme = 'blue'
    
    def initialize(self, app_context: Any):
        """Initialisiert Config-Manager"""
        super().initialize(app_context)

        # Pfade sind bereits in __init__() gesetzt (Race-Condition-Fix)
        # Hier nur noch Config laden
        self.load_config()
        self.load_layout()

        print(f"  [OK] {self.NAME} v{self.VERSION} initialisiert")
        print(f"  [OK] Config-Verzeichnis: {self.config_dir}")
        print(f"  [OK] Custom Lights: {len(self.custom_lights)}")
    
    def get_config_directory(self) -> str:
        """Bestimmt Config-Verzeichnis"""
        # Windows: Documents\TwinCAT_SmartHome
        # Linux: ~/.config/twincat_smarthome
        
        if os.name == 'nt':  # Windows
            # Nutzt den Ordner, in dem das Projekt liegt
            docs = os.getcwd()
            return os.path.join(docs, "TwinCAT_SmartHome")
        else:  # Linux/Mac
            return os.path.join(os.path.expanduser("~"), ".config", "twincat_smarthome")
    
    def load_config(self) -> bool:
        """Lädt Konfiguration"""
        if not os.path.exists(self.config_file):
            print(f"  [INFO] Keine Config gefunden, erstelle Default...")
            self.create_default_config()
            return False

        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # Extrahiere Daten
            self.config = data
            self.custom_lights = data.get('custom_lights', {})
            self.current_theme = data.get('theme', 'blue')

            version = data.get('version', '1.0')

            print(f"  [OK] Config geladen: v{version}, Theme={self.current_theme}")
            return True

        except Exception as e:
            print(f"  [ERROR] Fehler beim Laden der Config: {e}")
            return False
    
    def save_config(self) -> bool:
        """Speichert Konfiguration"""
        try:
            # Backup erstellen
            self.create_backup()
            
            # WICHTIG: Speichere ALLE Daten aus self.config!
            # Plus aktualisiere die wichtigen Felder
            config_data = dict(self.config)  # Kopiere existierende Config
            
            # Aktualisiere wichtige Felder
            config_data['version'] = config_data.get('version', '1.0')
            config_data['theme'] = self.current_theme
            config_data['custom_lights'] = self.custom_lights
            config_data['last_modified'] = datetime.now().isoformat()
            
            # PLC-Config bleibt erhalten wenn vorhanden
            # Performance-Settings bleiben erhalten wenn vorhanden
            # Alles andere auch!
            
            # Speichern
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, indent=2, ensure_ascii=False)

            print(f"  [OK] Config gespeichert")
            return True

        except Exception as e:
            print(f"  [ERROR] Fehler beim Speichern: {e}")
            return False
    
    def load_layout(self) -> bool:
        """Lädt Layout"""
        if not os.path.exists(self.layout_file):
            print(f"  [INFO] Kein Layout gefunden, verwende Default")
            return False

        try:
            with open(self.layout_file, 'r', encoding='utf-8') as f:
                self.layout = json.load(f)

            print(f"  [OK] Layout geladen: {len(self.layout)} Cards")
            return True

        except Exception as e:
            print(f"  [ERROR] Fehler beim Laden des Layouts: {e}")
            return False
    
    def save_layout(self, layout: Dict) -> bool:
        """Speichert Layout"""
        try:
            self.layout = layout

            with open(self.layout_file, 'w', encoding='utf-8') as f:
                json.dump(layout, f, indent=2)

            return True

        except Exception as e:
            print(f"  [ERROR] Fehler beim Speichern des Layouts: {e}")
            return False
    
    def create_default_config(self):
        """Erstellt Default-Konfiguration"""
        self.config = {
            'version': '1.0',
            'theme': 'blue',
            'plc': {
                'ams_net_id': '192.168.2.162.1.1',
                'port': 801  # TwinCAT 2 (TC2PLC1 = 801, TC3PLC1 = 851)
            },
            'custom_lights': {},
            'widgets': {},  # ⭐ v5.1.2: Widget-Section hinzugefügt
            'created': datetime.now().isoformat()
        }

        self.custom_lights = {}
        self.current_theme = 'blue'

        self.save_config()
    
    def create_backup(self) -> bool:
        """Erstellt Backup der aktuellen Config"""
        if not os.path.exists(self.config_file):
            return False
        
        try:
            # Backup-Dateiname mit Timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_file = os.path.join(self.backup_dir, f"config_backup_{timestamp}.json")
            
            # Kopiere Config
            shutil.copy2(self.config_file, backup_file)
            
            # Lösche alte Backups (behalte nur 10)
            self.cleanup_old_backups(max_backups=10)

            return True

        except Exception as e:
            print(f"  [ERROR] Backup-Fehler: {e}")
            return False
    
    def cleanup_old_backups(self, max_backups: int = 10):
        """Löscht alte Backups"""
        try:
            # Hole alle Backup-Dateien
            backups = []
            for filename in os.listdir(self.backup_dir):
                if filename.startswith('config_backup_'):
                    filepath = os.path.join(self.backup_dir, filename)
                    backups.append((filepath, os.path.getmtime(filepath)))
            
            # Sortiere nach Datum (neueste zuerst)
            backups.sort(key=lambda x: x[1], reverse=True)
            
            # Lösche alte
            for filepath, _ in backups[max_backups:]:
                os.remove(filepath)

        except Exception as e:
            print(f"  [WARNING] Cleanup-Fehler: {e}")
    
    def add_custom_light(self, light_id: str, light_data: Dict) -> bool:
        """Fügt Custom Light hinzu"""
        self.custom_lights[light_id] = light_data
        return self.save_config()
    
    def update_custom_light(self, light_id: str, light_data: Dict) -> bool:
        """Aktualisiert Custom Light"""
        if light_id in self.custom_lights:
            self.custom_lights[light_id].update(light_data)
            return self.save_config()
        return False
    
    def delete_custom_light(self, light_id: str) -> bool:
        """Löscht Custom Light"""
        if light_id in self.custom_lights:
            del self.custom_lights[light_id]
            return self.save_config()
        return False
    
    def get_custom_lights(self) -> Dict:
        """Gibt alle Custom Lights zurück"""
        return self.custom_lights
    
    def get_theme(self) -> str:
        """Gibt aktuelles Theme zurück"""
        return self.current_theme
    
    def set_theme(self, theme: str) -> bool:
        """Setzt Theme"""
        self.current_theme = theme
        return self.save_config()
    
    def get_config_value(self, key: str, default: Any = None) -> Any:
        """Holt Config-Wert"""
        return self.config.get(key, default)
    
    def set_config_value(self, key: str, value: Any) -> bool:
        """Setzt Config-Wert"""
        self.config[key] = value
        return self.save_config()

    def get_widgets(self) -> Dict:
        """
        Holt Widget-Konfiguration

        Returns:
            Dictionary mit Widget-Konfigurationen (leer wenn keine vorhanden)
        """
        return self.config.get('widgets', {})

    def set_widgets(self, widgets: Dict) -> bool:
        """
        Speichert Widget-Konfiguration

        Args:
            widgets: Dictionary mit Widget-Konfigurationen

        Returns:
            True bei Erfolg
        """
        self.config['widgets'] = widgets
        return self.save_config()

    def add_widget(self, widget_id: str, widget_config: Dict) -> bool:
        """
        Fügt einzelnes Widget hinzu

        Args:
            widget_id: Eindeutige Widget-ID
            widget_config: Widget-Konfiguration

        Returns:
            True bei Erfolg
        """
        widgets = self.get_widgets()
        widgets[widget_id] = widget_config
        return self.set_widgets(widgets)

    def remove_widget(self, widget_id: str) -> bool:
        """
        Entfernt Widget

        Args:
            widget_id: Widget-ID

        Returns:
            True bei Erfolg
        """
        widgets = self.get_widgets()
        if widget_id in widgets:
            del widgets[widget_id]
            return self.set_widgets(widgets)
        return False

    def update_widget(self, widget_id: str, updates: Dict) -> bool:
        """
        Aktualisiert Widget-Konfiguration

        Args:
            widget_id: Widget-ID
            updates: Dictionary mit Updates

        Returns:
            True bei Erfolg
        """
        widgets = self.get_widgets()
        if widget_id in widgets:
            widgets[widget_id].update(updates)
            return self.set_widgets(widgets)
        return False

    def export_config(self, filepath: str) -> bool:
        """Exportiert Config in Datei"""
        try:
            export_data = {
                'version': '1.0',
                'theme': self.current_theme,
                'custom_lights': self.custom_lights,
                'layout': self.layout,
                'exported': datetime.now().isoformat()
            }
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False)

            print(f"  [OK] Config exportiert: {filepath}")
            return True

        except Exception as e:
            print(f"  [ERROR] Export-Fehler: {e}")
            return False
    
    def import_config(self, filepath: str) -> bool:
        """Importiert Config aus Datei"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                import_data = json.load(f)
            
            # Backup erstellen vor Import
            self.create_backup()
            
            # Importiere Daten
            self.custom_lights = import_data.get('custom_lights', {})
            self.current_theme = import_data.get('theme', 'blue')
            self.layout = import_data.get('layout', {})
            
            # Speichere
            self.save_config()
            self.save_layout(self.layout)

            print(f"  [OK] Config importiert: {len(self.custom_lights)} Lights")
            return True

        except Exception as e:
            print(f"  [ERROR] Import-Fehler: {e}")
            return False
    
    def shutdown(self):
        """Speichert beim Beenden"""
        self.save_config()
        print("  [OK] Config gespeichert")


def register(module_manager):
    """Registriert Modul"""
    module_manager.register_module(
        ConfigManager.NAME,
        ConfigManager.VERSION,
        ConfigManager.DESCRIPTION,
        ConfigManager,
        author=ConfigManager.AUTHOR
    )
