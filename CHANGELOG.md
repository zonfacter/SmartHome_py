# Changelog

Dieses Changelog startet bewusst neu ab **v4.6.2**.
Ältere Änderungen wurden nach `docs/legacy/` ausgelagert.

## [Unreleased]

### Added
- TBD

### Changed
- TBD

### Fixed
- TBD

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
