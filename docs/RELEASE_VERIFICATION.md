# Release Verification

Dieser Ablauf prüft vor dem Einsatz, dass ein Release-Artefakt authentisch und unverändert ist.

## Voraussetzungen

- `gh` (GitHub CLI) installiert und authentifiziert
- `sha256sum` verfügbar

## 1. Artefakte und Checksums herunterladen

Beispiel für Tag `v1.2.3`:

```bash
gh release download v1.2.3 -D release-v1.2.3
cd release-v1.2.3
```

## 2. Integrität via SHA256 prüfen

```bash
sha256sum -c SHA256SUMS
```

Erwartung: alle Einträge melden `OK`.

## 3. Build-Provenance Attestation prüfen

```bash
gh attestation verify smarthome-web-v1.2.3.tar.gz \
  --repo zonfacter/SmartHome_py
```

Optional auch für ZIP:

```bash
gh attestation verify smarthome-web-v1.2.3.zip \
  --repo zonfacter/SmartHome_py
```

## 4. Nur verifizierte Artefakte deployen

Deploy nur ausführen, wenn:

- Checksum-Prüfung erfolgreich ist
- Attestation-Prüfung erfolgreich ist
