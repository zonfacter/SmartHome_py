# Feature Roadmap Update - v4.6.0 Central Data Router

**Datum:** 2026-01-04
**Status:** Design & Architecture abgeschlossen
**Dokument:** FEATURE_ROADMAP.md wurde erweitert

---

## Zusammenfassung der Änderungen

### 1. Aktualisierung der v4.7.0 Completion-Liste
- TreeView Component hinzugefügt
- Variable Explorer hinzugefügt
- Widget CRUD APIs dokumentiert
- Hardware Monitor Integration dokumentiert
- Widget Delete Button dokumentiert
- ConfigManager Widget-Persistence Methods dokumentiert

### 2. Neue Sektion: v4.6.0 Central Data Router

Die FEATURE_ROADMAP.md wurde um eine vollständige v4.6.0 Architektur-Spezifikation erweitert:

#### **Konzept: Middleware Broker Pattern**
- Problem: Keine Cross-Interface-Kommunikation (BT → PLC unmöglich)
- Lösung: Zentraler Data Router als "Single Source of Truth"
- Architektur-Diagramm mit bidirektionalem Datenfluss

#### **6 Hauptkomponenten:**

1. **route_data() - Zentraler Message Handler**
   - Unified Data Space Normalisierung
   - 6-stufiger Flow: Normalisierung → Routing → Pub/Sub → History → Widgets → Cross-Interface
   - Python-Code mit vollständiger Implementierungs-Logik

2. **Routing Configuration System**
   - `config/routing.json` Schema (vollständig)
   - 3 Beispiel-Routing-Rules:
     - BT Sensor → PLC Variable
     - PLC Alarm → MQTT + Webhook
     - MQTT Energy → History + Widget
   - RoutingEngine Klasse mit Pattern-Matching
   - Conditions: Time-Range, Rate-Limit, Value-Filters
   - Transform Engine für Werte-Mapping

3. **History Manager Plugin**
   - SQLite + InfluxDB Support
   - Automatische Aggregation (1min, 15min, 1h, 1d)
   - Query-API mit Wildcards
   - SQLite Schema dokumentiert
   - Backend REST-Endpunkt `/api/history/query`

4. **Universal Plugin API**
   - BasePlugin erweitert BaseModule
   - `subscribe()` und `publish()` Methoden
   - Beispiel-Plugin: TemperatureAggregator
   - Vollständiger Python-Code

5. **Status Monitor & Routing Visualization**
   - Sankey-Diagram für Datenflüsse (D3.js)
   - Live-Statistiken (Messages/sec)
   - UI-Mockup als ASCII-Art
   - JavaScript RoutingMonitor Klasse
   - Backend `/api/routing/stats` Endpunkt

6. **Pub/Sub Architecture**
   - MQTT-Style Wildcards (`+`, `#`)
   - Topic-Matching Algorithmus
   - Python-Implementierung vollständig dokumentiert

#### **3 Use Cases:**
1. BT-Sensor → PLC (mit komplettem Flow)
2. PLC Alarm → MQTT + Webhook
3. Multi-Sensor Aggregation Plugin

#### **Migration Guide:**
- Schritt-für-Schritt von v4.7.0 zu v4.6.0
- Code-Beispiele (Vorher/Nachher)
- Rückwärtskompatibilität dokumentiert

#### **Implementation Timeline:**
- Phase 1 (1-2 Tage): Core Architecture
- Phase 2 (2-3 Tage): Routing Configuration
- Phase 3 (2 Tage): History Manager
- Phase 4 (1-2 Tage): Plugin API
- Phase 5 (2-3 Tage): Frontend Visualization

**Gesamt: 9-12 Tage**

---

## Technische Highlights

### **Unified Data Space:**
Alle Datenquellen werden in ein einheitliches Format normalisiert:
```python
{
    "unified_topic": "sensors/temperature/living_room",
    "source": "mqtt",
    "original_topic": "home/living/temperature",
    "value": 22.5,
    "unit": "°C",
    "timestamp": 1704405600.123,
    "quality": "good",
    "data_type": "float"
}
```

### **Cross-Interface Routing:**
Ermöglicht bisher unmögliche Szenarien:
- Bluetooth-Sensor schreibt direkt in PLC-Variable
- PLC-Alarm triggert MQTT + HTTP-Webhook gleichzeitig
- MQTT-Daten werden in History gespeichert UND an Widgets verteilt
- Multi-Source Aggregation (5 Sensoren → 1 Durchschnittswert)

### **MQTT-Style Wildcards:**
```
sensors/+/temperature    → Single-Level Wildcard
sensors/#                → Multi-Level Wildcard
```

### **Condition Engine:**
```json
{
  "conditions": [
    {"type": "time_range", "start": "06:00", "end": "22:00"},
    {"type": "rate_limit", "max_updates_per_minute": 10},
    {"type": "value_range", "min": -20, "max": 50}
  ]
}
```

### **Transform Engine:**
```json
{
  "transform": "'triggered' if value else 'disarmed'"
}
```
Python-Expressions für Werte-Mapping!

---

## Dateien die erstellt werden müssen

### Backend:
1. `modules/core/routing_engine.py` - Routing Rules Engine
2. `modules/plugins/history_manager.py` - History Plugin
3. `modules/core/base_plugin.py` - Universal Plugin Interface
4. `config/routing.json` - Routing Configuration

### Frontend:
1. `web/static/js/components/routing_monitor.js` - Routing Visualization
2. Admin-Panel: Routing Config UI

### Modifikationen:
1. `modules/gateway/data_gateway.py` - route_data() Methode + Pub/Sub
2. `modules/gateway/web_manager.py` - Neue API-Endpunkte

---

## Nächste Schritte

**Empfohlene Reihenfolge:**

### Sofort (Phase 1):
1. `route_data()` in DataGateway implementieren
2. Unified Data Space Normalisierung
3. Pub/Sub Subscriber-System (MQTT Wildcards)
4. Basis routing.json Schema

### Kurzfristig (Phase 2):
1. RoutingEngine mit Pattern-Matching
2. Condition Evaluation (Time, Rate-Limit)
3. Transform Engine (Python eval)
4. Cross-Interface Execution

### Mittelfristig (Phase 3):
1. History Manager Plugin (SQLite)
2. Query API mit Aggregation
3. Retention Policies

### Optional (Phase 4+5):
1. BasePlugin Interface
2. Example Plugins
3. Routing Monitor Frontend
4. Sankey Diagram (D3.js)

---

## Änderungen im Detail

### FEATURE_ROADMAP.md:

**Zeile 3-16:** v4.6.0 → v4.7.0 aktualisiert + neue Features hinzugefügt

**Zeile 298-1018:** Komplett neue Sektion "v4.6.0 Central Data Router" mit:
- 726 Zeilen neue Dokumentation
- 6 Komponenten vollständig spezifiziert
- 3 Use Cases mit kompletten Flows
- Migration Guide
- Implementation Timeline

**Format:** Markdown mit Code-Blöcken (Python, JavaScript, JSON)

---

## Qualitätssicherung

Alle v4.6.0 Komponenten sind:
- ✅ Vollständig spezifiziert (Architektur + Code)
- ✅ Mit Use Cases dokumentiert
- ✅ Rückwärtskompatibel zu v4.7.0
- ✅ Timeline geschätzt (9-12 Tage)
- ✅ Mit Migration Guide versehen

---

**Status:** FEATURE_ROADMAP.md ist bereit für v4.6.0 Implementierung!

**Reviewer:** Bitte prüfen Sie insbesondere:
1. Routing Rules Schema - vollständig?
2. Pub/Sub Wildcard-Matching - korrekt implementiert?
3. History Manager - SQLite vs InfluxDB Trade-offs?
4. Migration Path - sind Breaking Changes vermieden?

---

**Autor:** Claude Sonnet 4.5
**Datum:** 2026-01-04 03:15 UTC
**Version:** 5.1.0-design
