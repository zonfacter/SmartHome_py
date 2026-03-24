# Changelog

Dieses Changelog startet bewusst neu ab **v4.6.2**.
Ältere Änderungen wurden nach `docs/legacy/` ausgelagert.
Die konsolidierte Release-/Versionshistorie inklusive Tags, Branch-Bezug und Doku-Gueltigkeit steht in `docs/17_release_version_history.md`.

## [4.8.0] - 2026-03-24

### Added
- Persistenter Ring-Ereignis-Speicher mit konfigurierbaren Backends `memory`, `sqlite`, `mysql`, `influxdb`
- Neue lokale Standarddatenbank `config/ring_events.db` fuer globale Ring-Events ueber mehrere Browser-Sessions hinweg
- Ring-Diagnose-Endpunkt mit Ursache/Hinweisen fuer `406`, Re-Auth, 2FA und Timeout-Faelle
- Ring-Hilfe in der UI mit Popup, offiziellen Links und konkreten Re-Auth-Schritten
- Persistente Ring-Health-Metadaten: letzter erfolgreicher Abruf, letzter Fehler, Re-Auth-Empfehlung und geschaetztes Re-Auth-Fenster
- Timeline im Ring-Info-/Diagnosebereich mit letztem Event, letztem Erfolg und Stoerungsbeginn
- Verschluesselte lokale Speicherung der Ring-Zugangsdaten und Tokens fuer spaetere Re-Auths ohne erneute Eingabe

### Changed
- Ring-Ereignis-Widget erkennt jetzt Trigger wie `Klingeln`, `Bewegung`, `Paket` und `On-Demand` klarer
- Ring-Kachel zeigt jetzt Diagnose-Badge sowie sichtbare Hinweise, wenn Live oder Event-History gerade nicht verfuegbar sind
- Ring-Snapshot-Verhalten im Kamera-Widget ist robuster und zeigt Fehler sichtbar anstatt still leer zu bleiben
- Live-Umschaltung fuer Ring wird in der UI klar deaktiviert, wenn der WebRTC-/Session-Pfad von Ring blockiert wird
- `.gitignore` deckt jetzt auch die lokale Ring-Event-DB explizit ab

### Fixed
- Ring-Events waren zuvor nicht persistent und gingen bei Neustarts oder Backend-Wechsel verloren
- Fehler in der Ring-History-Abfrage wurden bislang nur implizit sichtbar; jetzt werden sie dauerhaft gespeichert und in der UI erklaert
- Snapshot-Ausfaelle der Ring-Kamera fuehren nicht mehr nur zu einer leeren Kachel, sondern zu einer konkreten Rueckmeldung im Overlay
- Ring-Re-Auth kann jetzt vorhandene lokal gespeicherte Zugangsdaten wiederverwenden

## [4.7.0] - 2026-03-23

### Added
- Globales Theme-System mit Presets, Akzentfarbe, Flächenstil und Chrome-Tint
- Live-Vorschau für Theme- und Widget-Stil-Einstellungen
- Weitere Theme-Presets: `aurora`, `sand`, `graphite`, `berry`
- Ring-Ereignis-Kachel als Teil des Kamera-Layouts
- Persistente Widget-Stil-Konfiguration für Standard-Widgets

### Changed
- Standard-Widget-System visuell vereinheitlicht, inklusive moderner Schalterdarstellung
- Hauptseiten wie Dashboard, Setup, Admin, Widgets und Kameras auf gemeinsame Theme-Tokens gezogen
- Kamera-Kacheln, PLC-Verwaltung und Widget-/Raumlisten an den gemeinsamen UI-Standard angepasst
- Versionsmarker auf `4.7.0` synchronisiert (Runtime/UI/WebManager/Doku)

### Fixed
- Speichern des Theme-Configs stabilisiert
- Widget-Stil-Vorschau reagiert jetzt sofort auf Formänderungen
- Icon-Schnellauswahl im Widget-Editor zeigt die aktuelle Auswahl konsistent an

## [4.6.2] - 2026-02-21

### Added
- API-Key-Management im Admin-Bereich (Create/List/Update/Delete)
- Audit-Logging für API-Key-Operationen
- ONVIF/PTZ-Voraussetzungen in Kamera-Doku ergänzt

### Changed
- Auth-Pfad erweitert um validierte Managed API-Keys
- Bootstrap-Flow für ersten Key auf Trusted/Local Requests
- Versionsmarker auf `4.6.2` synchronisiert (Runtime/UI/WebManager)

### Fixed
- ONVIF/PTZ-Funktionalität durch ergänzte Dependency stabilisiert

## [4.6.1] - 2026-02-21

### Added
- Ring Snapshot Freshness Overlay
- Verbesserte Startup-Latenz (u.a. cam01)

### Fixed
- Stream-/Snapshot-Stottern in häufigen Ring-Fällen reduziert

## [4.6.0] - 2026-02-21

### Added
- Dynamische Räume/Pages in der UI
- Kiosk/Panel-Modus
- Mehrere UX- und Performance-Verbesserungen aus den PRs `#97` bis `#108`
