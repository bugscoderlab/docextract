import type { ApprovedRecord, Correction, ExtractedRecord, Revision } from "./types";

/** Money is integer minor units everywhere; format only for display. */
export function formatMinor(minor: number | null | undefined, currency?: string | null): string {
  if (minor === null || minor === undefined) return "—";
  const amount = (minor / 100).toLocaleString("en-US", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
  return currency ? `${currency} ${amount}` : amount;
}

/** Parse an edited money string ("1,063.15", "—") back to integer minor units. */
export function parseMinor(text: string): number | null {
  const cleaned = text.replace(/[^0-9.\-]/g, "");
  if (!/[0-9]/.test(cleaned)) return null;
  const value = Number(cleaned);
  return Number.isNaN(value) ? null : Math.round(value * 100);
}

/** Parse an edited numeric string ("4", "—") back to a number. */
export function parseNumber(text: string): number | null {
  const cleaned = text.replace(/[^0-9.\-]/g, "");
  if (!/[0-9]/.test(cleaned)) return null;
  const value = Number(cleaned);
  return Number.isNaN(value) ? null : value;
}

/** Display a record value for a column, honouring `money`. */
export function displayValue(value: unknown, money?: boolean): string {
  if (value === null || value === undefined) return "";
  if (money) return formatMinor(typeof value === "number" ? value : Number(value));
  return String(value);
}

function keyOf(part: string): string | number {
  return /^-?\d+$/.test(part) ? Number(part) : part;
}

export function setPath(data: unknown, path: string, value: unknown): void {
  const parts = path.split(".");
  let node = data as Record<string | number, unknown>;
  for (const part of parts.slice(0, -1)) {
    node = node[keyOf(part)] as Record<string | number, unknown>;
  }
  node[keyOf(parts[parts.length - 1])] = value;
}

export function allCorrections(revisions: Revision[]): Correction[] {
  return revisions.flatMap((revision) => revision.corrections);
}

export function editedCount(revisions: Revision[]): number {
  return allCorrections(revisions).length;
}

/** The Extraction's data with every recorded Correction applied, in order. */
export function effectiveRecord(record: ExtractedRecord, revisions: Revision[]): ExtractedRecord {
  const clone = structuredClone(record);
  for (const correction of allCorrections(revisions)) {
    setPath(clone, correction.field_path, correction.new_value);
  }
  return clone;
}

/** The one place that knows the correction path grammar for a record. */
export function buildCorrections(base: ExtractedRecord, draft: ExtractedRecord): Correction[] {
  const out: Correction[] = [];
  const fieldKeys = new Set([...Object.keys(base.fields), ...Object.keys(draft.fields)]);
  fieldKeys.forEach((key) => {
    const before = base.fields[key] ?? "";
    const after = draft.fields[key] ?? "";
    if (before !== after) out.push({ field_path: `fields.${key}`, old_value: before, new_value: after });
  });
  const count = Math.max(base.items.length, draft.items.length);
  for (let index = 0; index < count; index += 1) {
    const a = base.items[index];
    const b = draft.items[index];
    if (!a || !b) continue;
    const keys = new Set([...Object.keys(a), ...Object.keys(b)]);
    keys.forEach((key) => {
      if (a[key] !== b[key]) {
        out.push({ field_path: `items.${index}.${key}`, old_value: a[key], new_value: b[key] });
      }
    });
  }
  return out;
}

export function approvedCount(approved: ApprovedRecord[]): number {
  return approved.length;
}
