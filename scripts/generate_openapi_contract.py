#!/usr/bin/env python3
"""Generate OpenAPI contract from canonical API reference."""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOC = ROOT / "docs" / "05_api_reference.md"
OUT = ROOT / "docs" / "openapi.json"
PATTERN = re.compile(r"^\s*-\s*`(GET|POST|PUT|DELETE|PATCH)\s+(/api/[^`]+)`\s*$")
PARAM_PATTERN = re.compile(r"<([a-zA-Z_][a-zA-Z0-9_]*)>")


def to_openapi_path(path: str) -> str:
    return PARAM_PATTERN.sub(lambda m: "{" + m.group(1) + "}", path)


def operation_id(method: str, path: str) -> str:
    parts = [p for p in re.split(r"[^a-zA-Z0-9]+", path) if p]
    base = "_".join(parts)
    return f"{method.lower()}_{base}"[:120]


def discover_endpoints() -> list[tuple[str, str]]:
    endpoints: list[tuple[str, str]] = []
    for line in DOC.read_text(encoding="utf-8").splitlines():
        m = PATTERN.match(line)
        if m:
            endpoints.append((m.group(1), to_openapi_path(m.group(2))))
    return sorted(set(endpoints), key=lambda x: (x[1], x[0]))


def build_operation(method: str, path: str) -> dict:
    params = []
    for name in PARAM_PATTERN.findall(path.replace("{", "<").replace("}", ">")):
        params.append({
            "name": name,
            "in": "path",
            "required": True,
            "schema": {"type": "string"},
        })

    op: dict = {
        "operationId": operation_id(method, path),
        "responses": {
            "200": {
                "description": "Successful response",
                "content": {
                    "application/json": {
                        "schema": {"$ref": "#/components/schemas/GenericJson"}
                    }
                },
            },
            "400": {"$ref": "#/components/responses/BadRequest"},
            "401": {"$ref": "#/components/responses/Unauthorized"},
            "403": {"$ref": "#/components/responses/Forbidden"},
            "404": {"$ref": "#/components/responses/NotFound"},
            "429": {"$ref": "#/components/responses/RateLimited"},
            "500": {"$ref": "#/components/responses/InternalError"},
        },
    }
    if params:
        op["parameters"] = params
    if method in {"POST", "PUT", "PATCH"}:
        op["requestBody"] = {
            "required": False,
            "content": {
                "application/json": {
                    "schema": {"$ref": "#/components/schemas/GenericJson"}
                }
            },
        }
    return op


def main() -> int:
    endpoints = discover_endpoints()
    paths: dict[str, dict] = {}
    for method, path in endpoints:
        item = paths.setdefault(path, {})
        item[method.lower()] = build_operation(method, path)

    spec = {
        "openapi": "3.1.0",
        "info": {
            "title": "SmartHome Gateway API",
            "version": "1.0.0",
            "description": "Contract-first HTTP API specification for external integrations.",
        },
        "servers": [{"url": "http://localhost:5000", "description": "Local default"}],
        "security": [{"ApiKeyAuth": []}, {"BearerAuth": []}],
        "paths": paths,
        "components": {
            "securitySchemes": {
                "ApiKeyAuth": {"type": "apiKey", "in": "header", "name": "X-API-Key"},
                "BearerAuth": {"type": "http", "scheme": "bearer"},
            },
            "schemas": {
                "GenericJson": {
                    "oneOf": [
                        {"type": "object", "additionalProperties": True},
                        {"type": "array", "items": {"type": "object", "additionalProperties": True}},
                    ]
                },
                "ErrorResponse": {
                    "type": "object",
                    "properties": {
                        "success": {"type": "boolean"},
                        "status": {"type": "string"},
                        "error": {"type": "string"},
                        "message": {"type": "string"},
                        "error_class": {"type": "string"},
                    },
                    "additionalProperties": True,
                },
            },
            "responses": {
                "BadRequest": {
                    "description": "Invalid request",
                    "content": {"application/json": {"schema": {"$ref": "#/components/schemas/ErrorResponse"}}},
                },
                "Unauthorized": {
                    "description": "Authentication required",
                    "content": {"application/json": {"schema": {"$ref": "#/components/schemas/ErrorResponse"}}},
                },
                "Forbidden": {
                    "description": "Forbidden",
                    "content": {"application/json": {"schema": {"$ref": "#/components/schemas/ErrorResponse"}}},
                },
                "NotFound": {
                    "description": "Resource not found",
                    "content": {"application/json": {"schema": {"$ref": "#/components/schemas/ErrorResponse"}}},
                },
                "RateLimited": {
                    "description": "Rate limit exceeded",
                    "content": {"application/json": {"schema": {"$ref": "#/components/schemas/ErrorResponse"}}},
                },
                "InternalError": {
                    "description": "Internal server error",
                    "content": {"application/json": {"schema": {"$ref": "#/components/schemas/ErrorResponse"}}},
                },
            },
        },
    }

    OUT.write_text(json.dumps(spec, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    print(f"OpenAPI contract generated: {OUT}")
    print(f"Documented operations: {len(endpoints)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
