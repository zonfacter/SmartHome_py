# 16 Frontend Load Performance Strategy (verbindlich)

Dieses Dokument beschreibt die aktuelle Strategie zur Reduktion der Initial-Ladezeit.

## Maßnahmen
- `defer` für lokale JS-Bundles (`socket_handler.js`, `variable-manager.js`, `app.js`)
- nicht-kritische Boot-Aufgaben via `requestIdleCallback`:
- Socket-Init
- Systemstatus-Laden
- opt-in Dev-Test-Szenarien
- Dev-Testbundle (`test_scenarios.js`) wird nicht mehr standardmäßig geladen

## Code-Splitting-Ansatz
- risikoreiche/diagnostische Funktionen werden opt-in nachgeladen
- Heavy-Seitenlogik bleibt page-getrieben (Load on navigation)

## Messung (Before/After)
1. Browser DevTools > Performance/Lighthouse (Desktop + Mobile Profil)
2. Kennzahlen erfassen:
- FCP (First Contentful Paint)
- LCP (Largest Contentful Paint)
- TTI/INP
3. Vergleich unter identischen Bedingungen mit/ohne Warm-Cache

## Erwarteter Effekt
- schnellerer First-Paint durch verschobene Non-Critical Work
- weniger JS-Kosten im initialen Parse/Execute-Pfad
- bessere Reaktionsfähigkeit direkt nach Seitenaufbau
