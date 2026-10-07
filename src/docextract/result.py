"""The reusable result object, plus the two identities an extraction is keyed by.

``source_hash`` identifies a Document by its content; ``fingerprint`` identifies
the recipe (provider, model, temperature, prompt, schema). Together they are the
cache key the next ticket builds on. This module has no LangChain dependency.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime
from typing import Generic, Literal, TypeVar

from pydantic import BaseModel

from .config import ExtractionConfig
from .prompts import BASE_PROMPT, FILE_INSTRUCTION

T = TypeVar("T", bound=BaseModel)

Status = Literal["ok", "empty"]


def source_hash(data: bytes) -> str:
    """Content identity of a Document: the sha256 of its bytes (filename is irrelevant)."""
    return hashlib.sha256(data).hexdigest()


def fingerprint(
    config: ExtractionConfig,
    schema: type[BaseModel],
    hint: str | None = None,
    system_prompt: str = BASE_PROMPT,
    file_instruction: str = FILE_INSTRUCTION,
) -> str:
    """Recipe identity: any change to provider, model, temperature, prompt, hint, or schema changes it."""
    payload = {
        "provider": config.provider,
        "model": config.model,
        "temperature": config.temperature,
        "system_prompt": system_prompt,
        "file_instruction": file_instruction,
        "hint": hint,
        "schema": schema.model_json_schema(),
    }
    blob = json.dumps(payload, sort_keys=True, default=str)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


@dataclass
class ExtractionResult(Generic[T]):
    """What an extraction returns: the data, how it went, and its identity."""

    data: T | None
    status: Status
    source_hash: str
    fingerprint: str
    mime_type: str
    size_bytes: int
    created_at: datetime
    duration_ms: int
    cached: bool = False
    storage_path: str | None = None
