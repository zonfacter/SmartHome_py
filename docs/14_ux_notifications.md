# 14 UX Notification Strategy (verbindlich)

Dieses Dokument definiert die konsistente Notification-Strategie im Frontend.

## Ziele
- einheitliches Feedback statt verstreuter Browser-`alert()`-Dialoge
- nicht-blockierende Nutzerführung
- klare Semantik nach Schweregrad

## Notification-Typen
- `info`: neutraler Zustand/Hinweis
- `success`: erfolgreich abgeschlossene Aktion
- `error`: Fehlerzustand mit optionaler Recovery-Aktion

## Implementierung
- zentral über `showToast(message, { level, duration, actions })`
- Container: `#app-toast-container`
- max. 2 Aktionen pro Toast (z. B. Retry, Navigation)

## UX-Regeln
- keine modalen Alerts für normale Betriebsfehler
- Erfolgsmeldungen kurz und selbstschließend
- Fehler länger sichtbar und mit Recovery-Buttons
