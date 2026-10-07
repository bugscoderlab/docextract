"""docextract — a domain-free LangChain extraction engine.

    from docextract import Extractor
    from docextract.domain import Domain

    # a consumer supplies its schema + domain prompt + record mapper
    domain = Domain(schema=MyModel, prompt=MY_DOMAIN_PROMPT, record=to_record)
    result = Extractor(MyModel, domain_prompt=MY_DOMAIN_PROMPT).extract("doc.pdf")

The engine is domain-agnostic — the output schema and its vocabulary are supplied
by the caller. Importing this package does not import LangChain or FastAPI;
``Extractor``, the SQLModel stores, and ``build_router`` are resolved lazily so a
consumer can install only what it uses.

Extractions are content-addressed cached (``cache_store.py``); money is
normalized to integer minor units in ``money.py``; the prompt is part of the
recipe fingerprint (``result.py``).
"""

from __future__ import annotations

import importlib
from typing import TYPE_CHECKING, Any

from .cache_store import CacheEntry, CacheStore, MemoryCache, NullCache, cache_key
from .config import ExtractionConfig
from .corrections import (
    Correction,
    CorrectionStore,
    MemoryCorrectionStore,
    NullCorrectionStore,
    Revision,
    apply_corrections,
    effective_values,
)
from .document_store import (
    DiskDocumentStore,
    DocumentStore,
    NullDocumentStore,
    build_document_store,
)
from .domain import Domain
from .money import from_minor_units, to_minor_units
from .result import ExtractionResult, fingerprint, source_hash

if TYPE_CHECKING:  # pragma: no cover - typing only
    from .extractor import Extractor

__all__ = [
    "CacheEntry",
    "CacheStore",
    "Correction",
    "CorrectionStore",
    "DiskDocumentStore",
    "DocumentStore",
    "Domain",
    "ExtractionConfig",
    "ExtractionResult",
    "Extractor",
    "MemoryCache",
    "MemoryCorrectionStore",
    "NullCache",
    "NullCorrectionStore",
    "NullDocumentStore",
    "Revision",
    "apply_corrections",
    "build_document_store",
    "cache_key",
    "effective_values",
    "fingerprint",
    "from_minor_units",
    "source_hash",
    "to_minor_units",
]

# name -> (submodule, attribute); imported on first use, never at package import
_LAZY: dict[str, tuple[str, str]] = {
    "Extractor": (".extractor", "Extractor"),
    "SQLModelCache": (".cache_sqlmodel", "SQLModelCache"),
    "SQLModelCorrectionStore": (".corrections_sqlmodel", "SQLModelCorrectionStore"),
    "build_router": (".router", "build_router"),
}


def __getattr__(name: str) -> Any:
    if name in _LAZY:
        module_name, attribute = _LAZY[name]
        value = getattr(importlib.import_module(module_name, __name__), attribute)
        globals()[name] = value
        return value
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
