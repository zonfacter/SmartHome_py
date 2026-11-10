# 17 Milestone Status / Soll-Ist-Abgleich (aktiv)

Dieses Dokument bewertet die bereits beschriebenen Projektziele gegen den aktuellen technischen Stand ab **v4.8.0**.

Es ist **kein Feature-TODO** und **keine neue Produkt-Roadmap**. Ziel ist eine belastbare Standortbestimmung:
- Was war das Zielbild?
- Was ist heute nachweisbar erreicht?
- Wo gibt es nur Teilerreichung?
- Welche Punkte sind noch strukturell offen?

## Bewertungslogik
- `Erreicht`: Ziel ist im aktiven Code und in der aktiven Doku erkennbar umgesetzt.
- `Teilweise erreicht`: Ziel ist grundsätzlich vorhanden, aber mit erkennbaren Lücken, externer Abhängigkeit oder inkonsistenter Tiefe.
- `Offen`: Ziel ist beschrieben, aber noch nicht in belastbarer Form erreicht.

## Zusammenfassung

| Bereich | Zielbild | Status | Kurzbegründung |
|---|---|---|---|
| Web-HMI als zentrale Oberfläche | Eine zentrale steuer- und wartbare Web-Oberfläche für PLC, Kameras, Monitoring, Setup und Admin | Erreicht | Hauptbereiche sind vorhanden, aktiv nutzbar und versioniert dokumentiert |
| Kamera/Ring als First-Class-Use-Case | RTSP- und Ring-Kameras sind kein Nebenpfad, sondern integraler Kern des Gateways | Teilweise erreicht | RTSP, Snapshot, Import, Diagnose und Event-Historie sind da; Ring-Live hängt weiter an externer Ring-Session/WebRTC-Verfügbarkeit |
| Dynamische Räume/Widgets | Widget-basierte, konfigurierbare Seitenstruktur statt starrer Demo-Ansichten | Erreicht | Räume/Pages, Widget-CRUD und persistente UI-Konfiguration sind produktiv im aktiven Stand |
| Einheitliches UI-/Theme-System | Konsistentes Designsystem statt einzelner Sonderflächen | Erreicht | Theme-Tokens, Presets, Widget-Stil und weite Teile der Hauptseiten sind vereinheitlicht |
| Sichere API-/Admin-Steuerung | Kontrollierte Admin-Zugriffe statt offener Steuerpfade | Teilweise erreicht | API-Key-Management ist vorhanden; weitere Secret-/Config-Bereiche sollten langfristig noch vereinheitlicht werden |
| Betriebs- und Incident-Fähigkeit | Fehlerzustände und Störungen sollen nachvollziehbar und mit Recovery versehen sein | Teilweise erreicht | Playbooks, Error-Recovery und Ring-Diagnose wurden deutlich verbessert; Debug-Historie ist noch nicht vollständig konsolidiert |
| Dokumentationsreset mit aktiver Doku | Aktive, verbindliche Doku klar von Legacy trennen | Teilweise erreicht | Aktive Doku-Serie 01-17 existiert; vollständige historische Nachvollziehbarkeit wird erst über Issue #119/#120 hergestellt |
| Bereinigte aktive Projektbasis | Nur aktiv genutzte Dateien sollen die primäre Arbeitsbasis bilden | Offen | Genau dafür existiert Issue #117 mit den Unterpunkten #118 bis #122 |

## Detailbewertung

### 1. Web-HMI als zentrale Steueroberfläche
**Zielbild**
- Ein zentraler Einstieg für Betrieb, Setup, Monitoring, Admin und Feldintegration.

**Ist-Stand**
- Hauptnavigation und Seitenstruktur sind vorhanden.
- Aktive Dokumentation deckt Quickstart, Gateway, API, Betrieb und Architektur ab.
- Versionierung ist mit `v4.8.0` synchronisiert.

**Status**
- `Erreicht`

### 2. Kamera- und Ring-Integration als Kernfunktion
**Zielbild**
- Kameras, Streams, Snapshots, Diagnose und Ring sollen als primärer Use-Case behandelt werden.

**Ist-Stand**
- RTSP/HLS, Snapshot, Diagnose, Scan, PTZ und Kamera-Verwaltung sind aktiv vorhanden.
- Ring kann authentifiziert, importiert und als Kamera dargestellt werden.
- Ring-Ereignisse werden jetzt persistent gespeichert, diagnostiziert und in der UI erklärt.
- Ring-Live ist technisch integriert, aber in der Praxis weiterhin von Ring-Session/WebRTC und externen `406`-Zuständen abhängig.

**Status**
- `Teilweise erreicht`

**Grund für Teilerreichung**
- Der Produktpfad ist implementiert.
- Der Live-Pfad ist aber nicht vollständig unter eigener Kontrolle, weil Ring externe Sessions blockieren kann.

### 3. Widget-/Raum-System statt starrer Demo-Oberfläche
**Zielbild**
- Konfigurierbare Räume und Widgets als tragende UI-Struktur.

**Ist-Stand**
- Widget-CRUD ist aktiv.
- Räume/Pages und persistente Sortierung sind vorhanden.
- Widget-Stil und Theme greifen auf die Standard-Widgets durch.

**Status**
- `Erreicht`

### 4. Vereinheitlichtes Theme- und Bedienkonzept
**Zielbild**
- Ein konsistentes visuelles und operatives System statt gewachsener Einzelzustände.

**Ist-Stand**
- Globale Theme-Tokens, Presets und Widget-Stil-Konfiguration sind aktiv.
- Dashboard, Setup, Admin, Widgets und Kameras wurden auf den Standard gezogen.
- Kamera-Kacheln inklusive Ring-Ereignissen folgen dem gleichen Interaktionsmuster.

**Status**
- `Erreicht`

### 5. Sichere Steuer- und Admin-Pfade
**Zielbild**
- Nachvollziehbare, kontrollierte API- und Admin-Zugriffe.

**Ist-Stand**
- API-Key-Management und Audit-Logging sind aktiv dokumentiert und umgesetzt.
- Ring-Zugangsdaten und Tokens werden lokal verschlüsselt gespeichert.
- Gleichzeitig existieren im Projekt noch weitere Konfigurations- und Credential-Pfade, die perspektivisch auf denselben Sicherheitsstandard gehoben werden sollten.

**Status**
- `Teilweise erreicht`

### 6. Betriebs- und Incident-Reife
**Zielbild**
- Wiederkehrende Störungen sollen im Betrieb erkennbar, beschreibbar und mit klaren Recovery-Schritten versehen sein.

**Ist-Stand**
- Operations Playbook und Error-Recovery-Regeln sind aktiv dokumentiert.
- Ring hat jetzt sichtbare Diagnostik, Hilfe, Health-Status und Timeline.
- Eine vollständige projektweite Debug-Historie ist aber noch nicht konsolidiert.

**Status**
- `Teilweise erreicht`

### 7. Verbindliche aktive Doku statt Dokumentwildwuchs
**Zielbild**
- Klare Trennung zwischen aktiver Doku und Altlasten.

**Ist-Stand**
- Aktive Doku-Serie ist definiert.
- `docs/legacy/` ist bereits ausgelagert.
- Release-/Versions- und Debugging-Historie sind noch nicht vollständig systematisiert.

**Status**
- `Teilweise erreicht`

### 8. Bereinigte aktive Projektbasis
**Zielbild**
- Nur aktiv genutzte Dateien und Pfade sollen die tägliche Arbeitsbasis bilden.

**Ist-Stand**
- Das Ziel ist erkannt und in Issue #117 strukturiert zerlegt.
- Die eigentliche Inventarisierung und Bereinigung steht noch aus.

**Status**
- `Offen`

## Was heute klar erreicht ist
- Web-HMI als zentrale aktive Oberfläche
- Widget-/Raum-System als produktiver Pfad
- modernes, konsistentes Theme-/Widget-System
- aktive API-/Betriebs-/Architekturdoku als verbindliche Basis
- Ring-Event-Persistenz, Ring-Diagnostik und Ring-UX deutlich verbessert

## Was bewusst noch nicht als vollständig erreicht gelten sollte
- vollständig robuste Ring-Live-Funktion unabhängig von Ring-API-/Session-Problemen
- durchgängig vereinheitlichte Secret-/Credential-Strategie für alle Integrationen
- vollständige historische Release-/Debug-Nachvollziehbarkeit
- bereinigte aktive Dateibasis ohne Altlasten

## Nächste Folgerung aus diesem Abgleich
Aus Projektsicht ist die aktuelle Hauptlücke **nicht** ein neues Feature-Zielbild, sondern die strukturelle Konsolidierung:
- aktive Dateibasis inventarisieren
- Release-/Debug-Historie vervollständigen
- Soll/Ist-Abgleich weiter schärfen
- danach die eigentliche Bereinigung in kleinen PRs umsetzen

Verwandte Issues:
- `#117` Projektbereinigung
- `#118` Bereinigung umsetzen
- `#119` Release-/Versionshistorie
- `#120` Debugging-/Fehlerhistorie
- `#121` aktive vs. legacy Dateien
- `#122` Soll/Ist-Abgleich
