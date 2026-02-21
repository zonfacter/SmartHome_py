# 15 Error States with Recovery Actions (verbindlich)

Dieses Dokument beschreibt, wie Fehlerzustände mit klaren nächsten Schritten dargestellt werden.

## Prinzip
Jeder relevante Laufzeitfehler soll mindestens eine direkte Recovery-Option anbieten.

## Recovery-Muster
- `Erneut versuchen`: gleiche Aktion erneut ausführen
- `Zu Setup`: Nutzer auf passende Konfigurationsseite führen

## Aktuell abgedeckte Flüsse
- Laden System-Status:
- Fehler-Toast mit `Erneut versuchen` und `Zu Setup`
- PLC verbinden/trennen:
- Fehler-Toast mit Recovery-Aktionen

## Erweiterungsregel
Neue riskante Flows müssen vor Merge ein Recovery-Muster implementieren.
