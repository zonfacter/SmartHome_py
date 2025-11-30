"""
TwinCAT Smart Home - Module System
Version: 1.0.0
Zentrale Verwaltung aller Module mit Versionierung
"""

import importlib
import importlib.util
import os
import sys
from typing import Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum


class ModuleStatus(Enum):
    """Status eines Moduls"""
    LOADED = "loaded"
    ERROR = "error"
    DISABLED = "disabled"
    NOT_FOUND = "not_found"


@dataclass
class ModuleInfo:
    """Informationen über ein Modul"""
    name: str
    version: str
    description: str
    author: str
    dependencies: list
    status: ModuleStatus
    module_object: Any = None
    error_message: str = ""


class ModuleManager:
    """
    Zentrale Verwaltung aller Module
    
    Module registrieren sich selbst mit:
    - Name
    - Version
    - Abhängigkeiten
    - API-Interface
    """
    
    VERSION = "1.0.0"
    
    def __init__(self, modules_dir='modules'):
        self.modules_dir = modules_dir
        self.modules: Dict[str, ModuleInfo] = {}
        self.module_apis: Dict[str, Any] = {}
        
        # Erstelle Module-Verzeichnis
        os.makedirs(modules_dir, exist_ok=True)
        
        print(f"📦 Module Manager v{self.VERSION} gestartet")
    
    def register_module(self, name: str, version: str, description: str,
                       api_class: Any, author: str = "System", 
                       dependencies: list = None):
        """
        Registriert ein Modul
        
        Args:
            name: Modul-Name (z.B. 'modbus_integration')
            version: Version (z.B. '1.2.3')
            description: Beschreibung
            api_class: Klasse mit öffentlichen Methoden
            author: Entwickler
            dependencies: Liste von abhängigen Modulen
        """
        if dependencies is None:
            dependencies = []
        
        try:
            # Erstelle Modul-Instanz
            module_instance = api_class()
            
            self.modules[name] = ModuleInfo(
                name=name,
                version=version,
                description=description,
                author=author,
                dependencies=dependencies,
                status=ModuleStatus.LOADED,
                module_object=module_instance
            )
            
            # Speichere API-Zugriff
            self.module_apis[name] = module_instance
            
            print(f"  ✓ Modul geladen: {name} v{version}")
            return True
            
        except Exception as e:
            self.modules[name] = ModuleInfo(
                name=name,
                version=version,
                description=description,
                author=author,
                dependencies=dependencies,
                status=ModuleStatus.ERROR,
                error_message=str(e)
            )
            print(f"  ✗ Fehler bei {name}: {e}")
            return False
    
    def load_module_from_file(self, filepath: str):
        """Lädt Modul aus Datei"""
        try:
            module_name = os.path.basename(filepath).replace('.py', '')
            
            spec = importlib.util.spec_from_file_location(module_name, filepath)
            module = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = module
            spec.loader.exec_module(module)
            
            # Modul sollte register_module() aufrufen
            if hasattr(module, 'register'):
                module.register(self)
            
            return True
        except Exception as e:
            print(f"  ✗ Fehler beim Laden von {filepath}: {e}")
            return False
    
    def load_all_modules(self):
        """Lädt alle Module aus dem Verzeichnis"""
        if not os.path.exists(self.modules_dir):
            return
        
        for filename in sorted(os.listdir(self.modules_dir)):
            if filename.endswith('_module.py'):
                filepath = os.path.join(self.modules_dir, filename)
                self.load_module_from_file(filepath)
    
    def get_module(self, name: str) -> Optional[Any]:
        """Holt Modul-API"""
        return self.module_apis.get(name)
    
    def get_module_info(self, name: str) -> Optional[ModuleInfo]:
        """Holt Modul-Informationen"""
        return self.modules.get(name)
    
    def get_all_modules(self) -> Dict[str, ModuleInfo]:
        """Gibt alle Module zurück"""
        return self.modules
    
    def check_dependencies(self, module_name: str) -> bool:
        """Prüft ob alle Abhängigkeiten erfüllt sind"""
        if module_name not in self.modules:
            return False
        
        module_info = self.modules[module_name]
        
        for dep in module_info.dependencies:
            if dep not in self.modules:
                print(f"  ⚠️  {module_name} benötigt {dep}")
                return False
            
            if self.modules[dep].status != ModuleStatus.LOADED:
                print(f"  ⚠️  {module_name}: {dep} nicht geladen")
                return False
        
        return True
    
    def get_status_summary(self) -> str:
        """Erstellt Status-Übersicht"""
        total = len(self.modules)
        loaded = sum(1 for m in self.modules.values() if m.status == ModuleStatus.LOADED)
        errors = sum(1 for m in self.modules.values() if m.status == ModuleStatus.ERROR)
        
        summary = f"\n{'='*50}\n"
        summary += f"MODULE STATUS\n"
        summary += f"{'='*50}\n"
        summary += f"Gesamt: {total} | Geladen: {loaded} | Fehler: {errors}\n"
        summary += f"{'='*50}\n"
        
        for name, info in sorted(self.modules.items()):
            status_icon = {
                ModuleStatus.LOADED: "✓",
                ModuleStatus.ERROR: "✗",
                ModuleStatus.DISABLED: "○",
                ModuleStatus.NOT_FOUND: "?"
            }.get(info.status, "?")
            
            summary += f"{status_icon} {name:25s} v{info.version:10s} - {info.description}\n"
            
            if info.status == ModuleStatus.ERROR:
                summary += f"  └─ Fehler: {info.error_message}\n"
        
        summary += f"{'='*50}\n"
        return summary
    
    def call_module_method(self, module_name: str, method_name: str, *args, **kwargs):
        """
        Ruft Methode eines Moduls auf
        
        Returns:
            Ergebnis der Methode oder None bei Fehler
        """
        module = self.get_module(module_name)
        if not module:
            print(f"⚠️  Modul '{module_name}' nicht gefunden")
            return None
        
        if not hasattr(module, method_name):
            print(f"⚠️  Methode '{method_name}' in '{module_name}' nicht gefunden")
            return None
        
        try:
            method = getattr(module, method_name)
            return method(*args, **kwargs)
        except Exception as e:
            print(f"⚠️  Fehler bei {module_name}.{method_name}(): {e}")
            return None


# Beispiel-Modul-Template
class BaseModule:
    """
    Basis-Klasse für alle Module
    
    Jedes Modul sollte diese Klasse erweitern und
    in seiner register()-Funktion beim ModuleManager registrieren.
    """
    
    NAME = "base_module"
    VERSION = "1.0.0"
    DESCRIPTION = "Basis-Modul"
    AUTHOR = "System"
    DEPENDENCIES = []
    
    def __init__(self):
        """Initialisierung"""
        self.initialized = False
    
    def initialize(self, app_context: Any):
        """
        Wird beim Start aufgerufen
        
        Args:
            app_context: Haupt-Anwendung für Zugriff auf PLC, GUI, etc.
        """
        self.app = app_context
        self.initialized = True
    
    def shutdown(self):
        """Wird beim Beenden aufgerufen"""
        pass
    
    def get_info(self) -> dict:
        """Gibt Modul-Informationen zurück"""
        return {
            'name': self.NAME,
            'version': self.VERSION,
            'description': self.DESCRIPTION,
            'author': self.AUTHOR,
            'dependencies': self.DEPENDENCIES
        }


if __name__ == '__main__':
    # Test
    manager = ModuleManager()
    
    # Beispiel-Registrierung
    class TestModule(BaseModule):
        NAME = "test"
        VERSION = "1.0.0"
        DESCRIPTION = "Test-Modul"
        
        def say_hello(self):
            return "Hello from Test Module!"
    
    manager.register_module(
        TestModule.NAME,
        TestModule.VERSION,
        TestModule.DESCRIPTION,
        TestModule
    )
    
    print(manager.get_status_summary())
    
    # Test Methoden-Aufruf
    result = manager.call_module_method('test', 'say_hello')
    print(f"Result: {result}")
