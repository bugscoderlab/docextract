# docextract

A **domain-free** document-extraction stack: a Python **engine** + a review
**UI**. You supply the schema, the domain prompt, a record mapper, and a
`DomainConfig`; the stack reads a document (PDF / image / text), runs the model,
caches the result by content × recipe, and lets an operator review, correct, and
approve it.

Neither half carries domain knowledge — no invoice fields, no shipping
vocabulary. That belongs to the consumer.

---

## Quick start — a new domain project

The fastest path: clone the stack, scaffold a project from the starter, run it.

```sh
git clone https://github.com/bugscoderlab/docextract.git
cd docextract
scripts/new-domain.sh ../my-domain     # copy template/app, repoint its deps
cd ../my-domain
make bootstrap                         # installs the engine + UI + app deps
make dev                               # API on :8000, web on :3000
```

Then fill in the domain:

| File | What |
|---|---|
| `api/domain/schema.py` | the output shape (Pydantic) |
| `api/domain/prompt.py` | the domain rules |
| `api/domain/record.py` | map the schema to `{ fields, items, meta }` |
| `frontend/app/page.tsx` | the `DomainConfig` (item columns, checks, tabs) |

> This repo is a **template**: you can also click **Use this template** on GitHub
> to get a fresh copy of the monorepo.

---

## Use the engine alone (Python)

```sh
pip install "docextract[providers,sqlmodel,api,migrations] @ git+https://github.com/bugscoderlab/docextract.git"
```

```python
from pydantic import BaseModel, Field
from docextract import Extractor

class MyDoc(BaseModel):
    fields: dict[str, str] = Field(default_factory=dict)
    items: list[dict] = Field(default_factory=list)

DOMAIN_PROMPT = "You extract … documents. Put header values in `fields` …"

extractor = Extractor(MyDoc, domain_prompt=DOMAIN_PROMPT)
result = extractor.extract("doc.pdf")     # -> ExtractionResult[MyDoc]
result.data        # MyDoc | None
result.cached      # served from cache?
result.fingerprint # the recipe identity
```

Serve it over HTTP with the router factory:

```python
from docextract import build_router
from docextract.domain import Domain

domain = Domain(schema=MyDoc, prompt=DOMAIN_PROMPT, record=lambda d: d.model_dump())
app.include_router(build_router(domain))
```

Point it at a database (the engine never imports one):

```python
from docextract import Extractor, SQLModelCache, SQLModelCorrectionStore, build_document_store

domain = Domain(
    schema=MyDoc, prompt=DOMAIN_PROMPT, record=lambda d: d.model_dump(),
    build_document_store=build_document_store,
    build_extractor=lambda: Extractor(MyDoc, cache=SQLModelCache(engine),
                                      store=build_document_store(), domain_prompt=DOMAIN_PROMPT),
    build_correction_store=lambda: SQLModelCorrectionStore(engine),
)
```

---

## Use the UI alone (React / Next.js)

```sh
pnpm add "github:bugscoderlab/docextract#path:ui"
```

```tsx
"use client";
import { ReviewShell, type DomainConfig } from "@docextract/ui";
import "@docextract/ui/styles.css";

const domain: DomainConfig = {
  apiBaseUrl: process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000",
  itemColumns: [
    { key: "code", label: "Code" },
    { key: "description", label: "Description" },
    { key: "qty", label: "Qty", numeric: true },
    { key: "amount_minor", label: "Amount", numeric: true, money: true },
  ],
  // checks: (record) => [{ level: "ok", text: "…" }],
  // workbookTabs: [{ id, label, columns, rows }],
  exportName: "workbook",
};

export default function Page() {
  return <ReviewShell domain={domain} />;
}
```

In `next.config.ts`, transpile the package source:

```ts
const nextConfig = { transpilePackages: ["@docextract/ui"] };
```

And copy the PDF worker into `public/`:

```sh
cp node_modules/pdfjs-dist/build/pdf.worker.min.mjs public/
```

---

## The record contract

The backend record the UI reads must carry:

```ts
{ fields: Record<string, string>, items: Array<Record<string, unknown>>, meta?: Record<string, unknown> }
```

- `fields` → the editable header grid
- `items` → the editable table (columns from `domain.itemColumns`)
- `meta` → free-form; `meta.label` titles the document, `meta.preview` is a
  fallback preview URL

Money is not a domain: store monetary values as **integer minor units**
(`docextract.money.to_minor_units`), and mark the column `money: true`.

---

## Monorepo layout

| Path | What |
|---|---|
| `src/docextract/` | the **engine** (pip: `docextract`) |
| `ui/` | `@docextract/ui` — the **generic review UI** |
| `template/app/` | a **starter app** (FastAPI + Next.js) wired to both |
| `template/domain/` | a **backend domain scaffold** |
| `scripts/new-domain.sh` | scaffold a new project from the starter |
| `tests/` | engine tests |

See [`AGENTS.md`](AGENTS.md) and [`template/app/AGENTS.md`](template/app/AGENTS.md)
for the domain-adding checklist.

---

## Develop this repo

```sh
pip install -e ".[dev]" && pytest          # engine tests (73)
cd ui && pnpm install && pnpm typecheck    # UI typecheck
```
