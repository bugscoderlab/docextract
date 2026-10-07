# docextract starter app

A minimal app (FastAPI + Next.js) wired to the domain-free `docextract` engine
and `@docextract/ui`. Fill in the domain, then run.

## Start

```sh
make bootstrap   # installs the engine + UI + app deps
make dev         # api on :8000, web on :3000
```

## Fill in the domain

- `api/domain/schema.py` — the output shape (Pydantic).
- `api/domain/prompt.py` — the domain rules.
- `api/domain/record.py` — map the schema to `{ fields, items, meta }`.
- `frontend/app/page.tsx` — the `DomainConfig` (item columns, checks, tabs).

See `AGENTS.md` for the checklist, and `../..` for the engine + UI.

## Database (optional)

The engine's cache, corrections, and source-Document store are DB/file backed.
Set `DATABASE_URL` in `api/.env` and run `make migrate`. Without it, the app
still runs with no-op stores.
