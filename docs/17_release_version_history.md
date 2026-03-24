# 17 Release- und Versionshistorie (verbindlich)

Diese Übersicht konsolidiert die technisch relevanten Versionsmarker des Repositorys:
Releases, Tags, Branch-Bezug, größere Umbauten und die Frage, welche Dokumentation ab welcher Version verbindlich ist.

## Verbindliche Marker für Release- und Versionsstand

| Marker | Technische Bedeutung | Quelle |
|---|---|---|
| GitHub-Tag `v*` | offizieller Release-Marker für veröffentlichte Artefakte | `.github/workflows/release.yml` |
| GitHub Release | publizierte Release-Notizen und Artefakte zum Tag | GitHub Releases |
| `VERSION` | aktueller Versionsstand des aktiven Arbeitsbaums | `VERSION` |
| `CHANGELOG.md` | aktiver Changelog der aktuellen Release-Linie ab `v4.6.2` | `CHANGELOG.md` |
| `docs/README.md` + aktive `docs/01-17_*.md` | verbindliche Betriebs- und Entwicklungsdoku ab `v4.8.0` | `docs/README.md` |
| `docs/legacy/` | archivierte, historische Doku; nicht automatisch gegen aktuellen Code validiert | `docs/LEGACY.md` |

Hinweis: Shallow Clones können lokale Tags oder ältere Branches nicht enthalten. Für Audits ist deshalb GitHub (Tags/Releases) die maßgebliche Referenz.

## Release-Linien und größere Umbauten

| Phase / Versionen | Technische Einordnung | Verbindliche Doku für diese Phase |
|---|---|---|
| `<= v3.1.0` | ältere TwinCAT-Smart-Home-Linie vor dem Web-HMI-Neustart | GitHub Release `v3.1.0`, `docs/legacy/README_ROOT_pre_v4.6.2.md`, `docs/legacy/UPGRADE_GUIDE_v3.1.0.md` |
| `v4.6.0` | technischer Neustart/Neuaufbau der Web-HMI-/Edge-OS-Linie; Release-Notizen enthalten bereits Planungs- und Umbauanteile | GitHub Release `v4.6.0`, `docs/legacy/CHANGELOG.md`, `docs/legacy/CHANGELOG_ROOT_pre_v4.6.2.md`, `docs/legacy/RELEASE-NOTES-V5.md` |
| `v5.0.0`, `v5.1.0` | historisch vorhandene, aber laut GitHub Releases falsch versionierte Legacy-Releases; sie sind ausdrücklich **nicht** der gültige aktuelle Entwicklungsstand | GitHub Releases `v5.0.0` und `v5.1.0`; nur als historische Referenz verwenden |
| `v4.6.1` bis `v4.6.2` | Stabilisierung nach dem Neustart; ab `v4.6.2` beginnt der aktive Root-Changelog | GitHub Releases `v4.6.1`/`v4.6.2`, `CHANGELOG.md`, zusätzlich historische Details in `docs/legacy/CHANGELOG.md` |
| `v4.7.x` | Ausbau der neuen Web-HMI-Linie und gleichzeitige Bereinigung/Archivierung der Doku | GitHub Release `v4.7.0`, `docs/legacy/README_v4.7.0.md`, `docs/legacy/CHANGELOG.md` |
| `>= v4.8.0` | aktuelle aktive Release-Linie mit bereinigter, nummerierter Dokumentation und tag-basiertem Release-Prozess | `README.md`, `CHANGELOG.md`, `docs/README.md`, `docs/01_quickstart.md` bis `docs/17_release_version_history.md`, `docs/RELEASE_VERIFICATION.md` |

## Welche Doku ab welcher Version verbindlich ist

| Versionsbereich | Verbindliche Doku heute | Einordnung |
|---|---|---|
| `>= v4.8.0` | `README.md`, `CHANGELOG.md`, `docs/README.md`, aktive `docs/01-17_*.md`, `docs/openapi.json`, `docs/RELEASE_VERIFICATION.md` | aktuelle, gepflegte und für Betrieb/Weiterentwicklung maßgebliche Doku |
| `v4.6.2` bis `v4.7.x` | zugehörige GitHub Releases plus `docs/legacy/CHANGELOG.md` und `docs/legacy/README_v4.7.0.md` | historische Betriebs- und Umbauphase nach dem Neustart; nicht mehr aktive Standard-Doku |
| `v4.6.0`, `v5.0.0`, `v5.1.0` | GitHub Releases sowie die einschlägigen Legacy-Dokumente in `docs/legacy/` | nur für Historie/Herleitung verwenden, nicht als aktuelle Betriebsgrundlage |
| `<= v3.1.0` | Releases/Tags und Legacy-Dokumente unter `docs/legacy/` | Altbestand vor der aktuellen Web-HMI-Linie |

## Branches, Tags und Release-Mechanik

- Offizielle Releases werden aus Git-Tags `v*` erzeugt.
- Die Release-Pipeline ist in `.github/workflows/release.yml` definiert und publiziert Artefakte samt Checksums und Attestations.
- Ein eigener Release-Branch ist derzeit nicht dokumentiert; die nachvollziehbaren offiziellen Marker sind daher Tags und GitHub Releases.
- Arbeitsstände entstehen auf Themen-/PR-Branches (z. B. `copilot/*`), während Releases über Tags verankert werden.

## Identifizierte Lücken und Inkonsistenzen

1. **Zwei unterschiedliche Schnittpunkte für "aktuell":**
   - `CHANGELOG.md` beginnt ab `v4.6.2`.
   - Die nummerierte aktive Doku in `docs/` ist erst ab `v4.8.0` ausdrücklich verbindlich.
2. **Historisch falsch versionierte Releases `v5.0.0` und `v5.1.0`:**
   - Diese Releases existieren offiziell auf GitHub, sind dort aber selbst als Legacy-/Fehlversionierung markiert.
3. **Tag-/Release-Historie ist nicht vollständig aus einem Shallow Clone rekonstruierbar:**
   - Lokale Audits müssen für Tags/Releases ggf. explizit nachladen oder GitHub als Referenz nutzen.
4. **GitHub-Tag-Prüfung erforderlich:**
   - Bei der Audit-Sichtung zeigen `v4.7.0` und `v4.8.0` derzeit denselben GitHub-Tag-SHA. Das sollte separat verifiziert werden, damit Release- und Tag-Historie eindeutig bleibt.

## Praktische Regel für künftige Pflege

- Neue Releases immer über `v*`-Tag + GitHub Release veröffentlichen.
- `VERSION`, `CHANGELOG.md`, `README.md` und diese Historienseite gemeinsam aktualisieren.
- Alles, was nicht mehr für die aktuelle Release-Linie verbindlich ist, nach `docs/legacy/` verschieben statt im aktiven Pfad doppelt zu pflegen.
