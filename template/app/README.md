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

## What ships out of the box

- `/document-types` — manage document categories and review the saved
  documents in each. Types start empty; define them in the UI. The listing
  matches stored records by `doc_type` / `type_label`, so keep those fields on
  the schema. Backend: `api/routers/document_types.py` (`/document-types/*`).
- Tests: `cd api && pytest tests/`.

See `AGENTS.md` for the checklist, and `../..` for the engine + UI.

## Database (optional)

The engine's cache, corrections, and source-Document store are DB/file backed.
Copy `api/.env.example` to `api/.env`, set `DATABASE_URL`, and run `make migrate`
(or just `make dev` — the `env` target creates the tables if they do not exist).
Without it, the app still runs with no-op stores.
