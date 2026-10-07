"""The Domain descriptor — everything the engine needs to serve one document domain.

A consumer builds a ``Domain`` from its Pydantic schema, its domain prompt, and a
record mapper, then hands it to ``build_router`` and/or an ``Extractor``. The
engine itself stays domain-free: it never imports a concrete schema.

The ``build_*`` factories let a consumer wire DB-backed stores (and tests wire
stubs); when omitted, the engine falls back to no-op implementations.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel


def _default_record(data: BaseModel) -> dict[str, Any]:
    """Fallback mapper: the model as a plain dict, no domain shaping."""
    return data.model_dump()


@dataclass
class Domain:
    schema: type[BaseModel]
    prompt: str | None = None
    record: Callable[[BaseModel], dict[str, Any]] = _default_record
    build_extractor: Callable[[], Any] | None = None
    build_document_store: Callable[[], Any] | None = None
    build_correction_store: Callable[[], Any] | None = None
