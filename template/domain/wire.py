"""TODO: wire the domain to the engine.

In production, pass your SQLAlchemy engine so the cache and correction log are
DB-backed and the source Documents are stored. With no engine, everything falls
back to no-op stores (handy for tests).
"""

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
from .schema import MyDocument


def build_domain(engine: Any | None = None) -> Domain:
    if engine is None:
        return Domain(schema=MyDocument, prompt=DOMAIN_PROMPT, record=to_record)
    return Domain(
        schema=MyDocument,
        prompt=DOMAIN_PROMPT,
        record=to_record,
        build_document_store=build_document_store,
        build_extractor=lambda: Extractor(
            MyDocument,
            cache=SQLModelCache(engine),
            store=build_document_store(),
            domain_prompt=DOMAIN_PROMPT,
        ),
        build_correction_store=lambda: SQLModelCorrectionStore(engine),
    )


def build_router_for(engine: Any | None = None):
    return build_router(build_domain(engine))
