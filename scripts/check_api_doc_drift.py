#!/usr/bin/env python3
"""Validate that documented API endpoints exist in web_manager routes."""

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOC = ROOT / "docs" / "05_api_reference.md"
SRC = ROOT / "modules" / "gateway" / "web_manager.py"

DOC_PATTERN = re.compile(r"^\s*-\s*`(GET|POST|PUT|DELETE|PATCH)\s+(/api/[^`]+)`\s*$")
ROUTE_PATTERN = re.compile(
    r"@self\.app\.route\('\s*(/api[^']*)\s*'(?:,\s*methods=\[(.*?)\])?"
)
METHOD_PATTERN = re.compile(r"'([A-Z]+)'")


def load_documented() -> set[tuple[str, str]]:
    documented: set[tuple[str, str]] = set()
    for line in DOC.read_text(encoding="utf-8").splitlines():
        m = DOC_PATTERN.match(line)
        if m:
            documented.add((m.group(1), m.group(2)))
    return documented


def load_routes() -> set[tuple[str, str]]:
    routes: set[tuple[str, str]] = set()
    content = SRC.read_text(encoding="utf-8")
    for m in ROUTE_PATTERN.finditer(content):
        path = m.group(1).strip()
        methods_group = m.group(2)
        methods = ["GET"]
        if methods_group:
            methods = METHOD_PATTERN.findall(methods_group) or ["GET"]
        for method in methods:
            routes.add((method, path))
    return routes


def main() -> int:
    documented = load_documented()
    routes = load_routes()
    missing = sorted(documented - routes)

    if missing:
        print("API doc drift detected. Missing in code:")
        for method, path in missing:
            print(f"- {method} {path}")
        return 1

    print(f"API doc check passed ({len(documented)} documented endpoints found in code).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
