# @docextract/ui

A **domain-free** review UI for a [docextract](../) backend. The flow:
drop documents → extract → review & correct (inline, with the original struck
through) → approve → workbook.

It carries no domain knowledge. You supply a **`DomainConfig`**: the API base
URL, the editable columns of a repeated item, optional validation checks, and
optional workbook tabs.

## Use (Next.js)

```tsx
// app/page.tsx
import { ReviewShell, type DomainConfig } from "@docextract/ui";
import "@docextract/ui/styles.css";

const domain: DomainConfig = {
  apiBaseUrl: process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000",
  labels: { title: "ACME" },
  itemColumns: [
    { key: "code", label: "Code" },
    { key: "description", label: "Description" },
    { key: "qty", label: "Qty", numeric: true },
    { key: "amount_minor", label: "Amount", numeric: true, money: true },
  ],
  checks: (record) => [/* domain validation rows */],
};

export default function Page() {
  return <ReviewShell domain={domain} />;
}
```

In `next.config.ts`, transpile the package source:

```ts
const nextConfig = { transpilePackages: ["@docextract/ui"] };
export default nextConfig;
```

Copy `node_modules/pdfjs-dist/build/pdf.worker.min.mjs` to `public/` (the PDF
viewer loads it at `/pdf.worker.min.mjs`).

## The record contract

The backend's record must carry:

```ts
{ fields: Record<string, string>, items: Array<Record<string, unknown>>, meta?: Record<string, unknown> }
```

`fields` renders as the editable header grid; `items` renders as the editable
table (columns from `domain.itemColumns`); `meta` is free-form (e.g.
`meta.label` titles the document, `meta.preview` is a fallback preview URL).

## DomainConfig

| field | meaning |
|---|---|
| `apiBaseUrl` | the extraction API base (`/extract/*`) |
| `engineLabel` | fixed header pill; omit to read `/extract/config` |
| `actor` | credited on a revision (default `operator`) |
| `labels` | titles/copy |
| `itemColumns` | editable columns of each item row |
| `checks(record)` | domain validation rows (`ok`/`warn`/`err`) |
| `workbookTabs` | workbook tabs; default is a single "Records" tab |
| `exportName` | export file base name |

## Develop

```sh
pnpm install
pnpm typecheck
```
