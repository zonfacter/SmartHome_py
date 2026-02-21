#!/usr/bin/env python3
"""Validate OpenAPI contract matches canonical API reference."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOC = ROOT / "docs" / "05_api_reference.md"
OPENAPI = ROOT / "docs" / "openapi.json"
DOC_PATTERN = re.compile(r"^\s*-\s*`(GET|POST|PUT|DELETE|PATCH)\s+(/api/[^`]+)`\s*$")
PARAM_PATTERN = re.compile(r"<([a-zA-Z_][a-zA-Z0-9_]*)>")


def normalize(path: str) -> str:
    return PARAM_PATTERN.sub(lambda m: "{" + m.group(1) + "}", path)


def load_doc_endpoints() -> set[tuple[str, str]]:
    endpoints: set[tuple[str, str]] = set()
    for line in DOC.read_text(encoding="utf-8").splitlines():
        m = DOC_PATTERN.match(line)
        if m:
            endpoints.add((m.group(1).lower(), normalize(m.group(2))))
    return endpoints


def load_openapi_endpoints() -> set[tuple[str, str]]:
    data = json.loads(OPENAPI.read_text(encoding="utf-8"))
    paths = data.get("paths", {})
    endpoints: set[tuple[str, str]] = set()
    for path, methods in paths.items():
        if not isinstance(methods, dict):
            continue
        for method in methods.keys():
            m = str(method).lower()
            if m in {"get", "post", "put", "delete", "patch"}:
                endpoints.add((m, str(path)))
    return endpoints


def main() -> int:
    if not OPENAPI.exists():
        print("OpenAPI contract missing: docs/openapi.json")
        return 1

    doc_eps = load_doc_endpoints()
    openapi_eps = load_openapi_endpoints()

    missing = sorted(doc_eps - openapi_eps)
    extra = sorted(openapi_eps - doc_eps)

    if missing:
        print("OpenAPI drift: documented endpoints missing from docs/openapi.json")
        for method, path in missing:
            print(f"- {method.upper()} {path}")
    if extra:
        print("OpenAPI drift: docs/openapi.json contains undocumented endpoints")
        for method, path in extra:
            print(f"- {method.upper()} {path}")

    if missing or extra:
        return 1

    print(f"OpenAPI contract check passed ({len(doc_eps)} operations aligned).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
