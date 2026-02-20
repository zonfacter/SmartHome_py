# Reproducible Builds

This project uses lockfiles for deterministic dependency resolution in CI and release builds.

## Python

- Source of truth for direct deps: `requirements.txt`
- Fully locked transitive deps with hashes: `requirements.lock.txt`
- Lockfile is generated and verified in CI with Python `3.13`
- Install command:

```bash
pip install --require-hashes -r requirements.lock.txt
```

## Node

- Direct deps are pinned in `package.json` (no range specifiers)
- Fully locked transitive deps in `package-lock.json`
- Install command:

```bash
npm ci
```

## Update Process

Use the project script:

```bash
./scripts/update_dependency_locks.sh
```

This updates:

- `requirements.lock.txt` via `pip-compile --generate-hashes`
- `package-lock.json` via `npm install --package-lock-only`

## CI Enforcement

- `ci.yml` checks that lockfiles are in sync with their source files.
- Python installs in CI and security scans run from `requirements.lock.txt` with hash checking.

## Release Traceability

`release.yml` publishes:

- source archives
- `SHA256SUMS`
- `DEPENDENCY_MANIFEST.txt` (commit, lockfile checksums, runtime versions)
