"""
PLC Configuration Manager v4.6.0.8
Verwaltet mehrere PLC-Konfigurationen, TPY-Dateien und das HMI-Layout.

📁 SPEICHERORT: modules/gateway/plc_config_manager.py

Änderungen v4.6.0.8:
- ✅ Fix: Absolute Pfadsicherheit durch __file__ Referenz (behebt NoneType Error auf Host-Systemen)
- ✅ Vollständige Implementierung aller Management-Methoden (add, update, delete, get)
- ✅ Robuste JSON-Handling Logik für HMI-Widgets und TPY-Dateien
"""

import json
import os
import shutil
from typing import Dict, List, Optional, Any
from datetime import datetime

class PLCConfigManager:
    """
    Verwaltet mehrere PLC-Konfigurationen und das HMI-Layout.
    Bietet Persistenz und Validierung für alle Systempfade, unabhängig vom Host-Startverzeichnis.
    """

    def __init__(self, config_dir: Optional[str] = None, plc_data_dir: Optional[str] = None):
        """
        Initialisiert den Manager und erzwingt absolute Pfade.
        Dies verhindert den Fehler: '_path_exists: path should be string... not NoneType'
        """
        # Wir berechnen den Basis-Pfad absolut ausgehend vom Standort dieser Datei
        # modules/gateway/plc_config_manager.py -> 2 Ebenen hoch zum Projekt-Root
        current_file_path = os.path.abspath(__file__)
        current_dir = os.path.dirname(current_file_path)
        base_path = os.path.abspath(os.path.join(current_dir, '..', '..'))

        # Sicherstellen, dass die Verzeichnispfade niemals None sind (Fallback auf Root/config)
        self.config_dir = config_dir if config_dir else os.path.join(base_path, 'config')
        self.plc_data_dir = plc_data_dir if plc_data_dir else os.path.join(base_path, 'plc_data')

        # Verzeichnisse physisch anlegen, falls sie auf dem Host fehlen
        os.makedirs(self.config_dir, exist_ok=True)
        os.makedirs(self.plc_data_dir, exist_ok=True)

        # Dateipfade absolut setzen
        self.config_file = os.path.join(self.config_dir, "plc_connections.json")
        self.layout_file = os.path.join(self.config_dir, "twincat_layout.json")

        # Initialisierung der Konfigurationsstruktur
        self.configs = {"plc_configs": {}, "active_plc": None}
        self.load()

    # --- CORE STORAGE METHODS ---

    def _load_json(self, filepath: str, default_value: Any) -> Any:
        """Sicheres Laden von JSON mit Fehlerbehandlung und explizitem UTF-8 Encoding."""
        if not filepath or not os.path.exists(filepath):
            return default_value
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data if data is not None else default_value
        except Exception as e:
            print(f"  ✗ Fehler beim Lesen von {os.path.basename(filepath)}: {e}")
            return default_value

    def load(self) -> bool:
        """Lädt die gesamte PLC-Konfiguration aus der Datei."""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    loaded_data = json.load(f)
                    if isinstance(loaded_data, dict):
                        self.configs = loaded_data
                print(f"  [OK] {len(self.configs.get('plc_configs', {}))} PLC-Konfiguration(en) bereit.")
            except Exception as e:
                print(f"  [ERROR] Fehler beim Laden der Config: {e}")
        return True

    def save(self) -> bool:
        """
        Speichert die Konfiguration.
        Die Prüfung auf os.path.dirname stellt sicher, dass der Pfad valide ist.
        """
        try:
            if not self.config_file:
                return False

            # Sicherstellen, dass der Ordner auf dem Host existiert
            os.makedirs(os.path.dirname(self.config_file), exist_ok=True)

            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.configs, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"  [ERROR] Fehler beim Speichern der PLC-Config: {e}")
            return False

    # --- HMI / WIDGET METHODS ---

    def get_widgets(self) -> List[Dict]:
        """Lädt Widget-Layouts für das Web-Frontend."""
        return self._load_json(self.layout_file, [])

    def save_widgets(self, widgets_data: List[Dict]) -> bool:
        """Speichert Widget-Layouts vom Frontend."""
        try:
            os.makedirs(os.path.dirname(self.layout_file), exist_ok=True)
            with open(self.layout_file, 'w', encoding='utf-8') as f:
                json.dump(widgets_data, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"  [ERROR] Fehler beim Widget-Sync: {e}")
            return False

    # --- PLC MANAGEMENT METHODS ---

    def get_all_plcs(self) -> Dict[str, Dict]:
        """Gibt alle registrierten PLCs zurück."""
        return self.configs.get('plc_configs', {})

    def get_plc(self, plc_id: str) -> Optional[Dict]:
        """Liefert Konfiguration einer spezifischen PLC."""
        return self.configs.get('plc_configs', {}).get(plc_id)

    def get_active_plc(self) -> Optional[Dict]:
        """Liefert die aktive PLC-Konfiguration."""
        active_id = self.configs.get('active_plc')
        return self.get_plc(active_id) if active_id else None

    def set_active_plc(self, plc_id: str) -> bool:
        """Wechselt die aktive PLC."""
        if plc_id in self.configs.get('plc_configs', {}):
            self.configs['active_plc'] = plc_id
            return self.save()
        return False

    def get_tpy_path(self, plc_id: str) -> Optional[str]:
        """Gibt den absoluten Pfad zur TPY-Datei zurück."""
        config = self.get_plc(plc_id)
        if not config or not config.get('tpy_file'):
            return None
        return os.path.abspath(os.path.join(self.plc_data_dir, config['tpy_file']))

    def add_plc(self, name: str, ams_net_id: str, ams_port: int = 851,
                ip_address: str = None, description: str = "",
                tpy_file: str = None) -> str:
        """Fügt eine neue PLC-Konfiguration hinzu."""
        plc_id = self._generate_plc_id()
        now = datetime.now().isoformat()

        if not ip_address:
            # Versuche IP aus AMS Net ID zu extrahieren
            parts = ams_net_id.split('.')
            ip_address = ".".join(parts[:4]) if len(parts) >= 4 else "127.0.0.1"

        self.configs['plc_configs'][plc_id] = {
            'name': name,
            'ams_net_id': ams_net_id,
            'ams_port': ams_port,
            'ip_address': ip_address,
            'tpy_file': tpy_file,
            'description': description,
            'created': now,
            'last_modified': now,
            'active': True
        }

        if not self.configs.get('active_plc'):
            self.configs['active_plc'] = plc_id

        self.save()
        return plc_id

    def update_plc(self, plc_id: str, **kwargs) -> bool:
        """Aktualisiert Felder einer bestehenden PLC-Konfiguration."""
        if plc_id not in self.configs.get('plc_configs', {}):
            return False

        config = self.configs['plc_configs'][plc_id]
        allowed = ['name', 'ams_net_id', 'ams_port', 'ip_address', 'description', 'tpy_file', 'active']

        for key, value in kwargs.items():
            if key in allowed:
                config[key] = value

        config['last_modified'] = datetime.now().isoformat()
        return self.save()

    def delete_plc(self, plc_id: str, delete_tpy: bool = False) -> bool:
        """Entfernt eine PLC-Konfiguration und optional die TPY-Datei."""
        if plc_id not in self.configs.get('plc_configs', {}):
            return False

        if delete_tpy:
            tpy_path = self.get_tpy_path(plc_id)
            if tpy_path and os.path.exists(tpy_path):
                try:
                    os.remove(tpy_path)
                except Exception as e:
                    print(f"  [WARNING] Konnte TPY-Datei nicht loeschen: {e}")

        del self.configs['plc_configs'][plc_id]

        if self.configs.get('active_plc') == plc_id:
            rem = list(self.configs['plc_configs'].keys())
            self.configs['active_plc'] = rem[0] if rem else None

        return self.save()

    # --- HELPERS ---

    def _generate_plc_id(self) -> str:
        """Generiert eine neue ID wie 'plc_001'."""
        existing = self.configs.get('plc_configs', {}).keys()
        nums = [int(i.split('_')[1]) for i in existing if i.startswith('plc_') and i.split('_')[1].isdigit()]
        next_num = max(nums) + 1 if nums else 1
        return f"plc_{str(next_num).zfill(3)}"

    def get_statistics(self) -> Dict[str, Any]:
        """Liefert Statistiken für das Dashboard."""
        cfgs = self.configs.get('plc_configs', {})

        # Berechne TPY-Gesamtgröße
        tpy_total_size = 0
        for plc_id, config in cfgs.items():
            tpy_path = self.get_tpy_path(plc_id)
            if tpy_path and os.path.exists(tpy_path):
                try:
                    tpy_total_size += os.path.getsize(tpy_path)
                except Exception:
                    pass

        # Konvertiere Bytes zu MB
        tpy_size_mb = round(tpy_total_size / (1024 * 1024), 2)

        return {
            'total_plcs': len(cfgs),
            'active_plcs': sum(1 for c in cfgs.values() if c.get('active')),
            'active_plc_id': self.configs.get('active_plc'),
            'config_path': os.path.abspath(self.config_file),
            'tpy_size': tpy_size_mb
        }