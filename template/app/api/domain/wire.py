"""TODO: wire the domain to the engine (DB-backed in production)."""

from __future__ import annotations

from typing import Any

from docextract import (
    Extractor,
    SQLModelCache,
    SQLModelCorrectionStore,
    build_document_store,
    build_router,
)
from docextract.domain import Domain

from .prompt import DOMAIN_PROMPT
from .record import to_record
from .schema import Document


def build_domain(engine: Any | None = None) -> Domain:
    if engine is None:
        return Domain(schema=Document, prompt=DOMAIN_PROMPT, record=to_record)
    return Domain(
        schema=Document,
        prompt=DOMAIN_PROMPT,
        record=to_record,
        build_document_store=build_document_store,
        build_extractor=lambda: Extractor(
            Document,
            cache=SQLModelCache(engine),
            store=build_document_store(),
            domain_prompt=DOMAIN_PROMPT,
        ),
        build_correction_store=lambda: SQLModelCorrectionStore(engine),
    )


def create_router(engine: Any | None = None):
    return build_router(build_domain(engine))
