# AGENTS.md — adding a domain to docextract

This is a **domain-free monorepo**: the Python engine (`src/docextract/`), the
generic review UI (`ui/`), and a starter app (`template/app/`). To use it for a
real project, run `scripts/new-domain.sh ../my-domain`, then add **one domain
module** (backend) and a `DomainConfig` (frontend). Neither half ever gains
domain vocabulary.

## Start a domain

```sh
scripts/new-domain.sh ../my-domain
cd ../my-domain && make bootstrap && make dev
```

Fill in `api/domain/` (schema, prompt, record mapper, wiring) and
`frontend/app/page.tsx` (the `DomainConfig`: item columns, checks, tabs). See
[`template/app/AGENTS.md`](template/app/AGENTS.md).

## The backend seam

A domain is four things, plus wiring. Copy [`template/domain/`](template/domain/)
and fill it in:

| Piece | What it is |
|---|---|
| **Schema** | a Pydantic `BaseModel` describing the output. Add `Field(description=…)` so the model knows each field. |
| **Domain prompt** | a string of domain rules (field vocabulary, money, what to extract). It is composed *ahead of* the engine's `BASE_PROMPT`. |
| **Record mapper** | `Callable[[Schema], dict]` — turns the model into the stored/returned record (e.g. money → integer minor units via `docextract.money.to_minor_units`). |
| **Wiring** | zero-arg factories for the extractor / document store / correction store (DB-backed in production, stubs in tests), assembled into a `Domain`. |

```python
from docextract.domain import Domain
from docextract import build_router, Extractor, SQLModelCache, SQLModelCorrectionStore, build_document_store

domain = Domain(
    schema=MyModel,
    prompt=MY_DOMAIN_PROMPT,
    record=to_record,
    build_document_store=build_document_store,
    build_extractor=lambda: Extractor(MyModel, cache=SQLModelCache(engine),
                                      store=build_document_store(), domain_prompt=MY_DOMAIN_PROMPT),
    build_correction_store=lambda: SQLModelCorrectionStore(engine),
)
router = build_router(domain)
```

## Rules when adding a domain

- **Do not add domain words to the engine** (`prompts.BASE_PROMPT`, `extractor`,
  `router`, `cache_*`, `corrections`, `document_store*`, `money`, `mime`,
  `config`, `providers`, `result`, `loaders`). If a rule is domain-specific, it
  goes in the domain prompt.
- **Keep the schema open** unless the domain demands typed fields. A free-form
  `fields: dict[str, str]` stays extensible.
- **Money** is not a domain: when a value is monetary, store it as an integer
  minor unit with `docextract.money.to_minor_units`.
- **The prompt is part of the recipe fingerprint.** Changing the domain prompt or
  the schema re-runs cached Extractions — expected.
- **Tests**: use a throwaway schema (see `tests/stubs.Widget`). Keep engine tests
  domain-free; put domain tests with the domain.

## Migrations

The engine ships migrations for its own tables (`extraction_cache`, `revision`,
`correction`) under `docextract/migrations/`. Point Alembic at them:

```python
from docextract.migrations import version_locations
config.set_main_option("version_locations", version_locations())
```

## OCR (future)

`loaders.py` is the seam for a future OCR step: it turns source bytes into
LangChain messages. An OCR preprocessor can be added there (or via a `Loader`
protocol) without touching the extractor.
