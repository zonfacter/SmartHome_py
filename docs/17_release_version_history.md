# 17 Release- und Versionshistorie (verbindlich)

Diese Uebersicht konsolidiert die technisch relevanten Versionsmarker des Repositorys:
Releases, Tags, Branch-Bezug, groessere Umbauten und die Frage, welche Dokumentation ab welcher Version verbindlich ist.

## Verbindliche Marker fuer Release- und Versionsstand

| Marker | Technische Bedeutung | Quelle |
|---|---|---|
| GitHub-Tag `v*` | offizieller Release-Marker fuer veroeffentlichte Artefakte | `.github/workflows/release.yml` |
| GitHub Release | publizierte Release-Notizen und Artefakte zum Tag | GitHub Releases |
| `VERSION` | aktueller Versionsstand des aktiven Arbeitsbaums | `VERSION` |
| `CHANGELOG.md` | aktiver Changelog der aktuellen Release-Linie ab `v4.6.2` | `CHANGELOG.md` |
| `docs/README.md` + aktive `docs/01-17_*.md` | verbindliche Betriebs- und Entwicklungsdoku ab `v4.8.0` | `docs/README.md` |
| `docs/legacy/` | archivierte, historische Doku; nicht automatisch gegen aktuellen Code validiert | `docs/LEGACY.md` |

Hinweis: Shallow Clones koennen lokale Tags oder aeltere Branches nicht enthalten. Fuer Audits ist deshalb GitHub (Tags/Releases) die massgebliche Referenz.

## Release-Linien und groessere Umbauten

| Phase / Versionen | Technische Einordnung | Verbindliche Doku fuer diese Phase |
|---|---|---|
| `<= v3.1.0` | aeltere TwinCAT-Smart-Home-Linie vor dem Web-HMI-Neustart | GitHub Release `v3.1.0`, `docs/legacy/README_ROOT_pre_v4.6.2.md`, `docs/legacy/UPGRADE_GUIDE_v3.1.0.md` |
| `v4.6.0` | technischer Neustart/Neuaufbau der Web-HMI-/Edge-OS-Linie; Release-Notizen enthalten bereits Planungs- und Umbauanteile | GitHub Release `v4.6.0`, `docs/legacy/CHANGELOG.md`, `docs/legacy/CHANGELOG_ROOT_pre_v4.6.2.md`, `docs/legacy/RELEASE-NOTES-V5.md` |
| `v5.0.0`, `v5.1.0` | historisch vorhandene, aber laut GitHub Releases falsch versionierte Legacy-Releases; sie sind ausdruecklich **nicht** der gueltige aktuelle Entwicklungsstand | GitHub Releases `v5.0.0` und `v5.1.0`; nur als historische Referenz verwenden |
| `v4.6.1` bis `v4.6.2` | Stabilisierung nach dem Neustart; ab `v4.6.2` beginnt der aktive Root-Changelog | GitHub Releases `v4.6.1`/`v4.6.2`, `CHANGELOG.md`, zusaetzlich historische Details in `docs/legacy/CHANGELOG.md` |
| `v4.7.x` | Ausbau der neuen Web-HMI-Linie und gleichzeitige Bereinigung/Archivierung der Doku | GitHub Release `v4.7.0`, `docs/legacy/README_v4.7.0.md`, `docs/legacy/CHANGELOG.md` |
| `>= v4.8.0` | aktuelle aktive Release-Linie mit bereinigter, nummerierter Dokumentation und tag-basiertem Release-Prozess | `README.md`, `CHANGELOG.md`, `docs/README.md`, `docs/01_quickstart.md` bis `docs/17_release_version_history.md`, `docs/RELEASE_VERIFICATION.md` |

## Welche Doku ab welcher Version verbindlich ist

| Versionsbereich | Verbindliche Doku heute | Einordnung |
|---|---|---|
| `>= v4.8.0` | `README.md`, `CHANGELOG.md`, `docs/README.md`, aktive `docs/01-17_*.md`, `docs/openapi.json`, `docs/RELEASE_VERIFICATION.md` | aktuelle, gepflegte und fuer Betrieb/Weiterentwicklung massgebliche Doku |
| `v4.6.2` bis `v4.7.x` | zugehoerige GitHub Releases plus `docs/legacy/CHANGELOG.md` und `docs/legacy/README_v4.7.0.md` | historische Betriebs- und Umbauphase nach dem Neustart; nicht mehr aktive Standard-Doku |
| `v4.6.0`, `v5.0.0`, `v5.1.0` | GitHub Releases sowie die einschlaegigen Legacy-Dokumente in `docs/legacy/` | nur fuer Historie/Herleitung verwenden, nicht als aktuelle Betriebsgrundlage |
| `<= v3.1.0` | Releases/Tags und Legacy-Dokumente unter `docs/legacy/` | Altbestand vor der aktuellen Web-HMI-Linie |

## Branches, Tags und Release-Mechanik

- Offizielle Releases werden aus Git-Tags `v*` erzeugt.
- Die Release-Pipeline ist in `.github/workflows/release.yml` definiert und publiziert Artefakte samt Checksums und Attestations.
- Ein eigener Release-Branch ist derzeit nicht dokumentiert; die nachvollziehbaren offiziellen Marker sind daher Tags und GitHub Releases.
- Arbeitsstaende entstehen auf Themen-/PR-Branches (z. B. `copilot/*`), waehrend Releases ueber Tags verankert werden.

## Identifizierte Luecken und Inkonsistenzen

1. **Zwei unterschiedliche Schnittpunkte fuer "aktuell":**
   - `CHANGELOG.md` beginnt ab `v4.6.2`.
   - Die nummerierte aktive Doku in `docs/` ist erst ab `v4.8.0` ausdruecklich verbindlich.
2. **Historisch falsch versionierte Releases `v5.0.0` und `v5.1.0`:**
   - Diese Releases existieren offiziell auf GitHub, sind dort aber selbst als Legacy-/Fehlversionierung markiert.
3. **Tag-/Release-Historie ist nicht vollstaendig aus einem Shallow Clone rekonstruierbar:**
   - Lokale Audits muessen fuer Tags/Releases ggf. explizit nachladen oder GitHub als Referenz nutzen.
4. **GitHub-Tag-Pruefung erforderlich:**
   - Bei der Audit-Sichtung zeigen `v4.7.0` und `v4.8.0` derzeit denselben GitHub-Tag-SHA. Das sollte separat verifiziert werden, damit Release- und Tag-Historie eindeutig bleibt.

## Praktische Regel fuer kuenftige Pflege

- Neue Releases immer ueber `v*`-Tag + GitHub Release veroeffentlichen.
- `VERSION`, `CHANGELOG.md`, `README.md` und diese Historienseite gemeinsam aktualisieren.
- Alles, was nicht mehr fuer die aktuelle Release-Linie verbindlich ist, nach `docs/legacy/` verschieben statt im aktiven Pfad doppelt zu pflegen.
