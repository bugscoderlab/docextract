# AGENTS.md — this app

This is a **domain app** on top of the domain-free `docextract` engine (backend)
and `@docextract/ui` (frontend). Keep domain words here — never in the engine.

## Checklist

1. **Pull both halves**: `make bootstrap` installs `docextract` (Python, from
   `../..` or a git pin in `api/requirements.txt`) and `@docextract/ui` (from
   `../../../ui` or a git npm dep in `frontend/package.json`).
2. **Backend domain** (`api/domain/`):
   - `schema.py` — Pydantic output shape.
   - `prompt.py` — the domain prompt (composed ahead of the engine's BASE_PROMPT).
   - `record.py` — return `{ fields, items, meta }`; money → integer minor units.
   - `wire.py` — build the `Domain` and the router.
3. **Frontend domain** (`frontend/app/page.tsx`): the `DomainConfig` —
   `itemColumns`, `checks`, `workbookTabs`.
4. `make dev`, then verify.

## What the starter already ships

- **`/document-types`** (`frontend/app/document-types/` +
  `api/routers/document_types.py`): a settings page for document categories,
  with the saved documents of each category. Types start empty — define them in
  the UI. The listing reads stored extraction results (the engine's
  `extraction_cache`) and matches a record's `doc_type` / `type_label`, so keep
  those fields on the schema. The workbench header links over via
  `DomainConfig.navLink`.

## Contract

The backend record the UI reads is `{ fields, items, meta }`. `fields` → the
editable header grid; `items` → the editable table; `meta.label` titles the
document. Money is an integer minor unit.
