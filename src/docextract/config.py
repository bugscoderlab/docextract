"""Extraction configuration — provider/model resolved from environment.

Dependency-light on purpose (os + dataclasses): importing this never needs
LangChain. Only ``providers.build_chat_model`` reaches into LangChain, and only
when an extraction is actually run. The engine reads process environment
variables; loading a ``.env`` file is the consumer's job.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, replace

DEFAULT_PROVIDER = "google_genai"
DEFAULT_MODEL = "gemini-2.5-flash"


def _float(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, default))
    except (TypeError, ValueError):
        return default


@dataclass(frozen=True)
class ExtractionConfig:
    """Everything provider-specific, in one swappable value."""

    provider: str = DEFAULT_PROVIDER
    model: str = DEFAULT_MODEL
    temperature: float = 0.0
    max_tokens: int | None = None
    timeout: float | None = 120.0

    @classmethod
    def from_env(cls) -> ExtractionConfig:
        raw = (os.getenv("EXTRACTION_MODEL") or DEFAULT_MODEL).strip()
        provider = (os.getenv("EXTRACTION_PROVIDER") or "").strip()
        model = raw
        if ":" in raw:  # "provider:model" wins over EXTRACTION_PROVIDER
            provider, model = (part.strip() for part in raw.split(":", 1))
        max_tokens = (os.getenv("EXTRACTION_MAX_TOKENS") or "").strip()
        return cls(
            provider=provider or DEFAULT_PROVIDER,
            model=model or DEFAULT_MODEL,
            temperature=_float("EXTRACTION_TEMPERATURE", 0.0),
            max_tokens=int(max_tokens) if max_tokens.isdigit() else None,
            timeout=_float("EXTRACTION_TIMEOUT", 120.0),
        )

    def replaced(self, **changes) -> ExtractionConfig:
        return replace(self, **changes)
