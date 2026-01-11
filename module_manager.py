"""
Module Manager v2.1.0
ECHTES Auto-Discovery System mit automatischer Tab-Integration

Features:
- Automatisches Scannen aller Module
- Keine manuelle Code-Änderung nötig
- Module registrieren sich selbst für Tabs
- Enable/Disable in Settings
- Plug & Play

Changelog:
- v2.1.0 (2025-12-04):
  - Added: get_status_summary() Methode für textuelle Zusammenfassung der Module (für UI-Info).
  - Improved: Fehlerbehandlung bei Modul-Initialisierung.
  - Fixed: Potenzielle AttributeErrors in Modul-Status.
- v2.0.0: Initiale Version mit Auto-Discovery und Tab-Integration.
"""

import os
import sys
import importlib.util
from enum import Enum
from typing import Dict, Any, Optional, List
import json

# Sentry Integration (optional)
try:
    import sentry_sdk
    SENTRY_AVAILABLE = True
except ImportError:
    SENTRY_AVAILABLE = False
    print("  ℹ️  sentry-sdk nicht installiert - Error-Tracking deaktiviert")


class ModuleStatus(Enum):
    """Module Status"""
    LOADED = "LOADED"
    ERROR = "ERROR"
    DISABLED = "DISABLED"


class ModuleInfo:
    """Module Information"""
    def __init__(self, name: str, version: str, description: str, 
                 module_class: Any, author: str = "Unknown", 
                 dependencies: list = None):
        self.name = name
        self.version = version
        self.description = description
        self.module_class = module_class
        self.author = author
        self.dependencies = dependencies or []
        self.status = ModuleStatus.LOADED
        self.instance = None
        self.error_message = None
        
        # ⭐ NEU: Tab-Support
        self.has_tab = False
        self.tab_name = None
        self.tab_icon = None
        self.tab_order = 999  # Default: am Ende


class ModuleManager:
    """
    Module Manager v2.1.0
    
    ⭐ NEU:
    - Auto-Discovery: Scannt automatisch alle Module
    - Auto-Tab-Integration: Module mit Tabs werden automatisch eingebunden
    - Settings: Enable/Disable über Config
    """
    
    def __init__(self, config_file: str = None):
        self.modules: Dict[str, ModuleInfo] = {}
        self.config_file = config_file or 'module_config.json'
        self.disabled_modules = []

        # Resource Limiter (Phase 10)
        self.resource_limiter = None
        self._init_resource_limiter()

        # Lade disabled Module aus Config
        self._load_config()

    def _init_resource_limiter(self):
        """Initialisiert Resource Limiter (falls psutil verfügbar)"""
        try:
            from modules.core.resource_limiter import ResourceLimiter

            # CPU-Limit aus Environment oder Default 50%
            cpu_limit = int(os.getenv('CPU_LIMIT_PERCENT', '50'))
            check_interval = int(os.getenv('RESOURCE_CHECK_INTERVAL', '5'))

            self.resource_limiter = ResourceLimiter(
                cpu_limit_percent=cpu_limit,
                check_interval=check_interval
            )

            self.resource_limiter.start_monitoring()
            print(f"  ⚡ Resource Limiter aktiviert (CPU-Limit: {cpu_limit}%)")

        except ImportError:
            print("  ℹ️  psutil nicht verfügbar - Resource Limiter deaktiviert")
            self.resource_limiter = None
        except Exception as e:
            print(f"  ⚠️  Resource Limiter Fehler: {e}")
            self.resource_limiter = None
    
    def _load_config(self):
        """Lädt Module-Config (welche disabled sind)"""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r') as f:
                    config = json.load(f)
                    self.disabled_modules = config.get('disabled_modules', [])
            except Exception as e:
                print(f"  ⚠️  Konnte Module-Config nicht laden: {e}")
    
    def _save_config(self):
        """Speichert Module-Config"""
        config = {
            'disabled_modules': self.disabled_modules
        }
        try:
            with open(self.config_file, 'w') as f:
                json.dump(config, f, indent=2)
        except Exception as e:
            print(f"  ⚠️  Konnte Module-Config nicht speichern: {e}")
    
    def is_module_enabled(self, module_name: str) -> bool:
        """Prüft ob Modul enabled ist"""
        return module_name not in self.disabled_modules
    
    def enable_module(self, module_name: str):
        """Aktiviert Modul"""
        if module_name in self.disabled_modules:
            self.disabled_modules.remove(module_name)
            self._save_config()
            print(f"  ✓ Modul aktiviert: {module_name}")
    
    def disable_module(self, module_name: str):
        """Deaktiviert Modul"""
        if module_name not in self.disabled_modules:
            self.disabled_modules.append(module_name)
            self._save_config()
            print(f"  ✓ Modul deaktiviert: {module_name}")
    
    def register_module(self, name: str, version: str, description: str, 
                       module_class: Any, author: str = "Unknown",
                       dependencies: list = None):
        """Registriert Modul"""
        module_info = ModuleInfo(name, version, description, module_class, 
                                author, dependencies)
        
        # Prüfe ob disabled
        if not self.is_module_enabled(name):
            module_info.status = ModuleStatus.DISABLED
            print(f"  ⏸️  Modul übersprungen (disabled): {name} v{version}")
            self.modules[name] = module_info
            return
        
        # ⭐ NEU: Prüfe Tab-Support
        if hasattr(module_class, 'HAS_TAB') and module_class.HAS_TAB:
            module_info.has_tab = True
            module_info.tab_name = getattr(module_class, 'TAB_NAME', name)
            module_info.tab_icon = getattr(module_class, 'TAB_ICON', '📄')
            module_info.tab_order = getattr(module_class, 'TAB_ORDER', 999)
        
        self.modules[name] = module_info
        print(f"  ✓ Modul geladen: {name} v{version}")
        if module_info.has_tab:
            print(f"    └─ Tab: {module_info.tab_icon} {module_info.tab_name}")

    def load_module_from_file(self, filepath: str) -> Optional[str]:
        """Lädt Modul aus Datei und unterscheidet zwischen Plugin und Utility."""
        if not os.path.exists(filepath):
            return None

        try:
            module_name = os.path.splitext(os.path.basename(filepath))[0]
            spec = importlib.util.spec_from_file_location(module_name, filepath)
            module = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = module
            spec.loader.exec_module(module)

            # Prüfe ob es ein registrierbares Plugin ist
            if hasattr(module, 'register'):
                module.register(self)
                return module_name
            else:
                # ⭐ VERBESSERUNG: Keine Warnung mehr, sondern Info-Meldung
                # Wir kennzeichnen es als 'Helper' oder 'System-Core'
                if "core" in filepath or "gateway" in filepath:
                    print(f"  ⚙️  System-Komponente geladen: {module_name}")
                else:
                    print(f"  ℹ️  Utility-Modul (kein Plugin): {module_name}")
                return None

        except Exception as e:
            # Nur hier zeigen wir einen echten Fehler (✗)
            print(f"  ✗ KRITISCHER FEHLER beim Laden von {filepath}: {e}")
            if SENTRY_AVAILABLE:
                sentry_sdk.capture_exception(e)
            return None
    
    def auto_discover_modules(self, base_dir: str = 'modules'):
        """
        ⭐ AUTO-DISCOVERY
        Scannt automatisch alle Module in modules/
        """
        print(f"\n🔍 Auto-Discovery: Scanne {base_dir}/...")
        
        # Durchsuche alle Unterordner
        subdirs = ['core', 'gateway', 'ui', 'integrations', 'plugins']
        
        loaded_count = 0
        for subdir in subdirs:
            dir_path = os.path.join(base_dir, subdir)
            if not os.path.exists(dir_path):
                continue
            
            # Scanne alle .py Dateien
            for filename in sorted(os.listdir(dir_path)):
                if filename.endswith('.py') and not filename.startswith('__'):
                    filepath = os.path.join(dir_path, filename)
                    if self.load_module_from_file(filepath):
                        loaded_count += 1
        
        print(f"✓ Auto-Discovery: {loaded_count} Module gefunden")
    
    def get_all_modules(self) -> Dict[str, Any]:
        """
        Gibt alle Module zurück
        
        Returns:
            Dict mit module_name -> ModuleInfo (mit module_object Attribut)
        """
        result = {}
        for name, info in self.modules.items():
            # Erstelle ein Objekt das module_object enthält
            class ModuleWrapper:
                def __init__(self, module_info):
                    self.module_object = module_info.instance
                    self.name = module_info.name
                    self.version = module_info.version
                    self.status = module_info.status
            
            result[name] = ModuleWrapper(info)
        return result
    
    def get_module(self, name: str) -> Optional[Any]:
        """Holt Modul-Instanz"""
        if name not in self.modules:
            return None
        
        module_info = self.modules[name]
        
        # Disabled?
        if module_info.status == ModuleStatus.DISABLED:
            return None
        
        # Instanz schon erstellt?
        if module_info.instance:
            return module_info.instance
        
        # Erstelle Instanz
        try:
            module_info.instance = module_info.module_class()
            return module_info.instance
        except Exception as e:
            print(f"  ✗ Fehler beim Erstellen von {name}: {e}")
            module_info.status = ModuleStatus.ERROR
            module_info.error_message = str(e)
            return None
    
    def initialize_all_modules(self, app_context: Any):
        """Initialisiert alle Module"""
        print("\n⚙️  Initialisiere Module...")
        
        for name, module_info in self.modules.items():
            # Skip disabled
            if module_info.status == ModuleStatus.DISABLED:
                continue
            
            try:
                instance = self.get_module(name)
                if instance and hasattr(instance, 'initialize'):
                    instance.initialize(app_context)
            except Exception as e:
                print(f"  ✗ Fehler bei Initialisierung von {name}: {e}")
                module_info.status = ModuleStatus.ERROR
                module_info.error_message = str(e)
    
    def get_modules_with_tabs(self) -> List[ModuleInfo]:
        """
        ⭐ NEU: Gibt alle Module mit Tab-Support zurück
        Sortiert nach tab_order
        """
        tab_modules = [
            info for info in self.modules.values()
            if info.has_tab and info.status == ModuleStatus.LOADED
        ]
        return sorted(tab_modules, key=lambda x: x.tab_order)
    
    def create_all_tabs(self, gui_manager, parent_notebook):
        """
        ⭐ NEU: Erstellt automatisch alle Tabs
        KEINE manuelle Integration mehr nötig!
        """
        print("\n📑 Erstelle automatische Tabs...")
        
        tab_modules = self.get_modules_with_tabs()
        
        for module_info in tab_modules:
            try:
                # Hole Instanz
                instance = self.get_module(module_info.name)
                if not instance:
                    continue
                
                # Prüfe ob create_tab() existiert
                if not hasattr(instance, 'create_tab'):
                    print(f"  ⚠️  {module_info.name} hat HAS_TAB=True aber keine create_tab() Methode!")
                    continue
                
                # Erstelle Tab
                tab_text = f"{module_info.tab_name}"  # Ohne Icon, um Kompatibilität zu gewährleisten
                tab_frame = gui_manager.add_tab(tab_text)
                
                # Rufe create_tab()
                instance.create_tab(tab_frame)
                
                print(f"  ✓ Tab erstellt: {tab_text}")
                
            except Exception as e:
                print(f"  ✗ Fehler beim Erstellen von Tab {module_info.tab_name}: {e}")
    
    def print_status(self):
        """Zeigt Module-Status"""
        loaded = [m for m in self.modules.values() if m.status == ModuleStatus.LOADED]
        disabled = [m for m in self.modules.values() if m.status == ModuleStatus.DISABLED]
        errors = [m for m in self.modules.values() if m.status == ModuleStatus.ERROR]
        
        print("\n" + "=" * 50)
        print("MODULE STATUS")
        print("=" * 50)
        print(f"Gesamt: {len(self.modules)} | Geladen: {len(loaded)} | Disabled: {len(disabled)} | Fehler: {len(errors)}")
        print("=" * 50)
        
        for name, info in sorted(self.modules.items()):
            status_icon = {
                ModuleStatus.LOADED: "✓",
                ModuleStatus.DISABLED: "⏸️",
                ModuleStatus.ERROR: "✗"
            }[info.status]
            
            tab_info = f" [Tab: {info.tab_icon} {info.tab_name}]" if info.has_tab else ""
            
            print(f"{status_icon} {name:<25} v{info.version:<10} - {info.description}{tab_info}")
        
        print("=" * 50)
        print()
    
    def get_status_summary(self) -> str:
        """Gibt eine textuelle Zusammenfassung der Module zurück (für UI-Info)"""
        summary = "Module Status Summary:\n\n"
        loaded = [m for m in self.modules.values() if m.status == ModuleStatus.LOADED]
        disabled = [m for m in self.modules.values() if m.status == ModuleStatus.DISABLED]
        errors = [m for m in self.modules.values() if m.status == ModuleStatus.ERROR]
        
        summary += f"Gesamt: {len(self.modules)} | Geladen: {len(loaded)} | Disabled: {len(disabled)} | Fehler: {len(errors)}\n\n"
        
        for name, info in sorted(self.modules.items()):
            status = info.status.value
            tab_info = f" (Tab: {info.tab_name})" if info.has_tab else ""
            summary += f"{name} v{info.version}: {status} - {info.description}{tab_info}\n"
        
        return summary
    
    def shutdown(self):
        """Shutdown-Hook für alle Module"""
        print("\n🛑 Shutdown Module...")
        for name, info in self.modules.items():
            if info.instance and hasattr(info.instance, 'shutdown'):
                try:
                    info.instance.shutdown()
                    print(f"  ✓ {name} shutdown")
                except Exception as e:
                    print(f"  ⚠️  Fehler bei {name} shutdown: {e}")


class BaseModule:
    """Basis-Klasse für alle Module"""
    
    NAME = "base_module"
    VERSION = "1.0.0"
    DESCRIPTION = "Base Module"
    AUTHOR = "Unknown"
    DEPENDENCIES = []
    
    # ⭐ NEU: Tab-Support
    HAS_TAB = False
    TAB_NAME = None
    TAB_ICON = None
    TAB_ORDER = 999
    
    def __init__(self):
        self.initialized = False
        self._app_context = None
        self.sentry_enabled = False
        self._init_sentry()

    def _init_sentry(self):
        """Initialisiert Sentry Error-Tracking (falls konfiguriert)"""
        if not SENTRY_AVAILABLE:
            return

        sentry_dsn = os.getenv('SENTRY_DSN')
        if sentry_dsn:
            try:
                sentry_sdk.init(
                    dsn=sentry_dsn,
                    traces_sample_rate=1.0,
                    environment=os.getenv('ENVIRONMENT', 'production'),
                    release=f"{self.NAME}@{self.VERSION}",
                    # Performance Monitoring
                    profiles_sample_rate=0.1,
                    # Error Sampling
                    sample_rate=1.0
                )
                self.sentry_enabled = True
                print(f"  🔍 Sentry aktiviert für {self.NAME} v{self.VERSION}")
            except Exception as e:
                print(f"  ⚠️  Sentry-Initialisierung fehlgeschlagen: {e}")
                self.sentry_enabled = False

    def log_error(self, error: Exception, context: dict = None, level: str = 'error'):
        """
        Loggt Error zu Sentry mit optionalem Context

        Args:
            error: Exception-Objekt
            context: Zusätzlicher Context (dict)
            level: Sentry-Level ('error', 'warning', 'info', 'fatal')
        """
        # Sentry Logging
        if self.sentry_enabled:
            try:
                with sentry_sdk.push_scope() as scope:
                    # Module Context
                    scope.set_context("module", {
                        "name": self.NAME,
                        "version": self.VERSION,
                        "description": self.DESCRIPTION,
                        "author": self.AUTHOR
                    })

                    # Custom Context
                    if context:
                        scope.set_context("additional", context)

                    # Level setzen
                    scope.level = level

                    # Tags
                    scope.set_tag("module", self.NAME)
                    scope.set_tag("environment", os.getenv('ENVIRONMENT', 'production'))

                    # Exception erfassen
                    sentry_sdk.capture_exception(error)

            except Exception as e:
                print(f"  ⚠️  Sentry-Logging fehlgeschlagen: {e}")

        # Lokales Logging
        print(f"  ✗ [{self.NAME}] {level.upper()}: {error}")
        if context:
            print(f"     Context: {context}")

    def log_message(self, message: str, level: str = 'info', context: dict = None):
        """
        Loggt Nachricht zu Sentry

        Args:
            message: Nachricht
            level: Sentry-Level ('error', 'warning', 'info')
            context: Zusätzlicher Context (dict)
        """
        if self.sentry_enabled:
            try:
                with sentry_sdk.push_scope() as scope:
                    scope.set_context("module", {
                        "name": self.NAME,
                        "version": self.VERSION
                    })

                    if context:
                        scope.set_context("additional", context)

                    scope.level = level
                    scope.set_tag("module", self.NAME)

                    sentry_sdk.capture_message(message, level)

            except Exception as e:
                print(f"  ⚠️  Sentry-Message fehlgeschlagen: {e}")

        # Lokales Logging
        print(f"  [{self.NAME}] {message}")

    def initialize(self, app_context: Any):
        """Initialisiert Modul"""
        self._app_context = app_context
        self.initialized = True

    def shutdown(self):
        """Shutdown-Hook"""
        pass