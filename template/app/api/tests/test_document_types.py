"""Document-type settings + per-type listing, on a throwaway SQLite DB."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, create_engine

from docextract.cache_sqlmodel import ExtractionCacheRow
from routers.document_types import DocumentTypeSetting, create_document_types_router


@pytest.fixture()
def engine():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    ExtractionCacheRow.__table__.create(engine)
    return engine


@pytest.fixture()
def client(engine):
    app = FastAPI()
    app.include_router(create_document_types_router(engine))
    return TestClient(app)


def _seed_extraction(
    engine,
    source_hash: str,
    result: dict,
    *,
    fingerprint: str = "fp",
    storage_path: str | None = "docs/abc.pdf",
    created_at: datetime | None = None,
) -> None:
    row = ExtractionCacheRow(
        cache_key=f"{source_hash}:{fingerprint}",
        source_hash=source_hash,
        fingerprint=fingerprint,
        result=result,
        storage_path=storage_path,
        created_at=created_at or datetime.now(timezone.utc),
    )
    with Session(engine) as session:
        session.add(row)
        session.commit()


def test_types_start_empty(client):
    assert client.get("/document-types/").json() == []


def test_create_and_list(client):
    created = client.post("/document-types/", json={"name": "Bill of Lading", "remark": "Transport docs"})
    assert created.status_code == 201
    body = created.json()
    assert body["key"] == "bill_of_lading"
    assert body["name"] == "Bill of Lading"

    listed = client.get("/document-types/").json()
    assert [t["key"] for t in listed] == ["bill_of_lading"]


def test_create_rejects_duplicate_names(client):
    client.post("/document-types/", json={"name": "Sales Invoice"})
    response = client.post("/document-types/", json={"name": "sales  invoice!"})
    assert response.status_code == 409


def test_create_rejects_blank_key(client):
    response = client.post("/document-types/", json={"name": "☃"})
    assert response.status_code == 422


def test_update_renames_and_validates(client):
    client.post("/document-types/", json={"name": "Old Name"})
    response = client.put("/document-types/old_name", json={"name": "New Name", "remark": "  "})
    assert response.status_code == 200
    assert response.json()["name"] == "New Name"
    assert response.json()["remark"] is None  # blank remark stored as NULL

    assert client.put("/document-types/missing", json={"name": "X"}).status_code == 404


def test_update_rejects_conflict_with_another_type(client):
    client.post("/document-types/", json={"name": "One"})
    client.post("/document-types/", json={"name": "Two"})
    assert client.put("/document-types/one", json={"name": "Two"}).status_code == 409


def test_documents_match_by_doc_type_or_type_label(client, engine):
    client.post("/document-types/", json={"name": "Bill of Lading"})
    client.post("/document-types/", json={"name": "Sales Invoice"})
    _seed_extraction(engine, "h1", {"doc_type": "bill_of_lading", "type_label": ""})
    _seed_extraction(engine, "h2", {"doc_type": "", "type_label": "Bill of Lading · ACME → USD"})
    _seed_extraction(engine, "h3", {"doc_type": "sales_invoice", "type_label": ""})

    matches = client.get("/document-types/bill_of_lading/documents").json()
    assert {m["source_hash"] for m in matches} == {"h1", "h2"}
    assert matches[0]["file_name"] == "abc.pdf"


def test_documents_skip_unstored_and_dedupe_reextractions(client, engine):
    client.post("/document-types/", json={"name": "Sales Invoice"})
    old = datetime.now(timezone.utc) - timedelta(hours=1)
    _seed_extraction(engine, "h1", {"doc_type": "sales_invoice"}, storage_path=None)
    _seed_extraction(engine, "h2", {"doc_type": "sales_invoice", "type_label": "old"}, created_at=old)
    _seed_extraction(engine, "h2", {"doc_type": "sales_invoice", "type_label": "new"}, fingerprint="fp2")

    matches = client.get("/document-types/sales_invoice/documents").json()
    assert len(matches) == 1
    assert matches[0]["type_label"] == "new"


def test_documents_unknown_type_is_404(client):
    assert client.get("/document-types/missing/documents").status_code == 404
