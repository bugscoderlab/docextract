"""Document-type settings and per-type document listing for this app.

Settings are this app's own table and start empty — a project defines its
document types in the UI. The per-type listing reads stored extraction
results from the engine's ``extraction_cache`` table and matches each record's
``doc_type`` / ``type_label``, which are part of this template's record shape.
"""

from __future__ import annotations

import re
import unicodedata
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from pydantic import Field as PayloadField
from sqlmodel import Field, Session, SQLModel, col, select

from docextract.cache_sqlmodel import ExtractionCacheRow


class DocumentTypeSetting(SQLModel, table=True):
    __tablename__ = "document_type_setting"

    key: str = Field(primary_key=True)
    name: str
    remark: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class DocumentTypePayload(BaseModel):
    name: str = PayloadField(min_length=1, max_length=120)
    remark: str | None = PayloadField(default=None, max_length=1000)


class TypeDocument(BaseModel):
    source_hash: str
    file_name: str
    type_label: str
    created_at: str


def _key_for_name(name: str) -> str:
    normalized = unicodedata.normalize("NFKD", name)
    ascii_name = normalized.encode("ascii", "ignore").decode("ascii")
    key = re.sub(r"[^a-z0-9]+", "_", ascii_name.lower()).strip("_")
    if not key:
        raise HTTPException(status_code=422, detail="Type of document needs at least one letter or number")
    return key


def _clean_remark(remark: str | None) -> str | None:
    if remark is None:
        return None
    cleaned = remark.strip()
    return cleaned or None


def _conflicting_type(
    session: Session, key: str, *, exclude_key: str | None = None
) -> DocumentTypeSetting | None:
    existing = session.get(DocumentTypeSetting, key)
    if existing is not None and existing.key != exclude_key:
        return existing
    for row in session.exec(select(DocumentTypeSetting)).all():
        if row.key != exclude_key and _key_for_name(row.name) == key:
            return row
    return None


def _record_matches_type(result: dict[str, Any], document_type: DocumentTypeSetting) -> bool:
    if result.get("doc_type") == document_type.key:
        return True
    type_label = str(result.get("type_label") or "")
    return type_label.split("·", 1)[0].strip().casefold() == document_type.name.casefold()


def create_document_types_router(engine: Any) -> APIRouter:
    """The ``/document-types`` router for one app database."""
    SQLModel.metadata.tables["document_type_setting"].create(engine, checkfirst=True)
    # Read the engine's cache table; create it idempotently like SQLModelCache does.
    SQLModel.metadata.tables["extraction_cache"].create(engine, checkfirst=True)

    router = APIRouter(prefix="/document-types", tags=["document-types"])

    @router.get("/")
    def list_document_types() -> list[DocumentTypeSetting]:
        with Session(engine) as session:
            return list(session.exec(select(DocumentTypeSetting).order_by(col(DocumentTypeSetting.name))).all())

    @router.post("/", status_code=201)
    def create_document_type(payload: DocumentTypePayload) -> DocumentTypeSetting:
        name = payload.name.strip()
        key = _key_for_name(name)
        with Session(engine) as session:
            if _conflicting_type(session, key) is not None:
                raise HTTPException(status_code=409, detail="A document type with this name already exists")
            now = datetime.now(timezone.utc)
            document_type = DocumentTypeSetting(key=key, name=name, remark=_clean_remark(payload.remark), created_at=now, updated_at=now)
            session.add(document_type)
            session.commit()
            session.refresh(document_type)
            return document_type

    @router.put("/{key}")
    def update_document_type(key: str, payload: DocumentTypePayload) -> DocumentTypeSetting:
        with Session(engine) as session:
            document_type = session.get(DocumentTypeSetting, key)
            if document_type is None:
                raise HTTPException(status_code=404, detail="Document type not found")
            name = payload.name.strip()
            duplicate_key = _key_for_name(name)
            if _conflicting_type(session, duplicate_key, exclude_key=key) is not None:
                raise HTTPException(status_code=409, detail="A document type with this name already exists")
            document_type.name = name
            document_type.remark = _clean_remark(payload.remark)
            document_type.updated_at = datetime.now(timezone.utc)
            session.add(document_type)
            session.commit()
            session.refresh(document_type)
            return document_type

    @router.get("/{key}/documents")
    def list_documents_for_type(key: str) -> list[TypeDocument]:
        with Session(engine) as session:
            document_type = session.get(DocumentTypeSetting, key)
            if document_type is None:
                raise HTTPException(status_code=404, detail="Document type not found")
            rows = session.exec(
                select(ExtractionCacheRow)
                .where(
                    col(ExtractionCacheRow.storage_path).is_not(None),
                    col(ExtractionCacheRow.result).is_not(None),
                )
                .order_by(col(ExtractionCacheRow.created_at))
            ).all()

        # Re-extractions share a source_hash; keep only the latest row per document.
        latest: dict[str, Any] = {}
        for row in rows:
            latest[row.source_hash] = row

        matches = []
        for row in sorted(latest.values(), key=lambda r: r.created_at, reverse=True):
            result = row.result or {}
            if not _record_matches_type(result, document_type):
                continue
            storage_path = row.storage_path or ""
            matches.append(
                TypeDocument(
                    source_hash=row.source_hash,
                    file_name=storage_path.rsplit("/", 1)[-1] or "—",
                    type_label=str(result.get("type_label") or document_type.name),
                    created_at=row.created_at.isoformat(),
                )
            )
        return matches

    return router
