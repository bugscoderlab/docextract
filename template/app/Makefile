PYTHON ?= python3
VENV := api/.venv
VPIP := $(VENV)/bin/pip
PORT ?= 8000
WEB_PORT ?= 3000
DB_NAME ?= app

.DEFAULT_GOAL := help

.PHONY: help bootstrap install venv env db db-postgres db-sqlite free-port free-port-web dev api web migrate

help: ## show this help
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  make %-14s %s\n", $$1, $$2}'

bootstrap: install ## install the engine, the UI, and app deps

install: venv
	$(VPIP) install -r api/requirements.txt
	pnpm -C frontend install

venv:
	$(PYTHON) -m venv $(VENV)

dev: ## run the API and the web app together
	$(MAKE) -j2 api web

free-port: ## stop whatever is listening on $(PORT), if anything
	-@PIDS="$$(lsof -ti:$(PORT) 2>/dev/null)"; \
	if [ -n "$$PIDS" ]; then echo "port $(PORT) in use — stopping $$PIDS"; kill -9 $$PIDS 2>/dev/null || true; sleep 1; fi

env: venv ## create the database tables if they do not exist yet (idempotent)
	cd api && .venv/bin/python -c "import main; from sqlmodel import SQLModel; SQLModel.metadata.create_all(main.engine)"

db: ## create the Postgres database $(DB_NAME) if it does not exist
	-createdb $(DB_NAME) 2>/dev/null || echo "database '$(DB_NAME)' already exists (or createdb failed)"

db-postgres: db ## point api/.env at Postgres database $(DB_NAME)
	printf 'DATABASE_URL=postgresql+psycopg2://postgres:password@localhost:5432/$(DB_NAME)\n' > api/.env

db-sqlite: ## use a local SQLite file api/$(DB_NAME).db instead of Postgres (writes api/.env)
	printf 'DATABASE_URL=sqlite:///./$(DB_NAME).db\n' > api/.env

api: env free-port ## run the extraction API (http://localhost:$(PORT)); creates the env first, frees the port if in use
	cd api && .venv/bin/uvicorn main:app --reload --reload-include .env --port $(PORT)

web: free-port-web ## run the web app (http://localhost:$(WEB_PORT)) pointing at the API on $(PORT)
	NEXT_PUBLIC_API_URL=http://localhost:$(PORT) pnpm -C frontend dev --port $(WEB_PORT)

free-port-web: ## stop whatever is listening on $(WEB_PORT), if anything
	-@PIDS="$$(lsof -ti:$(WEB_PORT) 2>/dev/null)"; \
	if [ -n "$$PIDS" ]; then echo "port $(WEB_PORT) in use — stopping $$PIDS"; kill -9 $$PIDS 2>/dev/null || true; sleep 1; fi

migrate: ## apply the engine's migrations
	cd api && .venv/bin/alembic -x engine=1 upgrade head
