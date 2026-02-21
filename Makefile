SHELL := /bin/bash

PYTHON := $(shell if [ -x .venv/bin/python ]; then echo .venv/bin/python; else echo python3; fi)
PIP := $(shell if [ -x .venv/bin/pip ]; then echo .venv/bin/pip; else echo pip3; fi)

.PHONY: help install lint openapi check-api-docs check-openapi test smoke run docker-up docker-down

help:
	@echo "Targets:"
	@echo "  install         Install Python/Node dependencies"
	@echo "  lint            Syntax and static compile checks"
	@echo "  openapi         Regenerate docs/openapi.json from docs/05_api_reference.md"
	@echo "  check-api-docs  Validate docs/05_api_reference.md against code routes"
	@echo "  check-openapi   Validate docs/openapi.json against docs/05_api_reference.md"
	@echo "  test            Full local test suite used in CI smoke job"
	@echo "  smoke           Fast local smoke checks"
	@echo "  run             Start Web-HMI"
	@echo "  docker-up       Build and start docker compose stack"
	@echo "  docker-down     Stop docker compose stack"

install:
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements.txt
	npm ci --omit=dev --ignore-scripts

lint:
	$(PYTHON) -m py_compile start_web_hmi.py module_manager.py import_tpy.py
	$(PYTHON) -m compileall -q modules

openapi:
	$(PYTHON) scripts/generate_openapi_contract.py

check-api-docs:
	$(PYTHON) scripts/check_api_doc_drift.py

check-openapi:
	$(PYTHON) scripts/check_openapi_contract_drift.py

test: lint check-api-docs check-openapi
	$(PYTHON) test_web_manager_fix.py
	$(PYTHON) test_logging_system.py
	$(PYTHON) -m pytest -q test_api_contracts.py
	$(PYTHON) -m pytest -q test_backup_manager.py
	$(PYTHON) -m pytest -q test_integration_core_flows.py
	$(PYTHON) -m pytest -q test_control_auth_security.py
	$(PYTHON) -m pytest -q test_circuit_breakers.py
	$(PYTHON) -m pytest -q test_docker_runtime.py
	$(PYTHON) -m pytest -q test_secret_hygiene.py

smoke: lint check-api-docs check-openapi
	$(PYTHON) -m pytest -q test_api_contracts.py test_integration_core_flows.py

run:
	$(PYTHON) start_web_hmi.py

docker-up:
	docker compose up -d --build

docker-down:
	docker compose down -v
