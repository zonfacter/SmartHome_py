# 07 Operations Playbook (verbindlich)

Dieses Handbuch beschreibt den standardisierten Betrieb und Incident-Ablauf.

## Incident-Schweregrade
- `SEV-1`: Produktionsausfall (keine Steuerung oder Kernfunktionen betroffen)
- `SEV-2`: Starke Degradierung (Teilfunktionen instabil, Workaround möglich)
- `SEV-3`: Einzelne Features gestört, kein unmittelbarer Produktionsstopp

## Eskalationsstufen
1. `L1 Betrieb`: Erstdiagnose, sichere Sofortmaßnahmen, Incident-Ticket.
2. `L2 Entwicklung`: Fehleranalyse im Code/Config, Hotfix oder Rollback.
3. `L3 Architektur/Owner`: Cross-System-Fixes, Priorisierung, nachhaltige Maßnahmen.

## Standard-Checkliste (für jeden Incident)
1. Zeitstempel und Scope erfassen (welche Kamera/PLC/Endpoints).
2. `GET /api/system/status` und `GET /api/monitor/slo` prüfen.
3. Letzte Admin-Aktionen in `GET /api/admin/logs` verifizieren.
4. Betroffene Services/Container und Ressourcen (CPU/RAM/Disk) prüfen.
5. Nur reversible Sofortmaßnahmen zuerst (gezielter Restart statt Reboot).
6. Root-Cause-Hypothese dokumentieren und Gegenprobe durchführen.
7. Incident schließen mit Postmortem-Aktion (Issue/PR/Runbook-Update).

## Playbook A: Stream-Hänger / Stocken (RTSP oder Ring)

### Symptome
- Live-Stream friert ein, HLS-Playlist aktualisiert sich nicht.
- Ring-WebRTC bleibt in Verbindungszustand hängen.
- Kameraansicht stockt nach längerer Laufzeit.

### Diagnose
1. `GET /api/monitor/streams` auf Health/Fehler prüfen.
2. `GET /api/admin/logs?type=restart_error` auf Restart-/Fehlerhäufung prüfen.
3. Disk-Füllstand prüfen (`df -h`), besonders bei HLS-/Backup-Verzeichnissen.
4. FFmpeg-/Ring-Prozessstatus und Neustartfrequenz prüfen.
5. Browser-Konsole/Network auf wiederholte 4xx/5xx der Kamera-Endpunkte prüfen.

### Sofortmaßnahmen
1. Betroffenen Stream/Daemon gezielt über Admin-API neu starten.
2. Alte temporäre Stream-Artefakte und nicht mehr benötigte Backups bereinigen.
3. Bei Ring: Session sauber beenden (`.../webrtc/stop`) und neu starten.
4. Danach `GET /api/monitor/streams` und UI-Playback erneut validieren.

### Eskalation
- `SEV-1`, wenn mehrere Kernkameras gleichzeitig ausfallen.
- `SEV-2`, wenn nur Teilmenge betroffen ist, aber reproduzierbar instabil.

## Playbook B: PLC-Ausfall / TwinCAT nicht erreichbar

### Symptome
- Variablen lesen/schreiben fehlgeschlagen.
- `status=disconnected` oder ADS-Route nicht erreichbar.

### Diagnose
1. `GET /api/plc/ads/route/status` und `GET /api/system/status` prüfen.
2. PLC-Konfiguration (`GET /api/plc/config`) gegen Soll abgleichen.
3. Netzwerkpfad/AMS Net ID/Runtime-Port validieren.
4. TwinCAT-Routing-Status auf PLC/Engineering-Seite prüfen.

### Sofortmaßnahmen
1. ADS-Route mit `POST /api/plc/ads/route/test` prüfen.
2. Falls nötig: `POST /api/plc/ads/route/add`, danach erneuter Connect.
3. `POST /api/plc/connect` ausführen und Schreibtest mit sicherer Testvariable.

### Eskalation
- `SEV-1`, wenn Steuerbefehle nicht mehr möglich sind.
- `SEV-2`, wenn nur einzelne PLC-Namespaces betroffen sind.

## Playbook C: Restart-Fehlschlag (App/Daemon)

### Symptome
- Restart-API liefert Fehler oder ohne Wirkung.
- Service bleibt nach Restart im schlechten Zustand.

### Diagnose
1. `GET /api/admin/service/info` prüfen.
2. Audit-Logs filtern: `GET /api/admin/logs?type=restart`.
3. Laufzeitmodus prüfen (native service vs. container).
4. Berechtigungen/Service-Manager-Konfiguration validieren.

### Sofortmaßnahmen
1. Gezielten Daemon-Restart mit validiertem Delay auslösen.
2. Bei Containerbetrieb orchestratorseitigen Neustart prüfen.
3. Wenn Restart scheitert: kontrollierter Service-Neustart auf Hostebene.
4. Ergebnis via `GET /api/system/status` und relevanten Fachendpunkten prüfen.

### Eskalation
- `SEV-1`, wenn Restart weder API-seitig noch hostseitig Wirkung zeigt.
- `SEV-2`, wenn Restart wirkt, Problem aber kurzfristig wiederkehrt.

## Abschluss-Checkliste
1. Incident-Details im Ticket dokumentiert.
2. Reproduktionsschritte und wirksame Gegenmaßnahme festgehalten.
3. Monitoring-/Alerting-Lücke als Folgeaufgabe erfasst.
4. Falls nötig: neues technisches Issue mit Priorität angelegt.
