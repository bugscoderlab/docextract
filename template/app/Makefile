PYTHON ?= python3
VENV := api/.venv
VPIP := $(VENV)/bin/pip
PORT ?= 8000

.PHONY: bootstrap install venv free-port dev api web migrate

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

api: free-port ## run the extraction API (http://localhost:$(PORT)); frees the port first if in use
	cd api && .venv/bin/uvicorn main:app --reload --reload-include .env --port $(PORT)

web: ## run the web app (http://localhost:3000) pointing at the API on $(PORT)
	NEXT_PUBLIC_API_URL=http://localhost:$(PORT) pnpm -C frontend dev

migrate: ## apply the engine's migrations
	cd api && .venv/bin/alembic -x engine=1 upgrade head
