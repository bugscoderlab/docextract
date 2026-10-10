"use client";

import {
  useCallback,
  useEffect,
  useLayoutEffect,
  useMemo,
  useRef,
  useState,
  type FocusEvent as ReactFocusEvent,
  type FormEvent as ReactFormEvent,
  type KeyboardEvent as ReactKeyboardEvent,
  type MouseEvent as ReactMouseEvent,
} from "react";

import type { ColumnSpec, DomainConfig, WorkbookTab } from "./domain";
import EnginePill from "./EnginePill";
import PdfViewer from "./PdfViewer";
import {
  buildCorrections,
  displayValue,
  editedCount,
  effectiveRecord,
  parseMinor,
  parseNumber,
} from "./records";
import { loadRevisions, saveRevisions } from "./storage";
import type { ApprovedRecord, ExtractedRecord, QueueItem, QueueStatus, Revision } from "./types";

// Split-pane divider: the dragged column width persists here.
const SPLIT_STORAGE_KEY = "docextractSplit";
const DEFAULT_SPLIT_COLS = "minmax(0, 1fr) 7px minmax(0, 1.2fr)";

// The extractor's JSON envelope: the domain record plus source/recipe identity.
type ExtractResponse = ExtractedRecord & {
  source_hash: string;
  fingerprint: string;
  cached: boolean;
  status: string;
  mime_type: string;
  storage_path: string | null;
};

function isPending(status: QueueStatus): boolean {
  return status === "extracted" || status === "review";
}

function recordLabel(record: ExtractedRecord | null): string {
  if (!record) return "";
  const label = record.meta?.label;
  if (typeof label === "string" && label) return label;
  return Object.values(record.fields).find((value) => value) ?? "";
}

function deriveColumns(item: Record<string, unknown> | undefined): ColumnSpec[] {
  if (!item) return [];
  return Object.keys(item).map((key) => ({ key, label: key }));
}

export default function ReviewShell({ domain }: { domain: DomainConfig }) {
  const actor = domain.actor ?? "operator";
  const labels = domain.labels ?? {};

  const [queue, setQueue] = useState<QueueItem[]>([]);
  const [currentRef, setCurrentRef] = useState<string | null>(null);
  const [revisions, setRevisions] = useState<Record<string, Revision[]>>({});
  const [draft, setDraft] = useState<ExtractedRecord | null>(null);
  const [note, setNote] = useState("");
  const [toast, setToast] = useState("");
  const [dragging, setDragging] = useState(false);
  const [previewError, setPreviewError] = useState(false);
  const [splitCols, setSplitCols] = useState(DEFAULT_SPLIT_COLS);
  const [tabId, setTabId] = useState<string | null>(null);
  const counter = useRef(0);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const docScrollRef = useRef<HTMLDivElement>(null);

  const api = domain.apiBaseUrl.replace(/\/$/, "");

  const flash = useCallback((message: string) => {
    setToast(message);
    window.setTimeout(() => setToast(""), 2800);
  }, []);

  useEffect(() => {
    setRevisions(loadRevisions());
  }, []);

  useEffect(() => {
    const saved = localStorage.getItem(SPLIT_STORAGE_KEY);
    if (saved) setSplitCols(saved);
  }, []);

  const current = useMemo(() => queue.find((item) => item.ref === currentRef) ?? null, [queue, currentRef]);

  const currentEffective = useMemo(() => {
    if (!current?.record) return null;
    return effectiveRecord(current.record, revisions[current.sourceHash] ?? []);
  }, [current, revisions]);

  useEffect(() => {
    setDraft(currentEffective ? structuredClone(currentEffective) : null);
    setNote("");
  }, [currentEffective]);

  const checks = useMemo(
    () => (currentEffective && domain.checks ? domain.checks(currentEffective) : []),
    [currentEffective, domain],
  );

  const update = useCallback((ref: string, patch: Partial<QueueItem>) => {
    setQueue((items) => items.map((item) => (item.ref === ref ? { ...item, ...patch } : item)));
  }, []);

  const addItems = useCallback((incoming: QueueItem[]) => {
    setQueue((items) => [...items, ...incoming]);
    if (incoming[0]) setCurrentRef(incoming[0].ref);
  }, []);

  const applyExtraction = useCallback(
    (ref: string, data: ExtractResponse) => {
      update(ref, {
        status: data.status === "empty" ? "skipped" : "extracted",
        record: data.status === "empty" ? null : data,
        sourceHash: data.source_hash,
        fingerprint: data.fingerprint,
        cached: data.cached,
        mimeType: data.mime_type ?? "",
        stored: Boolean(data.storage_path),
        error: undefined,
      });
    },
    [update],
  );

  const onFiles = useCallback(
    async (files: FileList | null) => {
      if (!files || files.length === 0) return;
      const list = Array.from(files);
      const staged: QueueItem[] = list.map((file) => ({
        ref: `d${(counter.current += 1)}`,
        fileName: file.name,
        status: "queued",
        record: null,
        sourceHash: "",
        fingerprint: "",
        cached: false,
        mimeType: "",
        stored: false,
      }));
      addItems(staged);
      for (let index = 0; index < list.length; index += 1) {
        const file = list[index];
        const ref = staged[index].ref;
        update(ref, { status: "working" });
        const body = new FormData();
        body.append("file", file);
        try {
          const response = await fetch(`${api}/extract/file`, { method: "POST", body });
          if (!response.ok) throw new Error(`HTTP ${response.status}`);
          applyExtraction(ref, (await response.json()) as ExtractResponse);
        } catch (error) {
          update(ref, {
            status: "error",
            error: error instanceof Error ? error.message : "extraction failed",
          });
        }
      }
      flash("Extraction finished");
    },
    [api, addItems, update, applyExtraction, flash],
  );

  const removeItem = useCallback((ref: string) => {
    setQueue((items) => items.filter((item) => item.ref !== ref));
    setCurrentRef((active) => (active === ref ? null : active));
  }, []);

  const reExtract = useCallback(
    async (ref: string) => {
      const item = queue.find((entry) => entry.ref === ref);
      if (!item?.sourceHash) return;
      update(ref, { status: "working", error: undefined });
      try {
        const response = await fetch(`${api}/extract/documents/${item.sourceHash}/extract?force=true`, {
          method: "POST",
        });
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        applyExtraction(ref, (await response.json()) as ExtractResponse);
        flash("Re-extracted");
      } catch (error) {
        update(ref, {
          status: "error",
          error: error instanceof Error ? error.message : "extraction failed",
        });
        flash("Re-extraction failed");
      }
    },
    [api, queue, update, applyExtraction, flash],
  );

  const pendingCorrections = useMemo(
    () => (draft && currentEffective ? buildCorrections(currentEffective, draft) : []),
    [draft, currentEffective],
  );

  const persistCorrections = useCallback((): Revision | null => {
    if (!current || !draft || !currentEffective) return null;
    const remark = note.trim();
    if (pendingCorrections.length === 0 && remark === "") return null;
    const revision: Revision = {
      id: crypto.randomUUID(),
      actor,
      note: remark || null,
      created_at: new Date().toISOString(),
      corrections: pendingCorrections,
    };
    const next = { ...revisions, [current.sourceHash]: [...(revisions[current.sourceHash] ?? []), revision] };
    setRevisions(next);
    saveRevisions(next);
    return revision;
  }, [actor, current, draft, currentEffective, note, revisions, pendingCorrections]);

  const saveCorrections = useCallback(() => {
    const revision = persistCorrections();
    if (!revision) {
      flash("No changes to save");
      return;
    }
    const count = revision.corrections.length;
    if (count > 0 && current) update(current.ref, { status: "review" });
    flash(
      count > 0
        ? `Recorded ${count} correction${count === 1 ? "" : "s"}${revision.note ? " and a remark" : ""}`
        : "Remark saved",
    );
  }, [persistCorrections, flash, current, update]);

  const resolve = useCallback(
    (ref: string, status: QueueItem["status"]) => {
      update(ref, { status });
      setCurrentRef((active) => {
        if (active !== ref) return active;
        const next = queue.find((item) => item.ref !== ref && isPending(item.status));
        return next ? next.ref : active;
      });
    },
    [queue, update],
  );

  const approveCurrent = useCallback(() => {
    if (!current) return;
    const revision = persistCorrections();
    resolve(current.ref, "approved");
    const count = revision?.corrections.length ?? 0;
    flash(count > 0 ? `Committed with ${count} correction${count === 1 ? "" : "s"}` : "Committed");
  }, [current, persistCorrections, resolve, flash]);

  const editCurrent = useCallback(() => {
    if (!current) return;
    update(current.ref, { status: "review" });
    flash("Moved back to review");
  }, [current, update, flash]);

  const approveAll = useCallback(() => {
    setQueue((items) => items.map((item) => (isPending(item.status) ? { ...item, status: "approved" } : item)));
    flash("Approved all pending");
  }, [flash]);

  const approved = useMemo<ApprovedRecord[]>(
    () =>
      queue
        .filter((item) => item.status === "approved" && item.record)
        .map((item) => ({
          item,
          record: effectiveRecord(item.record as ExtractedRecord, revisions[item.sourceHash] ?? []),
        })),
    [queue, revisions],
  );

  useEffect(() => {
    setPreviewError(false);
  }, [currentRef]);

  const syncSplitHeight = useCallback(() => {
    const scroll = docScrollRef.current;
    const split = scroll?.closest(".split");
    const form = split?.querySelector<HTMLElement>(".doc-form");
    const grip = split?.querySelector<HTMLElement>(".split-grip");
    if (!scroll || !form) return;
    if (grip && getComputedStyle(grip).display === "none") {
      scroll.style.height = "";
      return;
    }
    const labelHeight = scroll.closest(".doc-view")?.querySelector<HTMLElement>(".pane-label")?.offsetHeight ?? 0;
    scroll.style.height = `${Math.max(120, form.offsetHeight - labelHeight)}px`;
  }, []);

  useEffect(() => {
    const frame = requestAnimationFrame(syncSplitHeight);
    window.addEventListener("resize", syncSplitHeight);
    return () => {
      cancelAnimationFrame(frame);
      window.removeEventListener("resize", syncSplitHeight);
    };
  }, [syncSplitHeight, currentRef, currentEffective, previewError, splitCols, draft]);

  const startResize = useCallback(
    (event: ReactMouseEvent<HTMLDivElement>) => {
      event.preventDefault();
      const grip = event.currentTarget;
      const split = grip.parentElement;
      if (!split) return;
      grip.classList.add("active");
      const onMove = (moveEvent: MouseEvent) => {
        const rect = split.getBoundingClientRect();
        const left = Math.max(220, Math.min(moveEvent.clientX - rect.left, rect.width - 300));
        split.style.gridTemplateColumns = `${Math.round(left)}px 7px minmax(0, 1fr)`;
        syncSplitHeight();
      };
      const onUp = () => {
        grip.classList.remove("active");
        document.removeEventListener("mousemove", onMove);
        document.removeEventListener("mouseup", onUp);
        const cols = split.style.gridTemplateColumns;
        localStorage.setItem(SPLIT_STORAGE_KEY, cols);
        setSplitCols(cols);
        syncSplitHeight();
      };
      document.addEventListener("mousemove", onMove);
      document.addEventListener("mouseup", onUp);
    },
    [syncSplitHeight],
  );

  const tabs = useMemo<WorkbookTab[]>(() => {
    if (domain.workbookTabs && domain.workbookTabs.length > 0) return domain.workbookTabs;
    return [
      {
        id: "records",
        label: "Records",
        columns: [
          { key: "document", label: "Document" },
          { key: "summary", label: "Summary" },
          { key: "corrections", label: "✎", numeric: true },
        ],
        rows: (rows) =>
          rows.map(({ item, record }) => ({
            document: recordLabel(record) || item.fileName,
            summary: Object.values(record.fields).filter(Boolean).slice(0, 4).join(" · "),
            corrections: editedCount(revisions[item.sourceHash] ?? []),
          })),
      },
    ];
  }, [domain.workbookTabs, revisions]);

  const activeTab = tabs.find((entry) => entry.id === tabId) ?? tabs[0];

  const exportXlsx = useCallback(async () => {
    const XLSX = await import("xlsx");
    const book = XLSX.utils.book_new();
    tabs.forEach((entry) => {
      XLSX.utils.book_append_sheet(book, XLSX.utils.json_to_sheet(entry.rows(approved)), entry.label.slice(0, 31));
    });
    XLSX.writeFile(book, `${domain.exportName ?? "workbook"}.xlsx`);
  }, [tabs, approved, domain.exportName]);

  const exportPdf = useCallback(async () => {
    const { jsPDF } = await import("jspdf");
    const autoTable = (await import("jspdf-autotable")).default;
    const finalY = (doc: unknown) => (doc as { lastAutoTable?: { finalY: number } }).lastAutoTable?.finalY ?? 20;

    const pdf = new jsPDF({ orientation: "landscape" });
    pdf.text(domain.exportName ?? "Workbook", 14, 14);
    let startY = 18;
    tabs.forEach((entry) => {
      autoTable(pdf, {
        startY,
        head: [entry.columns.map((column) => column.label)],
        body: entry.rows(approved).map((row) => entry.columns.map((column) => String(row[column.key] ?? ""))),
      });
      startY = finalY(pdf) + 8;
    });
    pdf.save(`${domain.exportName ?? "workbook"}.pdf`);
  }, [tabs, approved, domain.exportName]);

  const step =
    queue.length === 0
      ? 1
      : queue.every((item) => item.status === "approved" || item.status === "skipped" || item.status === "error")
        ? 3
        : 2;

  const currentRevisions = current ? revisions[current.sourceHash] ?? [] : [];
  const latestRemark = [...currentRevisions].reverse().find((revision) => revision.note)?.note ?? null;
  const currentBadge = current ? statusBadge(current) : null;
  const previewUrl = current?.stored
    ? `${api}/extract/documents/${current.sourceHash}`
    : ((current?.record?.meta?.preview as string | undefined) ?? null);

  const itemColumns = useMemo(() => {
    const configured = domain.itemColumns ?? deriveColumns(draft?.items[0]);
    const items = draft?.items ?? [];
    if (items.length === 0) return configured; // nothing to judge against; keep the layout
    // Hide columns that carry no value in any current row (e.g. price columns
    // on an unpriced cutlist) so the table shows only what the document uses.
    return configured.filter((column) =>
      items.some((item) => item[column.key] !== undefined && item[column.key] !== null && item[column.key] !== ""),
    );
  }, [domain.itemColumns, draft]);

  const patchItem = (index: number, changes: Record<string, unknown>) =>
    setDraft((d) => {
      if (!d) return d;
      const items = d.items.slice();
      items[index] = { ...items[index], ...changes };
      return { ...d, items };
    });

  return (
    <>
      <header>
        <div className="logo">
          {labels.title ?? "Extraction"} <span>Review</span>
        </div>
        <div className="steps">
          <div className={`step ${step === 1 ? "active" : step > 1 ? "done" : ""}`} id="st1">
            <span className="dot">{step > 1 ? "✓" : 1}</span> Drop files
          </div>
          <span className="step-sep">→</span>
          <div className={`step ${step === 2 ? "active" : step > 2 ? "done" : ""}`} id="st2">
            <span className="dot">{step > 2 ? "✓" : 2}</span> Review
          </div>
          <span className="step-sep">→</span>
          <div className={`step ${step === 3 ? "active" : ""}`} id="st3">
            <span className="dot">3</span> Workbook
          </div>
        </div>
        <div className="hdr-right">
          {domain.navLink && (
            <a className="btn-ghost hdr-link" href={domain.navLink.href}>
              {domain.navLink.label}
            </a>
          )}
          <EnginePill apiBaseUrl={api} label={domain.engineLabel} />
        </div>
      </header>

      <main>
        <section id="review" className="on">
          <aside className="queue">
            <h3>{labels.queueTitle ?? "Review queue"}</h3>
            <section
              className={`qz-drop ${dragging ? "over" : ""}`}
              id="qz-drop"
              aria-label="Drop documents to extract"
              onDragOver={(event) => {
                event.preventDefault();
                setDragging(true);
              }}
              onDragLeave={() => setDragging(false)}
              onDrop={(event) => {
                event.preventDefault();
                setDragging(false);
                void onFiles(event.dataTransfer.files);
              }}
            >
              <b>{labels.dropTitle ?? "Drop documents here"}</b>
              <br />
              <span style={{ fontSize: 12 }}>
                {labels.dropHint ?? "PDF or image · extracted first, reviewed after"}
              </span>
              <div style={{ marginTop: 8, display: "flex", gap: 6, justifyContent: "center" }}>
                <input
                  ref={fileInputRef}
                  type="file"
                  multiple
                  hidden
                  accept=".pdf,.png,.jpg,.jpeg,.webp,.txt,.json,.md,.csv"
                  onChange={(event) => {
                    void onFiles(event.target.files);
                    event.target.value = "";
                  }}
                />
                <button
                  className="btn-primary"
                  style={{ padding: "6px 12px", fontSize: 12 }}
                  onClick={() => fileInputRef.current?.click()}
                >
                  Upload
                </button>
                <button
                  className="btn-ghost"
                  id="btn-reset"
                  style={{ padding: "6px 12px", fontSize: 12 }}
                  onClick={() => {
                    setQueue([]);
                    setCurrentRef(null);
                  }}
                >
                  Reset
                </button>
              </div>
            </section>

            {queue.length > 0 && (
              <section id="q-list" className="q-list" aria-label="Review queue documents">
                {queue.map((item) => {
                  const badge = statusBadge(item);
                  return (
                    <div
                      key={item.ref}
                      className={`q-item ${item.ref === currentRef ? "current" : ""} st-${item.status}`}
                      role="button"
                      tabIndex={0}
                      onClick={() => setCurrentRef(item.ref)}
                      onKeyDown={(event) => {
                        if (event.key === "Enter" || event.key === " ") setCurrentRef(item.ref);
                      }}
                    >
                      <div className="q-main">
                        <span className="nm">{item.fileName}</span>
                        <span className="tp">
                          {item.fileName} ·{" "}
                          {recordLabel(item.record) ||
                            item.error ||
                            (item.status === "working" ? "extracting…" : item.status === "queued" ? "queued" : "—")}
                          {item.cached ? " · cached" : ""}
                        </span>
                        <span className={`badge ${badge.cls}`}>{badge.label}</span>
                      </div>
                      {item.sourceHash && (
                        <button
                          type="button"
                          className="q-action q-reextract"
                          title="Re-extract — fresh model call"
                          aria-label={`Re-extract ${item.fileName} with a fresh model call`}
                          onClick={(event) => {
                            event.stopPropagation();
                            void reExtract(item.ref);
                          }}
                        >
                          ↻
                        </button>
                      )}
                      <button
                        type="button"
                        className="q-remove"
                        title="Remove from queue"
                        aria-label={`Remove ${item.fileName}`}
                        onClick={(event) => {
                          event.stopPropagation();
                          removeItem(item.ref);
                        }}
                      >
                        ✕
                      </button>
                    </div>
                  );
                })}
              </section>
            )}

            <section className="q-stats" id="q-stats" aria-label="Queue statistics">
              ● {queue.filter((item) => item.status === "extracted").length} extracted · ●{" "}
              {queue.filter((item) => item.status === "queued" || item.status === "working" || isPending(item.status)).length}{" "}
              pending · ● {queue.filter((item) => item.status === "approved").length} approved · ●{" "}
              {queue.filter((item) => item.status === "skipped").length} skipped
            </section>
            {queue.length > 0 && (
              <button
                className="btn-ghost q-approve-all"
                id="btn-approve-all"
                disabled={!queue.some((item) => isPending(item.status))}
                onClick={approveAll}
              >
                ✓ Approve all pending
              </button>
            )}
          </aside>

          <section className="doc" id="doc-panel" aria-label="Document review panel">
            {!current && (
              <div className="review-empty">
                <div className="big">Nothing to review</div>
                Drop or load documents to begin.
              </div>
            )}
            {current && !current.record && (
              <>
                <header className="doc-head">
                  <span className={`badge ${currentBadge?.cls}`}>{currentBadge?.label}</span>
                  <h2>{current.fileName}</h2>
                </header>
                <div className="review-empty">
                  <div className="big">{current.status === "error" ? "Extraction failed" : "No content"}</div>
                  {current.error ?? "This document yielded no extractable data."}
                </div>
              </>
            )}
            {current && current.record && draft && currentEffective && (
              <>
                <header className="doc-head">
                  <span className="compare-tag">{isPending(current.status) ? "compare" : "preview"}</span>
                  <span className={`badge ${currentBadge?.cls}`}>{currentBadge?.label}</span>
                  <h2>{recordLabel(current.record) || current.fileName}</h2>
                  <span className="fn">{current.fileName}</span>
                  <div className="right">
                    {current.status === "approved" ? (
                      <button className="btn-ok" onClick={editCurrent}>
                        ✎ Edit
                      </button>
                    ) : (
                      <>
                        <button className="btn-ghost" onClick={() => resolve(current.ref, "skipped")}>
                          Skip
                        </button>
                        <button className="btn-ok" onClick={approveCurrent}>
                          ✓ Approve &amp; commit
                        </button>
                      </>
                    )}
                  </div>
                </header>
                <div className="split" style={{ gridTemplateColumns: splitCols }}>
                  <section className="doc-view" aria-label="Original document">
                    <div className="pane-label">Original — {current.fileName}</div>
                    <div className="doc-scroll" ref={docScrollRef}>
                      {previewUrl && !previewError ? (
                        current.mimeType === "application/pdf" ? (
                          <PdfViewer url={previewUrl} />
                        ) : (
                          // eslint-disable-next-line @next/next/no-img-element
                          <img
                            src={previewUrl}
                            alt={`Page preview — ${current.fileName}`}
                            onError={() => setPreviewError(true)}
                          />
                        )
                      ) : (
                        <div className="doc-placeholder">
                          Original document preview unavailable
                          <br />
                          <span style={{ fontFamily: "var(--mono)", fontSize: 11.5 }}>{current.fileName}</span>
                        </div>
                      )}
                    </div>
                  </section>
                  <div
                    className="split-grip"
                    title="Drag to resize panes"
                    role="separator"
                    aria-orientation="vertical"
                    onMouseDown={startResize}
                  />
                  <section className="doc-form">
                    <div className="pane-label">
                      {labels.reviewPane ?? "Extracted data"}{" "}
                      <span className="hint-inline">— click any value to correct</span>
                    </div>
                    <div className="doc-form-inner">
                      <div className="fields">
                        {Object.keys(currentEffective.fields).map((key) => {
                          const original = current.record?.fields[key] ?? "";
                          const currentValue = draft.fields[key] ?? "";
                          const edited = original !== currentValue;
                          return (
                            <div className="fld" key={key}>
                              <label>{key}</label>
                              <EditableText
                                className={`val${edited ? " edited" : ""}`}
                                value={currentValue}
                                ariaLabel={key}
                                onChange={(next) =>
                                  setDraft((d) => (d ? { ...d, fields: { ...d.fields, [key]: next } } : d))
                                }
                              />
                              {edited && <span className="struck">{original}</span>}
                            </div>
                          );
                        })}
                      </div>

                      {itemColumns.length > 0 && (
                        <table className="lines">
                          <thead>
                            <tr>
                              <th>#</th>
                              {itemColumns.map((column) => (
                                <th key={column.key} className={column.numeric ? "num" : undefined}>
                                  {column.label}
                                </th>
                              ))}
                            </tr>
                          </thead>
                          <tbody>
                            {draft.items.map((item, index) => {
                              const originalItem = current.record?.items[index];
                              return (
                                <tr key={index}>
                                  <td>{index + 1}</td>
                                  {itemColumns.map((column) => {
                                    const value = item[column.key];
                                    const display = displayValue(value, column.money);
                                    const original = originalItem?.[column.key];
                                    const originalText = displayValue(original, column.money);
                                    const edited =
                                      original !== undefined &&
                                      displayValue(original, column.money) !== displayValue(value, column.money);
                                    if (column.readOnly) {
                                      return (
                                        <td key={column.key} className={column.numeric ? "num" : undefined}>
                                          {display}
                                        </td>
                                      );
                                    }
                                    return (
                                      <EditableText
                                        key={column.key}
                                        tag="td"
                                        className={`${column.numeric ? "num" : ""}${edited ? " edited" : ""}`.trim() || undefined}
                                        value={display}
                                        struck={originalText || undefined}
                                        ariaLabel={`Item ${index + 1} ${column.label}`}
                                        commitOn={column.numeric ? "blur" : "input"}
                                        onChange={(next) =>
                                          patchItem(index, {
                                            [column.key]: column.money
                                              ? parseMinor(next)
                                              : column.numeric
                                                ? parseNumber(next)
                                                : next,
                                          })
                                        }
                                      />
                                    );
                                  })}
                                </tr>
                              );
                            })}
                          </tbody>
                        </table>
                      )}

                      {checks.length > 0 && (
                        <div className="checks">
                          {checks.map((check, index) => (
                            <div key={index} className={`chk ${check.level}`}>
                              <span className="mark">
                                {check.level === "ok" ? "✓" : check.level === "warn" ? "⚠" : "✕"}
                              </span>{" "}
                              {check.text}
                            </div>
                          ))}
                        </div>
                      )}

                      {latestRemark && (
                        <div className="remark-banner">
                          <span className="mark">✎</span>
                          <span>
                            <b>Remark</b> — {latestRemark}
                          </span>
                        </div>
                      )}

                      <div className="remark">
                        <input
                          className="remark-input"
                          placeholder="Add a remark — why this correction was made…"
                          value={note}
                          onChange={(event) => setNote(event.target.value)}
                          onKeyDown={(event) => {
                            if (event.key === "Enter") saveCorrections();
                          }}
                        />
                        <button
                          className="btn-primary"
                          disabled={pendingCorrections.length === 0 && note.trim() === ""}
                          onClick={saveCorrections}
                        >
                          💾 Save
                        </button>
                      </div>

                      <div className="history">
                        <b>History</b> — {currentRevisions.length} revision{currentRevisions.length === 1 ? "" : "s"}
                        {currentRevisions.length === 0 && <div>No corrections recorded yet.</div>}
                        {currentRevisions.map((revision) => (
                          <div key={revision.id} className="chk ok">
                            <span className="mark">✎</span> {revision.actor} ·{" "}
                            {new Date(revision.created_at).toLocaleString()}
                            {revision.note ? ` · ${revision.note}` : ""}
                            {revision.corrections.length > 0 && (
                              <ul style={{ margin: "4px 0 0 18px" }}>
                                {revision.corrections.map((correction, index) => (
                                  <li key={index}>
                                    <code>{correction.field_path}</code>: {String(correction.old_value)} →{" "}
                                    <b>{String(correction.new_value)}</b>
                                  </li>
                                ))}
                              </ul>
                            )}
                          </div>
                        ))}
                      </div>
                    </div>
                  </section>
                </div>
              </>
            )}
          </section>
        </section>

        <section id="wb" className="on">
          <section className="wb-head" aria-label="Workbook controls">
            <h2>Master workbook</h2>
            <div className="tabs">
              {tabs.map((entry) => (
                <button
                  key={entry.id}
                  className={`tab ${activeTab?.id === entry.id ? "on" : ""}`}
                  onClick={() => setTabId(entry.id)}
                >
                  {entry.label}
                </button>
              ))}
            </div>
            <div className="export-box">
              <button className="btn-ghost" id="btn-xlsx" onClick={() => void exportXlsx()}>
                ⬇ Export .xlsx
              </button>
              <button className="btn-ghost" id="btn-pdf" onClick={() => void exportPdf()}>
                ⬇ Export .pdf
              </button>
            </div>
          </section>

          <section className="sheet" id="sheet" aria-label="Workbook sheet">
            {approved.length === 0 && <div className="empty">Approve documents to fill the workbook.</div>}
            {approved.length > 0 && activeTab && (
              <table>
                <thead>
                  <tr>
                    {activeTab.columns.map((column) => (
                      <th key={column.key} className={column.numeric ? "num" : undefined}>
                        {column.label}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {activeTab.rows(approved).map((row, index) => (
                    <tr key={index}>
                      {activeTab.columns.map((column) => (
                        <td key={column.key} className={column.numeric ? "num" : undefined}>
                          {column.money ? displayValue(row[column.key], true) : String(row[column.key] ?? "")}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </section>
        </section>
      </main>

      <div id="toast" className={toast ? "on" : ""}>
        {toast}
      </div>
    </>
  );
}

function statusBadge(item: QueueItem): { cls: string; label: string } {
  switch (item.status) {
    case "queued":
      return { cls: "b-queue", label: "queued" };
    case "working":
      return { cls: "b-work", label: "extracting" };
    case "extracted":
      return { cls: "b-extract", label: "extracted" };
    case "review":
      return { cls: "b-review", label: "needs review" };
    case "approved":
      return { cls: "b-ok", label: "✓ approved" };
    case "skipped":
      return { cls: "b-skip", label: "skipped" };
    case "error":
      return { cls: "b-skip", label: "error" };
  }
}

// The value the operator is editing, excluding any struck-through original that
// lives inside the same contenteditable (the `.struck` marker).
function editableValue(node: HTMLElement): string {
  const marker = node.querySelector(":scope > .struck");
  return marker ? (node.textContent ?? "").replace(marker.textContent ?? "", "") : node.textContent ?? "";
}

function paintEditable(node: HTMLElement, value: string, struck?: string): void {
  node.textContent = value;
  if (!struck) return;
  const marker = document.createElement("span");
  marker.className = "struck";
  marker.textContent = ` ${struck}`;
  node.appendChild(marker);
}

function paintStruck(node: HTMLElement, value: string, struck?: string): void {
  const marker = node.querySelector(":scope > .struck");
  const show = Boolean(struck) && value.trim() !== "" && value.trim() !== struck!.trim();
  if (!show) {
    marker?.remove();
    return;
  }
  if (marker) {
    marker.textContent = ` ${struck}`;
  } else {
    const span = document.createElement("span");
    span.className = "struck";
    span.textContent = ` ${struck}`;
    node.appendChild(span);
  }
}

// Inline editor: a contenteditable element the browser owns while typing. React
// only pushes an external value in when it differs and the element is not
// focused, so the caret never jumps. `struck` is the original shown struck
// through; `commitOn` decides when the parsed value is written back.
function EditableText({
  tag = "div",
  value,
  struck,
  onChange,
  className,
  ariaLabel,
  commitOn = "input",
}: {
  tag?: "div" | "td" | "span";
  value: string;
  struck?: string;
  onChange: (next: string) => void;
  className?: string;
  ariaLabel?: string;
  commitOn?: "input" | "blur";
}) {
  const element = useRef<HTMLElement | null>(null);
  const focused = useRef(false);
  const setRef = useCallback((node: HTMLElement | null) => {
    element.current = node;
  }, []);
  useLayoutEffect(() => {
    const node = element.current;
    if (!node || focused.current) return;
    const marker = node.querySelector(":scope > .struck");
    const current = editableValue(node);
    const currentStruck = marker ? (marker.textContent ?? "").replace(/^ /, "") : undefined;
    const wantStruck = struck && value.trim() !== "" && value.trim() !== struck.trim() ? struck : undefined;
    if (current !== value || currentStruck !== wantStruck) paintEditable(node, value, wantStruck);
  });
  const shared = {
    className,
    contentEditable: true,
    suppressContentEditableWarning: true,
    "aria-label": ariaLabel,
    onFocus: () => {
      focused.current = true;
    },
    onBlur: (event: ReactFocusEvent<HTMLElement>) => {
      focused.current = false;
      if (commitOn === "blur") onChange(editableValue(event.currentTarget));
    },
    onInput: (event: ReactFormEvent<HTMLElement>) => {
      const node = event.currentTarget;
      const text = editableValue(node);
      paintStruck(node, text, struck);
      if (commitOn === "input") onChange(text);
    },
    onKeyDown: (event: ReactKeyboardEvent<HTMLElement>) => {
      if (event.key === "Enter") event.preventDefault();
    },
  };
  if (tag === "td") return <td ref={setRef} {...shared} />;
  if (tag === "span") return <span ref={setRef} {...shared} />;
  return <div ref={setRef} {...shared} />;
}
