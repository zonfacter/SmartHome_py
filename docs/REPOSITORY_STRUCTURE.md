# Repository-Inventar: aktiv, legacy, runtime

Diese Übersicht ordnet die aktuell versionierten Dateien und Verzeichnisse in vier Klassen ein:

- **aktiv**: Teil des aktuellen Web-/Gateway-Stacks oder der gepflegten Projektdokumentation
- **legacy**: historisch vorhanden, aber funktional vom aktuellen Stand abgelöst
- **runtime**: zur Laufzeit erzeugt, lokal befüllt oder als Arbeitsstand/Beispieldaten genutzt
- **archivwürdig**: aktuell versioniert, aber kein aktiver Kernpfad; vor einer späteren Bereinigung separat prüfen

Ziel ist **keine** sofortige Umstrukturierung, sondern eine belastbare Grundlage für spätere Cleanup-Schritte.

## 1. Aktive Kernpfade

| Pfad | Status | Zweck |
|------|--------|-------|
| `modules/` | aktiv | Kernmodule für Core, Gateway, PLC, Plugins, Bluetooth und UI |
| `web/` | aktiv | Flask-Templates, statische Assets und Browser-UI |
| `config/` | aktiv | versionierte Konfigurationen; enthält zusätzlich lokale Runtime-Dateien |
| `scripts/` | aktiv | gepflegte Hilfs- und Validierungsskripte |
| `docs/` | aktiv | verbindliche aktive Dokumentation ab `v4.8.x` |
| `deploy/` | aktiv | Deployment-Artefakte, z. B. `systemd` |
| `ops/` | aktiv | betriebliche Beispielkonfigurationen |
| `smarthome-sdk-v5/` | aktiv | offizielles SDK und Integrationsbeispiele |
| `start_web_hmi.py` | aktiv | aktueller Einstiegspunkt für die Web-HMI |
| `module_manager.py` | aktiv | Modul-Lifecycle und Discovery |
| `import_tpy.py` | aktiv | Import-/Hilfslogik für PLC-/TPY-Daten |
| `Makefile` | aktiv | Standardbefehle für Install, Smoke, Test und Doku-Checks |
| `Dockerfile`, `docker-compose.yml` | aktiv | Container- und lokale Stack-Ausführung |
| `requirements.txt`, `requirements.lock.txt`, `package.json`, `package-lock.json` | aktiv | deklarierte Python-/Node-Abhängigkeiten |
| `test_*.py` im Repository-Root | aktiv | aktuelle automatisierte Tests, auch wenn noch kein eigenes `tests/`-Verzeichnis existiert |

## 2. Aktives Verzeichnisinventar nach Domäne

### Applikationscode

- `modules/core/`: Logging, Konfiguration, Cache-/Resilience- und Basisdienste
- `modules/gateway/`: Web- und Daten-Gateway-Funktionen
- `modules/plc/`: PLC-spezifische Kommunikation und Variablenzugriffe
- `modules/integrations/`: externe Integrationen wie MQTT/RTSP/ONVIF
- `modules/plugins/`: Plugin-System und Erweiterungen
- `modules/bluetooth/`: BLE-/BMS-Anbindung
- `modules/ui/`: UI-nahe Serverlogik

### Web-Oberfläche

- `web/templates/`: serverseitige HTML-Templates
- `web/static/js/`: Frontend-Logik
- `web/static/css/`: Styles

### Konfiguration und Betriebsunterstützung

- `config/plc_configs.json`: PLC-Definitionen
- `config/plc_connections.json`: Verbindungsparameter
- `config/routing.json`: Routing-/Gateway-Konfiguration
- `config/alias_mappings.json`: Alias-Mappings
- `deploy/systemd/`: Service-Definitionen
- `ops/staging.env.example`: Beispiel für Staging-Umgebungen

### Dokumentation

- `docs/README.md`: Einstieg in die aktive Doku
- `docs/01_quickstart.md` bis `docs/16_frontend_performance.md`: gepflegte Kern-Dokumente
- `docs/WEB_SETUP_ROUTING_ADS_GUIDE.md`: aktive Spezialanleitung für Web-Setup und ADS-Routing
- `docs/ADR/`: Architekturentscheidungen
- `docs/openapi.json`: generierter/verifizierter API-Vertrag innerhalb der aktiven Doku

## 3. Legacy- und Altlasten-Pfade

Die folgenden Pfade sind für Historie und Rückverfolgbarkeit relevant, bilden aber **nicht** die empfohlene aktive Kernstruktur:

| Pfad | Einordnung | Begründung |
|------|------------|------------|
| `docs/legacy/` | legacy | ausgelagerte historische Dokumentation; laut `docs/LEGACY.md` nicht verbindlich für aktuellen Betrieb |
| `Haussteuerung.py` | legacy | ältere Tkinter-basierte Hauptanwendung, durch Web-HMI abgelöst |
| `Haussteuerung_v3.py` | legacy | weiterer Tkinter-Stand vor dem heutigen Web-Stack |

## 4. Archivwürdige Root-Dateien und Hilfsskripte

Diese Dateien wirken nicht wie aktiver Kerncode, sind aber als Kontext oder für manuelle Analyse noch nützlich. Für spätere Bereinigung sollten sie separat validiert und danach eher archiviert als gelöscht werden.

| Pfad | Status | Hinweis |
|------|--------|---------|
| `FIXES_v5_1_1.md` | archivwürdig | versionsspezifische Hotfix-Notizen |
| `FIXES_v5_1_2.md` | archivwürdig | versionsspezifische Hotfix-Notizen |
| `PROJEKT_ZUSAMMENFASSUNG_v2.2.6.md` | archivwürdig | ältere Projektzusammenfassung |
| `analyze_light_detailed.py` | archivwürdig | einmalige/diagnostische Analysehilfe |
| `analyze_prefix_types.py` | archivwürdig | einmalige/diagnostische Analysehilfe |
| `analyze_symbol_pattern.py` | archivwürdig | einmalige/diagnostische Analysehilfe |
| `inspect_light_symbols.py` | archivwürdig | manuelle Symbol-Inspektion |
| `inspect_symbols.py` | archivwürdig | manuelle Symbol-Inspektion |
| `inspect_tpy.py` | archivwürdig | manuelle TPY-Inspektion |
| `inspect_tpy2.py` | archivwürdig | manuelle TPY-Inspektion |
| `check_rm_light.py` | archivwürdig | fallspezifisches Prüfskript außerhalb des aktiven `scripts/`-Pfads |
| `TEST_CONSOLE_SCENARIOS.js` | archivwürdig | manuelle/temporäre Konsolen-Szenarien, kein regulärer Build-/Testpfad |

## 5. Runtime-, Cache- und generierte Pfade

Diese Pfade sind für lokale Ausführung, Caches oder Arbeitsstände relevant. Sie sollten bei Aufräumarbeiten **nicht** wie Quellcode behandelt werden.

| Pfad | Status | Hinweis |
|------|--------|---------|
| `__pycache__/` | runtime | Python-Bytecode-Cache |
| `modules/**/__pycache__/` | runtime | modulbezogene Bytecode-Caches |
| `config/cache/` | runtime | lokaler Cache, bereits in `.gitignore` ausgenommen |
| `config/system_logs.db` | runtime | lokale SQLite-Logs, bereits in `.gitignore` |
| `config/ring_events.db` | runtime | lokale Runtime-Daten, bereits in `.gitignore` |
| `web/static/hls/` | runtime | HLS-Streaming-Ausgabe, bereits in `.gitignore` |
| `TwinCAT_SmartHome/backups/` | runtime | generierte/gesicherte Arbeitsstände |
| `TwinCAT_SmartHome/symbol_cache.json` | runtime | Symbol-Cache |
| `TwinCAT_SmartHome/twincat_config.json` | runtime | lokaler Arbeitsstand für TwinCAT |
| `TwinCAT_SmartHome/twincat_layout.json` | runtime | lokaler Layout-/Arbeitsstand |
| `plc_data/*.tpy` | runtime-nahe Referenzdaten | Test-/Importdaten für PLC-Symbole; kein eigentlicher Applikationscode |
| `docs/openapi.json` | generiert, aber aktiv | generierter Vertrag, bewusst versioniert und durch Checks abgesichert |

## 6. Vorschlag für aktive Kernstruktur

Für künftige Bereinigungsschritte sollte die aktive Kernstruktur auf folgende Pfade fokussiert werden:

```text
SmartHome_py/
├── docs/
├── modules/
├── web/
├── config/
├── scripts/
├── deploy/
├── ops/
├── smarthome-sdk-v5/
├── start_web_hmi.py
├── module_manager.py
├── import_tpy.py
├── test_*.py
├── Makefile
├── Dockerfile
├── docker-compose.yml
├── requirements*.txt
└── package*.json
```

## 7. Empfehlung für spätere Bereinigung

1. **Legacy klar abtrennen**  
   Root-Dateien wie `Haussteuerung.py` und `Haussteuerung_v3.py` perspektivisch in einen dedizierten Archivpfad verschieben, sobald keine aktiven Verweise mehr bestehen.

2. **Archivwürdige Root-Dateien konsolidieren**  
   Analyse-/Inspektionsskripte und versionsbezogene Markdown-Dateien entweder unter `docs/legacy/` oder in einen expliziten Archivordner überführen.

3. **Runtime von versioniertem Quellcode trennen**  
   Den Status von `TwinCAT_SmartHome/` und `plc_data/` vor einer Bereinigung bewusst entscheiden: entweder als Fixtures/Beispieldaten dokumentieren oder aus der Kernstruktur herauslösen.

4. **Tests später separat bündeln**  
   Die Root-basierten `test_*.py` sind aktiv, aber strukturell ein Kandidat für ein zukünftiges `tests/`-Verzeichnis. Für dieses Issue bleibt ihre aktuelle Lage bewusst unverändert.

## 8. Entscheidungsregel für Folgearbeiten

Bei späteren Cleanup-PRs sollte jeder Pfad zuerst einer der vier Klassen aus diesem Dokument zugeordnet werden:

- **aktiv behalten**
- **legacy archivieren**
- **runtime aus dem Quellbestand fernhalten**
- **archivwürdig erst nach Referenzprüfung verschieben**

Damit ist eine nachvollziehbare Einordnung in **aktiv, legacy, runtime, archivwürdig** vorhanden, ohne den aktuellen Codepfad voreilig umzubauen.
