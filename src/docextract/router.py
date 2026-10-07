"""FastAPI surface for an extraction domain — a router factory.

``build_router(domain)`` returns an ``APIRouter`` mounted at ``/extract``. The
engine resolves the extractor, the source-Document store, and the correction
store through the domain's zero-arg factories (tests substitute stubs; a consumer
wires its database). Nothing here imports a concrete schema.
"""

from __future__ import annotations

import os
from typing import Any

from fastapi import APIRouter, File, HTTPException, Response, UploadFile
from pydantic import BaseModel

from .config import ExtractionConfig
from .corrections import Correction, NullCorrectionStore, Revision
from .domain import Domain
from .mime import guess_mime_type, is_supported_mime, is_text_mime, looks_like

MAX_UPLOAD_BYTES = int(os.getenv("UPLOAD_MAX_BYTES", str(25 * 1024 * 1024)))


class TextIn(BaseModel):
    text: str
    hint: str | None = None


class CorrectionIn(BaseModel):
    field_path: str
    new_value: Any = None
    old_value: Any = None
    origin: str = "manual"


class RevisionIn(BaseModel):
    source_hash: str
    actor: str
    base_fingerprint: str = ""
    note: str | None = None
    corrections: list[CorrectionIn]


def _resolve_mime(file: UploadFile) -> str:
    """Prefer the filename's MIME; fall back to the declared content type."""
    guessed = guess_mime_type(file.filename or "")
    if is_supported_mime(guessed):
        return guessed
    declared = (file.content_type or "").split(";")[0].strip()
    return declared if is_supported_mime(declared) else guessed


def build_router(domain: Domain) -> APIRouter:
    """Build the ``/extract`` router for one domain."""

    def get_document_store() -> Any:
        if domain.build_document_store is not None:
            return domain.build_document_store()
        from .document_store import build_document_store

        return build_document_store()

    def get_extractor() -> Any:
        if domain.build_extractor is not None:
            return domain.build_extractor()
        from .cache_store import NullCache
        from .extractor import Extractor

        return Extractor(
            domain.schema,
            cache=NullCache(),
            store=get_document_store(),
            domain_prompt=domain.prompt,
        )

    def get_correction_store() -> Any:
        if domain.build_correction_store is not None:
            return domain.build_correction_store()
        return NullCorrectionStore()

    def _record(result: Any) -> dict:
        payload = {
            "source_hash": result.source_hash,
            "fingerprint": result.fingerprint,
            "status": result.status,
            "cached": result.cached,
            "mime_type": result.mime_type,
            "size_bytes": result.size_bytes,
            "storage_path": getattr(result, "storage_path", None),
        }
        if result.data is None:
            payload["data"] = None
        else:
            payload.update(domain.record(result.data))
        return payload

    def _revision_dict(revision: Revision) -> dict:
        return {
            "id": revision.id,
            "source_hash": revision.source_hash,
            "actor": revision.actor,
            "note": revision.note,
            "base_fingerprint": revision.base_fingerprint,
            "created_at": revision.created_at.isoformat(),
            "corrections": [
                {
                    "field_path": correction.field_path,
                    "old_value": correction.old_value,
                    "new_value": correction.new_value,
                    "origin": correction.origin,
                    "created_at": correction.created_at.isoformat(),
                }
                for correction in revision.corrections
            ],
        }

    def _load_stored(store: Any, source_hash: str) -> tuple[bytes, str]:
        data = store.get(source_hash)
        if data is None:
            raise HTTPException(status_code=404, detail="Document not found")
        return data, store.content_type(source_hash) or "application/octet-stream"

    router = APIRouter(prefix="/extract", tags=["extraction"])

    @router.get("/config")
    def show_config() -> dict:
        config = ExtractionConfig.from_env()
        return {"provider": config.provider, "model": config.model, "temperature": config.temperature}

    @router.post("/text")
    def extract_text_endpoint(body: TextIn) -> dict:
        try:
            result = get_extractor().extract_text(body.text, body.hint)
        except Exception as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc
        return _record(result)

    @router.post("/file")
    async def extract_file_endpoint(file: UploadFile = File(...)) -> dict:  # noqa: B008
        mime_type = _resolve_mime(file)
        if not is_supported_mime(mime_type):
            raise HTTPException(status_code=415, detail=f"Unsupported file type: {mime_type}")
        size = file.size
        if isinstance(size, int) and size > MAX_UPLOAD_BYTES:
            raise HTTPException(status_code=413, detail=f"File too large (max {MAX_UPLOAD_BYTES} bytes)")
        data = await file.read()
        if len(data) > MAX_UPLOAD_BYTES:
            raise HTTPException(
                status_code=413,
                detail=f"File too large: {len(data)} bytes (max {MAX_UPLOAD_BYTES})",
            )
        if not looks_like(mime_type, data):
            raise HTTPException(status_code=415, detail=f"File content does not match {mime_type}")
        try:
            extractor = get_extractor()
            if is_text_mime(mime_type):
                result = extractor.extract_text(
                    data.decode("utf-8", errors="replace"), mime_type=mime_type, raw=data, persist=True
                )
            else:
                result = extractor.extract_bytes(data, mime_type)
        except Exception as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc
        return _record(result)

    @router.get("/documents/{source_hash}")
    def get_document_endpoint(source_hash: str) -> Response:
        data, media_type = _load_stored(get_document_store(), source_hash)
        return Response(content=data, media_type=media_type)

    @router.delete("/documents/{source_hash}")
    def delete_document_endpoint(source_hash: str) -> dict:
        return {"deleted": get_document_store().delete(source_hash)}

    @router.post("/documents/{source_hash}/extract")
    def extract_stored_endpoint(source_hash: str, hint: str | None = None, force: bool = False) -> dict:
        data, mime_type = _load_stored(get_document_store(), source_hash)
        try:
            extractor = get_extractor()
            if is_text_mime(mime_type):
                result = extractor.extract_text(
                    data.decode("utf-8", errors="replace"),
                    hint,
                    mime_type=mime_type,
                    raw=data,
                    persist=True,
                    force=force,
                )
            else:
                result = extractor.extract_bytes(data, mime_type, hint, force=force)
        except Exception as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc
        return _record(result)

    @router.post("/corrections")
    def append_revision_endpoint(body: RevisionIn) -> dict:
        corrections = [
            Correction(
                field_path=item.field_path,
                old_value=item.old_value,
                new_value=item.new_value,
                origin=item.origin,
            )
            for item in body.corrections
        ]
        revision = get_correction_store().append(
            body.source_hash,
            body.actor,
            corrections,
            note=body.note,
            base_fingerprint=body.base_fingerprint,
        )
        return _revision_dict(revision)

    @router.get("/corrections/{source_hash}")
    def list_revisions_endpoint(source_hash: str) -> dict:
        return {
            "revisions": [_revision_dict(revision) for revision in get_correction_store().revisions(source_hash)]
        }

    return router
