#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT_DIR}"

if [[ ! -x "./venv/bin/python" ]]; then
  echo "Missing ./venv/bin/python. Create venv first: python3 -m venv venv"
  exit 1
fi

echo "[1/3] Updating Python lockfile with hashes"
./venv/bin/python -m pip install -q pip-tools
./venv/bin/python -m piptools compile --generate-hashes --resolver=backtracking -o requirements.lock.txt requirements.txt

echo "[2/3] Updating Node lockfile"
npm install --package-lock-only --ignore-scripts

echo "[3/3] Verifying deterministic lock sync"
./venv/bin/python -m piptools compile --quiet --generate-hashes --resolver=backtracking -o requirements.lock.txt requirements.txt
git diff --exit-code requirements.lock.txt package-lock.json >/dev/null

echo "Dependency locks are updated and consistent."
