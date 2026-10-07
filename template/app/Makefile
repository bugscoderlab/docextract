PYTHON ?= python3
VENV := api/.venv
VPIP := $(VENV)/bin/pip

.PHONY: bootstrap install venv dev api web migrate

bootstrap: install ## install the engine, the UI, and app deps

install: venv
	$(VPIP) install -r api/requirements.txt
	pnpm -C frontend install

venv:
	$(PYTHON) -m venv $(VENV)

dev: ## run the API and the web app together
	$(MAKE) -j2 api web

api: ## run the extraction API (http://localhost:8000)
	cd api && .venv/bin/uvicorn main:app --reload --reload-include .env --port 8000

web: ## run the web app (http://localhost:3000)
	pnpm -C frontend dev

migrate: ## apply the engine's migrations
	cd api && .venv/bin/alembic -x engine=1 upgrade head
