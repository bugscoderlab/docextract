/** The seam a consumer fills in to use the review UI for a domain. */

import type { ApprovedRecord, ExtractedRecord } from "./types";

export type Check = { level: "ok" | "warn" | "err"; text: string };

/** How one column of an editable/repeated row is shown and edited. */
export type ColumnSpec = {
  key: string;
  label: string;
  /** right-align + monospace (numbers, money) */
  numeric?: boolean;
  /** render money as `1,234.56` from an integer minor unit in the record */
  money?: boolean;
  /** not editable */
  readOnly?: boolean;
};

/** A workbook tab: columns + how to project approved records into rows. */
export type WorkbookTab = {
  id: string;
  label: string;
  columns: ColumnSpec[];
  rows: (approved: ApprovedRecord[]) => Array<Record<string, unknown>>;
};

export type Labels = {
  title?: string;
  queueTitle?: string;
  dropTitle?: string;
  dropHint?: string;
  reviewPane?: string;
  itemsNoun?: string;
};

export type DomainConfig = {
  /** Base URL of the domain's extraction API (e.g. http://localhost:8000). */
  apiBaseUrl: string;
  /** Short engine label for the header pill; falls back to `/extract/config`. */
  engineLabel?: string;
  /** Actor credited on a revision. Default "operator". */
  actor?: string;
  labels?: Labels;
  /** Editable columns of each repeated item row. */
  itemColumns?: ColumnSpec[];
  /** Domain validation rows for the current record. */
  checks?: (record: ExtractedRecord) => Check[];
  /** Workbook tabs. Defaults to a single "Records" tab over approved records. */
  workbookTabs?: WorkbookTab[];
  /** File name (without extension) for the workbook exports. */
  exportName?: string;
};
