# docextract

A **domain-free** document-extraction stack: a Python engine + a review UI. You
supply the schema, the domain prompt, a record mapper, and a `DomainConfig`; the
stack reads a document (PDF / image / text), runs the model, caches the result by
content × recipe, and lets an operator review, correct, and approve it.

Neither half carries domain knowledge — no invoice fields, no shipping
vocabulary. That belongs to the consumer.

## Monorepo layout

| Path | What |
|---|---|
| `src/docextract/` | the **engine** (pip: `docextract`) — extraction, cache, corrections, document store, router factory, migrations |
| `ui/` | `@docextract/ui` — the **generic review UI** (React) |
| `template/app/` | a **starter app** (FastAPI + Next.js) wired to both |
| `template/domain/` | a **backend domain scaffold** (schema + prompt + mapper + wiring) |
| `scripts/new-domain.sh` | the hook — copy the starter into a new project |
| `tests/` | engine tests |

## Start a domain

```sh
scripts/new-domain.sh ../my-domain
cd ../my-domain && make bootstrap && make dev
```

Then fill in `api/domain/` (backend) and `frontend/app/page.tsx` (UI config). See
[`AGENTS.md`](AGENTS.md) and [`template/app/AGENTS.md`](template/app/AGENTS.md).

## Install

```sh
pip install docextract            # core
pip install "docextract[providers,sqlmodel,api,migrations]"   # typical app
```

Or, as a git dependency in another project's `requirements.txt`:

```requirements
docextract @ git+https://github.com/<owner>/docextract.git@v0.1.0
# or, for local development:
# -e ../docextract
```

## Use

```python
from pydantic import BaseModel
from docextract import Extractor

class MyModel(BaseModel):
    title: str = ""
    total: str | None = None

DOMAIN_PROMPT = """You extract ACME receipts. Put the header in `fields` ..."""

extractor = Extractor(MyModel, domain_prompt=DOMAIN_PROMPT)
result = extractor.extract("receipt.pdf")   # -> ExtractionResult[MyModel]
result.data      # -> MyModel | None
result.cached    # -> served from cache?
result.fingerprint
```

Serve it over HTTP with the router factory:

```python
from docextract.domain import Domain
from docextract import build_router

domain = Domain(schema=MyModel, prompt=DOMAIN_PROMPT, record=lambda m: m.model_dump())
app.include_router(build_router(domain))
```

Wire a database (the engine never imports one):

```python
from docextract import SQLModelCache, SQLModelCorrectionStore, build_document_store
from sqlmodel import create_engine

engine = create_engine(DATABASE_URL)
domain = Domain(
    schema=MyModel,
    prompt=DOMAIN_PROMPT,
    record=lambda m: m.model_dump(),
    build_document_store=build_document_store,
    build_extractor=lambda: Extractor(MyModel, cache=SQLModelCache(engine),
                                      store=build_document_store(), domain_prompt=DOMAIN_PROMPT),
    build_correction_store=lambda: SQLModelCorrectionStore(engine),
)
```

## Layout

| Module | Responsibility |
|---|---|
| `config.py` | `ExtractionConfig` — provider, model, temperature, limits (from env) |
| `providers.py` | `build_chat_model()` — the only file that touches LangChain |
| `result.py` | `ExtractionResult`, `source_hash` (content), `fingerprint` (recipe) |
| `extractor.py` | `Extractor(schema, …, domain_prompt=…)` — the entry point |
| `prompts.py` | generic `BASE_PROMPT` + `compose_system_prompt()` |
| `loaders.py` | source → LangChain messages |
| `domain.py` | `Domain` — the descriptor the router factory consumes |
| `router.py` | `build_router(domain)` — the FastAPI surface |
| `cache_store.py` / `cache_sqlmodel.py` | content-addressed Extraction cache |
| `corrections.py` / `corrections_sqlmodel.py` | append-only Correction / Revision log |
| `document_store.py` / `document_store_s3.py` | source-Document bytes by content hash |
| `money.py` | integer minor-unit money |
| `mime.py` | MIME helpers |
| `migrations/` | Alembic scripts for the engine's tables |

## Extending with a domain

See [`AGENTS.md`](AGENTS.md) and copy [`template/domain/`](template/domain/):
define the schema, the domain prompt, the record mapper, and the wiring.

## Tests

```sh
pip install -e ".[dev]"
pytest
```
