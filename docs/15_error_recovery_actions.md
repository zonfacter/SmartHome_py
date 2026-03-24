# 15 Error Recovery, Debugging und Fehlerhistorie (verbindlich)

Dieses Dokument bündelt wiederkehrende Problemklassen aus Betrieb, Support und früheren Fixes.
Es ergänzt das `07_operations_playbook.md` um eine technische Referenz für typische Symptome,
wahrscheinliche Ursachen, praktikable Workarounds und den aktuellen Status der bekannten Fehlerbilder.
Versionsbezogene Referenzen zeigen auf [`../CHANGELOG.md`](../CHANGELOG.md).

## Zielbild
- wiederkehrende Incidents schneller einordnen
- historische Fehler von weiterhin relevanten Betriebsrisiken trennen
- Recovery-Aktionen für UI, Betrieb und Support konsistent halten

## Recovery-Muster
- `Erneut versuchen`: gleiche Aktion erneut ausführen, wenn der Fehler transient ist
- `Gezielter Neustart`: nur betroffenen Stream/Daemon/API-Pfad neu initialisieren
- `Zu Setup`: Nutzer auf die passende Konfigurationsseite führen
- `Re-Auth`: Credentials/Token bewusst erneuern statt wiederholt blind neu anzustoßen

## Problemklasse Ring

| Problemfeld | Typische Symptome | Wahrscheinliche Ursachen | Workaround / Recovery | Fix- und Relevanzstatus |
|---|---|---|---|---|
| Ring-Auth / `406` | Session-Aufbau scheitert, Live-Verbindung bleibt hängen, Re-Auth-Hinweis in UI | Ring lehnt Session-Validierung mit ungeeignetem User-Agent ab | Ring-Session sauber beenden, Auth erneut starten, Diagnosehinweise auswerten | **Weiterhin relevant.** Seit `v4.8.0` helfen zusätzliche Diagnosehinweise, UI-Hilfe und Fallback-Verhalten ([`../CHANGELOG.md`](../CHANGELOG.md)). |
| Ring-2FA | Anmeldung fordert zusätzlichen Code, API liefert `requires_2fa` | Ring erzwingt OTP-Validierung | OTP erneut eingeben und Auth mit 2FA abschließen | **Weiterhin relevant, aber abgefedert.** Recovery-Pfad ist fest eingeplant; kein rein historischer Fehler. |
| Ring-Token / Re-Auth | gespeicherte Anmeldung funktioniert nach Neustart nicht mehr, lokale Credentials wirken ungültig | abgelaufene oder nicht mehr entschlüsselbare Tokens, geänderte lokale Schlüsselbasis | kontrollierte Re-Auth auslösen statt alte Tokens wiederzuverwenden | **Teilweise historisch.** Seit `v4.8.0` sind lokale Zugangsdaten verschlüsselt gespeichert; Re-Auth bleibt operativ relevant ([`../CHANGELOG.md`](../CHANGELOG.md)). |
| Ring-Event-Historie fehlt | Event-Liste ist nach Neustart leer oder unvollständig | frühere rein flüchtige Speicherung im Speicher | bei Verdacht Backend/Store prüfen und Ring-Health mit Zeitstempeln kontrollieren | **Historisch weitgehend behoben.** Seit `v4.8.0` gibt es einen persistenten Ring-Event-Speicher ([`../CHANGELOG.md`](../CHANGELOG.md)). |

## Problemklasse Streams

| Problemfeld | Typische Symptome | Wahrscheinliche Ursachen | Workaround / Recovery | Fix- und Relevanzstatus |
|---|---|---|---|---|
| HLS-/RTSP-Stream hängt | Playlist aktualisiert sich nicht, Kamera friert ein, UI stockt | FFmpeg-Prozess hängt oder beendet sich, RTSP-Quelle instabil, HLS-Artefakte blockieren Folgestarts | betroffenen Stream gezielt stoppen/starten, temporäre Artefakte bereinigen, `/api/monitor/streams` prüfen | **Weiterhin relevant.** Ein eigenes Stream-Playbook in `07_operations_playbook.md` beschreibt die Sofortmaßnahmen. |
| Stream-Stottern | kurze Bildaussetzer, Ring- oder Kameraansicht wirkt unruhig | Segment-Generierung verzögert, aggressive Segment-Löschung, Lastspitzen | Stream neu initialisieren, `GET /api/monitor/slo` und `GET /api/monitor/streams` prüfen, Last und Disk-Füllstand kontrollieren | **Teilweise historisch, aber noch relevant.** `v4.6.1` reduzierte häufige Ring-Stotterfälle; das Restrisiko bleibt setup-abhängig ([`../CHANGELOG.md`](../CHANGELOG.md)). |
| Wiederholte Startfehler | Stream startet nach mehreren Versuchen nicht mehr | wiederholte Initialisierungsfehler öffnen den Schutzmechanismus | Recovery-Fenster abwarten oder Ursache der Startfehler zuerst beheben, dann erneut starten | **Weiterhin relevant, aber kontrolliert.** Die Circuit-Breaker-Logik begrenzt Restart-Schleifen. |
| Restart ohne Wirkung | API-Restart endet formal erfolgreich, Dienst bleibt aber in schlechtem Zustand | Prozesszustand ist bereits inkonsistent oder Host-/Container-Restart greift nicht sauber | Daemon gezielt hostseitig bzw. orchestratorseitig neu starten und Status-Endpunkte gegenprüfen | **Weiterhin relevant.** Das dazugehörige Restart-Playbook steht in `07_operations_playbook.md`. |

## Problemklasse Kamera-Snapshots

| Problemfeld | Typische Symptome | Wahrscheinliche Ursachen | Workaround / Recovery | Fix- und Relevanzstatus |
|---|---|---|---|---|
| Ring-Snapshot fehlt | leere oder fehlerhafte Kachel, Snapshot wird nicht geladen | Snapshot-Timeout, Ring-API liefert kein Bild rechtzeitig | Snapshot erneut anfordern, Ring-Status und Auth prüfen, bei Bedarf Re-Auth | **Weiterhin relevant, aber verbessert.** Seit `v4.8.0` wird der Fehler sichtbar statt still leer dargestellt ([`../CHANGELOG.md`](../CHANGELOG.md)). |
| Snapshot ist veraltet | Bild wirkt alt, Nutzer kann Aktualität schlecht einschätzen | Quelle liefert nicht rechtzeitig frische Daten, letztes Bild bleibt sichtbar | Live-Ansicht oder neuen Snapshot anstoßen, Zeitstempel im Overlay beachten | **Überwiegend historisch.** Seit `v4.6.1` hilft ein Freshness-Overlay bei der Einordnung ([`../CHANGELOG.md`](../CHANGELOG.md)). |
| ONVIF-/PTZ-Snapshot-Probleme | Kamera-Diagnose findet Snapshot nicht, PTZ/Snapshot-Aufruf läuft ins Leere | fehlende ONVIF-Abhängigkeiten, ungültige Credentials oder Endpunkte | ONVIF-Voraussetzungen, Credentials und konfigurierte Kamera-Endpunkte prüfen | **Historisch reduziert, operativ weiter relevant.** `v4.6.2` stabilisierte Voraussetzungen in Doku und Runtime; [`03_camera_setup.md`](03_camera_setup.md) nennt ONVIF-Port und valide Credentials explizit. |
| Segment-/Dateifehler rund um Kamera-Ansicht | Snapshot oder Stream-Teilabrufe liefern 404/fehlende Artefakte | Segment wurde vor Client-Abruf gelöscht oder Pfade sind inkonsistent | betroffene Kameraansicht neu laden, Streamstatus und Storage/Disk prüfen | **Weiterhin relevant, aber mitigiert.** Stream-Tuning reduziert solche Ausfälle, beseitigt sie jedoch nicht vollständig. |

## Problemklasse API / Auth

| Problemfeld | Typische Symptome | Wahrscheinliche Ursachen | Workaround / Recovery | Fix- und Relevanzstatus |
|---|---|---|---|---|
| `401 Unauthorized` / fehlender Zugriff | Steuer- oder Admin-Endpunkte antworten mit `401` oder `403` | fehlender/ungültiger `X-API-Key`, Bearer-Token ungültig, Request nicht als lokal/vertraut eingestuft | Header und Rollen prüfen, Managed Key erneuern oder lokalen Trusted-Pfad nur gezielt nutzen | **Weiterhin relevant.** Seit `v4.6.2` gibt es Managed API Keys und Audit-Logging ([`../CHANGELOG.md`](../CHANGELOG.md)). |
| API/Auth wirkt instabil nach Änderung | Requests funktionieren lokal, aber remote oder nach Konfigurationswechsel nicht mehr | Policy- oder Whitelist-Änderung, inkonsistente Key-Verwaltung | zuerst den betroffenen Key-/Origin-Pfad prüfen, dann Audit-Logs und Systemstatus kontrollieren | **Weiterhin relevant.** Das ist ein wiederkehrendes Support-Thema, kein rein historischer Defekt. |
| Secrets/Tokens in Logs oder Dateien | sensible Daten tauchen in Fehlersituationen unerwartet auf | unsaubere Speicherung oder Logging-Pfade | betroffenen Flow stoppen, Secret rotieren und Log-/Dateiablage prüfen | **Historisch stark verbessert.** Secret-Hygiene ist in [`../SECURITY.md`](../SECURITY.md) verankert; verschlüsselte Ring-Speicherung ergänzt den technischen Schutz ([`../CHANGELOG.md`](../CHANGELOG.md)). |
| Rate-Limit-/Schutzmechanismen greifen anders als erwartet | Clients rechnen mit `429` oder abgestuftem Schutz, Verhalten unterscheidet sich je nach Endpoint | unterschiedliche Schutzpfade, Auth-/Control-Kontext oder abweichende Erwartung aus früheren Incidents | keine stillschweigende Annahme treffen; Verhalten gegen aktuelle Laufzeit und betroffenen Endpoint prüfen | **Weiterhin relevant.** Das ist ein Diagnosefeld für Betrieb und Support, nicht nur ein historischer Bug. |

## Historisch vs. weiterhin relevant

### Überwiegend historisch / weitgehend behoben
- nicht persistente Ring-Event-Historie vor `v4.8.0`
- fehlende Sichtbarkeit bei Snapshot-Fehlern vor `v4.8.0`
- fehlende Freshness-Anzeige bei Ring-Snapshots vor `v4.6.1`
- frühere ONVIF-/PTZ-Stabilitätsprobleme vor `v4.6.2`

### Weiterhin operativ relevant
- Ring-Re-Auth, 2FA und User-Agent-/Session-Themen
- Stream-Hänger, Restart-Probleme und Stottern unter Last
- Kamera-Snapshot-Timeouts oder segmentbedingte Folgefehler
- API-/Auth-Probleme durch ungültige Keys, Policy- oder Origin-Mismatches

## Aktuell abgedeckte Recovery-Flüsse
- Laden System-Status: Fehler-Toast mit `Erneut versuchen` und `Zu Setup`
- PLC verbinden/trennen: Fehler-Toast mit Recovery-Aktionen
- Ring: Re-Auth, 2FA und Diagnosehinweise
- Streams/Kameras: gezielter Restart statt vollständigem Reboot

## Erweiterungsregel
Neue riskante Flows müssen vor Merge ein Recovery-Muster erhalten und bei
wiederkehrenden Incidents zusätzlich in diese Fehlerhistorie eingeordnet werden.
