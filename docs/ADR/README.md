# ADR Process (verbindlich)

ADR = Architecture Decision Record.

## Zweck
- Technische Entscheidungen nachvollziehbar und auditierbar dokumentieren.
- Kontext, Alternativen und Konsequenzen langfristig auffindbar halten.

## Ablage und Nummerierung
- Ablageort: `docs/ADR/`
- Dateiformat: `NNNN-kurzer-titel.md`
- Nummern sind fortlaufend und werden nicht wiederverwendet.

## Statuswerte
- `proposed`: in Diskussion
- `accepted`: beschlossen
- `superseded`: durch neue ADR ersetzt
- `deprecated`: nicht mehr gültig

## Workflow
1. ADR-Entwurf aus `docs/ADR/0000-template.md` erstellen.
2. Kontext, Optionen und Trade-offs nachvollziehbar ausfüllen.
3. Review im PR einholen (Architektur/Owner + betroffene Module).
4. Bei Merge Status auf `accepted` setzen.
5. Bei Folgeentscheidungen neue ADR erstellen und alte per `Superseded by` verlinken.

## Mindestkriterien
- Problem klar beschrieben
- mindestens zwei Optionen mit Vor-/Nachteilen
- Entscheidung und Konsequenzen explizit
- Migrations-/Betriebsfolgen genannt
