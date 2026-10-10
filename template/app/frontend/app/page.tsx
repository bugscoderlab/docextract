"use client";

import { ReviewShell, type DomainConfig } from "@docextract/ui";

// TODO: describe your domain. The record must carry { fields, items, meta }.
const domain: DomainConfig = {
  apiBaseUrl: process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000",
  labels: { title: "Docextract" },
  navLink: { href: "/document-types", label: "Document types" },
  itemColumns: [
    { key: "code", label: "Code" },
    { key: "description", label: "Description" },
    { key: "qty", label: "Qty", numeric: true },
    { key: "amount_minor", label: "Amount", numeric: true, money: true },
  ],
  // checks: (record) => [{ level: "ok", text: "…" }],
  // workbookTabs: [{ id: "records", label: "Records", columns: [...], rows: (approved) => [...] }],
  exportName: "workbook",
};

export default function Page() {
  return <ReviewShell domain={domain} />;
}
