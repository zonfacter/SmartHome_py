# README

## Projektübersicht
Dieses Projekt ist eine modulare, hochgradig erweiterbare Middleware‑Plattform zur Verarbeitung, Verteilung und Visualisierung technischer Daten aus unterschiedlichsten Quellen wie SPS/PLC‑Systemen, Bluetooth‑Geräten, MQTT‑Brokern, RS485‑Modulen oder weiteren Sensor‑ und Kommunikationssystemen.

Mit Version **v5.1.0** entwickelt sich das System von einer klassischen HMI‑Visualisierung zu einem **Universal Data Hub**, in dem sämtliche Datenpunkte zentral erfasst, normalisiert, verarbeitet und über deklarative Regeln weitergeleitet werden.

Der Benutzer kann **jeden gerouteten Datenpunkt** – unabhängig von dessen Ursprung – **ohne Programmierung direkt im Dashboard visualisieren**, binden oder automatisieren.

---

## Hauptfunktionen
- Verwaltung beliebig vieler paralleler Verbindungen (PLC, MQTT, Bluetooth, RS485, CAN, TCP/UDP)
- Router für deklarative Datenwege (z. B. Bluetooth‑Sensor → PLC‑Variable → MQTT‑Alarm → UI‑Widget)
- Plugin‑System für zusätzliche Protokolle, Analysemodule oder Automationslogiken
- UI‑Widget‑Editor (Drag & Drop) zur schnellen Erstellung individueller Dashboards
- Einheitlicher Datenraum (Unified Data Space) für alle eingehenden Werte
- Vollständige Entkopplung von Hardware, Routing‑Logik und UI

---

## Architektur
### DataGateway
Das zentrale Element der Plattform. Es verarbeitet sämtliche Datenpakete nach folgendem Fluss:
```
Quelle → Normalisierung → Routing → Ziel(e) → Visualisierung/Automatisierung
```

### Connection Manager
Verwaltet parallele Datenquellen, führt Health‑Checks durch, übernimmt Reconnect‑Strategien und abstrahiert die jeweiligen Protokolle.

### routing.json
Deklaratives Regelwerk, das festlegt:
- welche Datenpunkte weitergeleitet werden
- wohin sie gesendet werden
- ob sie transformiert, gefiltert oder aggregiert werden

### Plugin‑Interface
Ermöglicht die Integration zusätzlicher Hardware‑Module, Datenquellen oder Analysekomponenten.

---

## Installation
1. Repository klonen
2. Abhängigkeiten installieren
3. Gateway starten
4. Verbindungen im Connection Manager konfigurieren
5. Routen in `routing.json` definieren
6. Dashboard mit Widgets bestücken

---

## Nutzung
- Verbindungen einrichten (Bluetooth, PLC, MQTT etc.)
- Routing‑Regeln anlegen
- Widgets im Editor platzieren und miteinander verknüpfen
- Datenpunkte in Echtzeit visualisieren
- Optional: Automationen über Plugins oder Routing‑Transformen

---

## Lizenz
Siehe LICENSE Datei im Repository.

---

## Version
v5.1.0