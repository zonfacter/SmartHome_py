"""
Variable Manager v1.0.0
Zentrale Verwaltung von Variable-Subscriptions und Widget-Mappings

📁 SPEICHERORT: modules/plc/variable_manager.py

Features:
- Symbol-Registry (Metadaten-Speicherung)
- Widget-Subscriptions (Widget → Variable Zuordnung)
- Value-Cache (aktuelle Werte mit Timestamp)
- Multi-PLC Support (plc_id als Prefix)
"""

import time
import logging
from typing import Dict, Set, Optional, Any, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class SymbolInfo:
    """Symbol-Metadaten"""
    name: str
    symbol_type: str
    index_group: int
    index_offset: int
    size: int
    comment: str
    plc_id: str = 'plc_001'

    def to_dict(self):
        return {
            'name': self.name,
            'type': self.symbol_type,
            'index_group': self.index_group,
            'index_offset': self.index_offset,
            'size': self.size,
            'comment': self.comment,
            'plc_id': self.plc_id
        }


class VariableManager:
    """
    Zentrale Variable-Registry mit Subscription-Management

    Aufgaben:
    - Symbol-Metadaten speichern
    - Widget → Variable Zuordnungen verwalten
    - Subscription-Liste pflegen
    - Value-Cache für schnelle Zugriffe
    """

    def __init__(self):
        # Symbol-Registry: (plc_id, variable_name) → SymbolInfo
        self.symbols: Dict[Tuple[str, str], SymbolInfo] = {}

        # Alias-Registry: (plc_id, alias) -> full_symbol_name
        self.alias_map: Dict[Tuple[str, str], str] = {}

        # Pending-Aliase: (plc_id, full_symbol_name) -> [aliases]
        # Wird verwendet, wenn Alias aus config geladen wird, aber das Full-Symbol
        # noch nicht registriert ist (z.B. vor dem Symbol-Cache-Load)
        self.pending_aliases: Dict[Tuple[str, str], List[str]] = {}

        # Widget-Subscriptions: (plc_id, variable_name) → Set(widget_ids)
        self.subscriptions: Dict[Tuple[str, str], Set[str]] = {}

        # Reverse-Mapping: widget_id → (plc_id, variable_name)
        self.widget_mappings: Dict[str, Tuple[str, str]] = {}

        # Value-Cache: (plc_id, variable_name) → (value, timestamp)
        self.value_cache: Dict[Tuple[str, str], Tuple[Any, float]] = {}

        logger.info("✅ Variable Manager initialisiert")
        # Lade benutzerdefinierte Alias-Mappings (falls vorhanden)
        try:
            self.load_alias_mappings()
        except Exception:
            logger.debug("Keine Alias-Mappings geladen oder Fehler beim Laden")

    def register_symbol(self, symbol_info: SymbolInfo):
        """
        Registriert ein Symbol in der Registry

        Args:
            symbol_info: SymbolInfo mit allen Metadaten
        """
        key = (symbol_info.plc_id, symbol_info.name)
        self.symbols[key] = symbol_info
        logger.debug(f"Symbol registriert: {symbol_info.plc_id}/{symbol_info.name}")

        # Generiere automatische Aliase für bessere Lesbarkeit
        try:
            aliases = self._generate_aliases(symbol_info.name)
            for alias in aliases:
                alias_key = (symbol_info.plc_id, alias)
                # Registriere Alias nur wenn noch nicht vorhanden (vermeide Überschreiben)
                if alias_key not in self.symbols:
                    self.symbols[alias_key] = symbol_info
                    self.alias_map[alias_key] = symbol_info.name
                    logger.debug(f"Alias registriert: {symbol_info.plc_id}/{alias} -> {symbol_info.name}")
        except Exception as e:
            logger.debug(f"Alias-Generierung fehlgeschlagen für {symbol_info.name}: {e}")

        # Wende ggf. Pending-Aliase an, die aus config/alias_mappings.json geladen wurden
        try:
            full_key = (symbol_info.plc_id, symbol_info.name)
            if full_key in self.pending_aliases:
                for alias in self.pending_aliases.pop(full_key):
                    alias_key = (symbol_info.plc_id, alias)
                    if alias_key not in self.symbols:
                        self.symbols[alias_key] = symbol_info
                        self.alias_map[alias_key] = symbol_info.name
                        logger.debug(f"Config-Alias registriert: {symbol_info.plc_id}/{alias} -> {symbol_info.name}")
        except Exception:
            pass

    def register_symbols_bulk(self, symbols: list, plc_id: str = 'plc_001'):
        """
        Registriert mehrere Symbole auf einmal

        Args:
            symbols: Liste von PLCSymbol Objekten ODER Dictionaries
            plc_id: PLC-ID (Standard: 'plc_001')
        """
        count = 0
        for symbol in symbols:
            try:
                # Unterstütze sowohl Objekte als auch Dictionaries
                if isinstance(symbol, dict):
                    # Dictionary-Format (von symbol_browser)
                    symbol_info = SymbolInfo(
                        name=symbol.get('name', ''),
                        symbol_type=symbol.get('type', 'UNKNOWN'),
                        index_group=symbol.get('index_group', 0),
                        index_offset=symbol.get('index_offset', 0),
                        size=symbol.get('size', 0),
                        comment=symbol.get('comment', ''),
                        plc_id=plc_id
                    )
                else:
                    # Objekt-Format (PLCSymbol)
                    symbol_info = SymbolInfo(
                        name=symbol.name,
                        symbol_type=symbol.symbol_type,
                        index_group=symbol.index_group,
                        index_offset=symbol.index_offset,
                        size=symbol.size,
                        comment=symbol.comment,
                        plc_id=plc_id
                    )

                self.register_symbol(symbol_info)
                count += 1
            except Exception as e:
                logger.warning(f"Symbol konnte nicht registriert werden: {e}")
                continue

        logger.info(f"📚 {count} Symbole registriert für PLC {plc_id}")

    def _generate_aliases(self, full_name: str) -> list:
        """
        Generiert heuristische Alias-Namen aus einem vollständigen PLC-Symbolnamen.

        Beispiele:
          - MAIN.VbAusgang6 -> VbAusgang6, bAusgang6, vb_ausgang6, ausgang6
          - MAIN.fbLichter.bLichtWohnzimmer -> bLichtWohnzimmer, licht_wohnzimmer

        Die Aliase sind rein heuristisch; spezifische Mappings können später in
        einer konfigurationsdatei (`config/alias_mappings.json`) ergänzt werden.
        """
        import re

        parts = full_name.split('.')
        last = parts[-1] if parts else full_name

        aliases = set()

        # 1) raw last segment
        aliases.add(last)

        # 2) strip common single-letter type prefixes (b, n, r, s) when followed by uppercase
        stripped = re.sub(r'^[a-z]{1,2}(?=[A-Z0-9])', '', last)
        if stripped and stripped != last:
            aliases.add(stripped)

        # 3) camelCase -> snake_case (lower) and Title_Case (readable)
        def camel_to_snake(s):
            s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', s)
            s2 = re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1)
            return s2.strip('_').lower()

        snake = camel_to_snake(stripped)
        if snake:
            aliases.add(snake)
            # also add a Title_Case variant for nicer display (underscores kept)
            aliases.add('_'.join([w.capitalize() for w in snake.split('_')]))

        # 4) short-name without 'MAIN.' prefix
        if len(parts) > 1:
            short = '.'.join(parts[1:])
            aliases.add(short)

        # 5) lowercase/uppercase variants for matching
        to_add = set()
        for a in list(aliases):
            to_add.add(a.lower())
            to_add.add(a.upper())
        aliases.update(to_add)

        # Remove the original full_name if accidentally included
        aliases.discard(full_name)

        return list(aliases)

    def load_alias_mappings(self, path: str = None) -> bool:
        """
        Lädt benutzerdefinierte Alias-Mappings aus `config/alias_mappings.json`.

        Format:
        {
          "plc_001": {
            "Licht_WZ": "MAIN.fbLichter.bLichtWohnzimmer",
            "bAusgang6": "MAIN.VbAusgang6"
          }
        }
        """
        import os, json

        cfg_path = path or os.path.join(os.getcwd(), 'config', 'alias_mappings.json')
        if not os.path.exists(cfg_path):
            return False

        try:
            with open(cfg_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            for plc_id, mappings in (data or {}).items():
                if not isinstance(mappings, dict):
                    continue

                for alias, full in mappings.items():
                    full_key = (plc_id, full)
                    alias_key = (plc_id, alias)

                    # Wenn Full-Symbol schon registriert -> setze Alias direkt
                    if full_key in self.symbols:
                        self.symbols[alias_key] = self.symbols[full_key]
                        self.alias_map[alias_key] = full
                        logger.debug(f"Config-Alias registriert: {plc_id}/{alias} -> {full}")
                    else:
                        # Merke als Pending-Alias, wird bei Symbol-Registrierung angewandt
                        self.pending_aliases.setdefault(full_key, []).append(alias)

            return True

        except Exception as e:
            logger.warning(f"Fehler beim Laden der Alias-Mappings: {e}")
            return False

    def subscribe_widget(self, widget_id: str, variable_name: str, plc_id: str = 'plc_001'):
        """
        Widget abonniert eine Variable

        Args:
            widget_id: Eindeutige Widget-ID
            variable_name: Vollständiger Symbol-Name (z.B. "Light.Light_EG_WZ.bOn")
            plc_id: PLC-ID (Standard: 'plc_001')
        """
        key = (plc_id, variable_name)

        # Erstelle Subscription-Set falls nicht vorhanden
        if key not in self.subscriptions:
            self.subscriptions[key] = set()

        # Füge Widget zu Subscription hinzu
        self.subscriptions[key].add(widget_id)

        # Speichere Reverse-Mapping
        self.widget_mappings[widget_id] = key

        logger.info(f"📌 Widget {widget_id} abonniert {plc_id}/{variable_name}")
        logger.debug(f"   Insgesamt {len(self.subscriptions[key])} Subscriber für diese Variable")

    def unsubscribe_widget(self, widget_id: str):
        """
        Widget beendet Subscription

        Args:
            widget_id: Widget-ID
        """
        if widget_id not in self.widget_mappings:
            logger.debug(f"Widget {widget_id} hat keine aktive Subscription")
            return

        # Hole Variable-Key
        key = self.widget_mappings[widget_id]
        plc_id, variable_name = key

        # Entferne aus Subscription-Set
        if key in self.subscriptions:
            self.subscriptions[key].discard(widget_id)

            # Wenn keine Subscriber mehr → Entferne Key
            if len(self.subscriptions[key]) == 0:
                del self.subscriptions[key]
                logger.info(f"🗑️  Keine Subscriber mehr für {plc_id}/{variable_name}")

        # Entferne Reverse-Mapping
        del self.widget_mappings[widget_id]

        logger.info(f"📌 Widget {widget_id} Subscription beendet")

    def get_subscribers(self, variable_name: str, plc_id: str = 'plc_001') -> Set[str]:
        """
        Gibt alle Widget-IDs zurück die diese Variable abonniert haben

        Args:
            variable_name: Symbol-Name
            plc_id: PLC-ID

        Returns:
            Set von Widget-IDs
        """
        key = (plc_id, variable_name)
        return self.subscriptions.get(key, set())

    def get_all_subscribed_variables(self) -> list:
        """
        Gibt alle abonnierten Variablen zurück

        Returns:
            Liste von (plc_id, variable_name) Tupeln
        """
        return list(self.subscriptions.keys())

    def update_value(self, variable_name: str, value: Any, plc_id: str = 'plc_001'):
        """
        Aktualisiert Value-Cache

        Args:
            variable_name: Symbol-Name
            value: Neuer Wert
            plc_id: PLC-ID
        """
        key = (plc_id, variable_name)
        self.value_cache[key] = (value, time.time())
        logger.debug(f"💾 Cache aktualisiert: {plc_id}/{variable_name} = {value}")

    def get_cached_value(self, variable_name: str, plc_id: str = 'plc_001') -> Optional[Tuple[Any, float]]:
        """
        Holt Wert aus Cache

        Args:
            variable_name: Symbol-Name
            plc_id: PLC-ID

        Returns:
            Tuple (value, timestamp) oder None
        """
        key = (plc_id, variable_name)
        return self.value_cache.get(key)

    def get_symbol_info(self, variable_name: str, plc_id: str = 'plc_001') -> Optional[SymbolInfo]:
        """
        Holt Symbol-Metadaten

        Args:
            variable_name: Symbol-Name
            plc_id: PLC-ID

        Returns:
            SymbolInfo oder None
        """
        # Direct hit
        key = (plc_id, variable_name)
        if key in self.symbols:
            return self.symbols[key]

        # Fallbacks to handle different naming styles (short names, MAIN prefix, case variants)
        candidates = []

        # If variable already contains a dot, try case-variants
        if '.' in variable_name:
            candidates.append(variable_name)
            candidates.append(variable_name.upper())
            candidates.append(variable_name.lower())
        else:
            # Try with MAIN. prefix (common in configs)
            candidates.append(f"MAIN.{variable_name}")
            candidates.append(f"MAIN.{variable_name}".upper())
            candidates.append(f"MAIN.{variable_name}".lower())
            # Also try raw name with different casing
            candidates.append(variable_name.upper())
            candidates.append(variable_name.lower())

        for name in candidates:
            k = (plc_id, name)
            if k in self.symbols:
                # Cache this as direct mapping to speed up future lookups
                self.symbols[key] = self.symbols[k]
                return self.symbols[k]

        return None

    def get_statistics(self) -> dict:
        """
        Gibt Statistiken zurück

        Returns:
            Dictionary mit Statistiken
        """
        return {
            'total_symbols': len(self.symbols),
            'total_subscriptions': len(self.subscriptions),
            'total_widgets': len(self.widget_mappings),
            'cached_values': len(self.value_cache),
            'subscribed_variables': len(self.subscriptions),
            'unique_plcs': len(set(plc_id for plc_id, _ in self.symbols.keys()))
        }

    def get_subscription_snapshot(self) -> list:
        """
        Liefert eine flache Momentaufnahme aller Widget-Subscriptions.

        Returns:
            Liste von Dicts: {widget_id, plc_id, variable}
        """
        items = []
        for widget_id, key in self.widget_mappings.items():
            try:
                plc_id, variable = key
                items.append({
                    'widget_id': str(widget_id),
                    'plc_id': str(plc_id),
                    'variable': str(variable)
                })
            except Exception:
                continue
        return items

    def clear_cache(self, max_age_seconds: float = 60.0):
        """
        Löscht alte Cache-Einträge

        Args:
            max_age_seconds: Maximales Alter in Sekunden (Standard: 60s)
        """
        now = time.time()
        to_remove = []

        for key, (value, timestamp) in self.value_cache.items():
            if now - timestamp > max_age_seconds:
                to_remove.append(key)

        for key in to_remove:
            del self.value_cache[key]

        if to_remove:
            logger.info(f"🗑️  {len(to_remove)} alte Cache-Einträge gelöscht")


# Factory-Funktion für einfache Integration
def create_variable_manager() -> VariableManager:
    """
    Erstellt eine neue Variable Manager Instanz

    Returns:
        VariableManager Instanz
    """
    return VariableManager()
