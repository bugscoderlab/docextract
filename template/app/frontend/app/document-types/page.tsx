"use client";

import Link from "next/link";
import { useEffect, useState, type FormEvent } from "react";

type DocumentType = {
  key: string;
  name: string;
  remark: string | null;
};

type TypeDocument = {
  source_hash: string;
  file_name: string;
  type_label: string;
  created_at: string;
};

const API = (process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000").replace(/\/$/, "");

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API}/document-types${path}`, init);
  const body = (await response.json()) as T & { detail?: string };
  if (!response.ok) {
    throw new Error(body.detail ?? `Request failed (${response.status})`);
  }
  return body;
}

export default function DocumentTypesPage() {
  const [types, setTypes] = useState<DocumentType[]>([]);
  const [selectedKey, setSelectedKey] = useState<string | null>(null);
  const [editingKey, setEditingKey] = useState<string | null>(null);
  const [name, setName] = useState("");
  const [remark, setRemark] = useState("");
  const [typesLoading, setTypesLoading] = useState(true);
  const [documents, setDocuments] = useState<TypeDocument[]>([]);
  const [documentsLoading, setDocumentsLoading] = useState(false);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [documentsError, setDocumentsError] = useState<string | null>(null);
  const [formError, setFormError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  const selectedType = types.find((type) => type.key === selectedKey) ?? null;

  useEffect(() => {
    let cancelled = false;
    request<DocumentType[]>("/")
      .then((list) => {
        if (cancelled) return;
        setTypes(list);
        setSelectedKey((current) =>
          current && list.some((type) => type.key === current) ? current : (list[0]?.key ?? null),
        );
        setLoadError(null);
      })
      .catch((error: unknown) => {
        if (!cancelled) setLoadError(error instanceof Error ? error.message : "Failed to load document types");
      })
      .finally(() => {
        if (!cancelled) setTypesLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (!selectedKey) {
      setDocuments([]);
      return;
    }
    let cancelled = false;
    setDocumentsLoading(true);
    setDocumentsError(null);
    request<TypeDocument[]>(`/${encodeURIComponent(selectedKey)}/documents`)
      .then((list) => {
        if (!cancelled) setDocuments(list);
      })
      .catch((error: unknown) => {
        if (!cancelled) setDocumentsError(error instanceof Error ? error.message : "Failed to load documents");
      })
      .finally(() => {
        if (!cancelled) setDocumentsLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [selectedKey]);

  const selectType = (type: DocumentType) => {
    setSelectedKey(type.key);
    setEditingKey(type.key);
    setName(type.name);
    setRemark(type.remark ?? "");
    setFormError(null);
  };

  const startNew = () => {
    setSelectedKey(null);
    setEditingKey(null);
    setName("");
    setRemark("");
    setFormError(null);
  };

  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!name.trim()) {
      setFormError("Type of document is required.");
      return;
    }
    setSaving(true);
    setFormError(null);
    try {
      const saved = await request<DocumentType>(editingKey ? `/${editingKey}` : "/", {
        method: editingKey ? "PUT" : "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name: name.trim(), remark: remark.trim() || null }),
      });
      setTypes(await request<DocumentType[]>("/"));
      setEditingKey(saved.key);
      setSelectedKey(saved.key);
      setName(saved.name);
      setRemark(saved.remark ?? "");
      setDocuments(await request<TypeDocument[]>(`/${saved.key}/documents`));
    } catch (error: unknown) {
      setFormError(error instanceof Error ? error.message : "Failed to save document type");
    } finally {
      setSaving(false);
    }
  };

  return (
    <>
      <header>
        <div className="logo">
          Docextract <span>Document types</span>
        </div>
        <div className="hdr-right">
          <Link className="btn-ghost hdr-link" href="/">
            ← Workbench
          </Link>
        </div>
      </header>

      <main>
        <section className="wb-head" aria-label="Document types header">
          <h2>Document types</h2>
          <p className="dt-intro">Add or edit document categories, then review the saved documents in each category.</p>
        </section>

        <div className="doc-types-layout">
          <section className="doc-type-panel" aria-label="Document type editor">
            <div className="dt-panel-head">
              <h3>Types</h3>
              <button type="button" className="btn-ghost" onClick={startNew}>
                + Add new
              </button>
            </div>

            <div className="dt-type-list">
              {typesLoading && <div className="dt-muted">Loading document types…</div>}
              {loadError && <div className="form-error">{loadError}</div>}
              {!typesLoading && !loadError && types.length === 0 && (
                <div className="dt-muted">No document types yet.</div>
              )}
              {types.map((type) => (
                <button
                  key={type.key}
                  type="button"
                  className={`dt-type-option ${type.key === selectedKey ? "on" : ""}`}
                  onClick={() => selectType(type)}
                >
                  <span className="dt-type-name">{type.name}</span>
                  <span className="dt-type-remark">{type.remark ?? "No remark"}</span>
                </button>
              ))}
            </div>

            <form className="dt-form" onSubmit={(event) => void submit(event)}>
              <div className="dt-field">
                <label htmlFor="document-type-name">Type of document</label>
                <input
                  id="document-type-name"
                  type="text"
                  value={name}
                  placeholder="e.g. Supplier Invoice"
                  onChange={(event) => setName(event.target.value)}
                />
              </div>
              <div className="dt-field">
                <label htmlFor="document-type-remark">Remark</label>
                <textarea
                  id="document-type-remark"
                  value={remark}
                  placeholder="What is this document used for?"
                  rows={3}
                  onChange={(event) => setRemark(event.target.value)}
                />
              </div>
              {formError && <div className="form-error">{formError}</div>}
              <div className="dt-actions">
                <button className="btn-primary" type="submit" disabled={saving}>
                  {saving ? "Saving…" : editingKey ? "Save changes" : "Add document type"}
                </button>
                {editingKey && (
                  <button type="button" className="btn-ghost" onClick={startNew}>
                    Cancel
                  </button>
                )}
              </div>
            </form>
          </section>

          <section className="doc-type-documents" aria-label="Documents for selected type">
            <div className="dt-doc-head">
              <div>
                <h3>{selectedType ? selectedType.name : "Documents"}</h3>
                {selectedType?.remark && <p>{selectedType.remark}</p>}
              </div>
              {selectedType && <span className="pill">{documents.length} saved</span>}
            </div>

            <section className="sheet dt-documents">
              {!selectedType && <div className="empty">Select a document type on the left, or add a new one.</div>}
              {selectedType && documentsLoading && <div className="empty">Loading documents…</div>}
              {selectedType && !documentsLoading && documentsError && (
                <div className="empty form-error">{documentsError}</div>
              )}
              {selectedType && !documentsLoading && !documentsError && documents.length === 0 && (
                <div className="empty">No saved documents belong to this type yet.</div>
              )}
              {selectedType && !documentsLoading && !documentsError && documents.length > 0 && (
                <table>
                  <thead>
                    <tr>
                      <th>Document</th>
                      <th>Type</th>
                      <th>Added</th>
                    </tr>
                  </thead>
                  <tbody>
                    {documents.map((document) => (
                      <tr key={document.source_hash}>
                        <td>
                          <b>{document.file_name}</b>
                          <span className="dt-doc-sub">{document.type_label}</span>
                        </td>
                        <td>{document.type_label || selectedType.name}</td>
                        <td>{new Date(document.created_at).toLocaleDateString()}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </section>
          </section>
        </div>
      </main>
    </>
  );
}
