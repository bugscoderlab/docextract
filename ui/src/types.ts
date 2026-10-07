/** Domain-neutral shapes the review UI renders. A domain's API record must
 * carry `fields`, `items`, and (optionally) `meta`. */

export type Item = Record<string, unknown>;

export type ExtractedRecord = {
  fields: Record<string, string>;
  items: Item[];
  meta?: Record<string, unknown>;
};

export type Correction = {
  field_path: string;
  old_value: unknown;
  new_value: unknown;
  origin?: string;
};

export type Revision = {
  id: string;
  actor: string;
  note: string | null;
  created_at: string;
  corrections: Correction[];
};

export type QueueStatus = "queued" | "working" | "extracted" | "review" | "approved" | "skipped" | "error";

export type QueueItem = {
  ref: string;
  fileName: string;
  status: QueueStatus;
  record: ExtractedRecord | null;
  sourceHash: string;
  fingerprint: string;
  cached: boolean;
  mimeType: string;
  stored: boolean;
  error?: string;
};

export type SavedRecord = {
  fileName: string;
  sourceHash: string;
  mimeType: string;
  record: ExtractedRecord;
  revisions: Revision[];
};

export type SavedBundle = {
  key: string;
  label: string;
  created_at: string;
  records: SavedRecord[];
};

export type ApprovedRecord = { item: QueueItem; record: ExtractedRecord };
