"""The recyclable extraction entry point.

    from docextract import Extractor

    result = Extractor(MyModel, domain_prompt=MY_PROMPT).extract("doc.pdf")
    result.data     # -> MyModel | None
    result.cached   # -> served from cache?

The output schema is supplied by the caller, so the engine carries no domain
knowledge. Extractions are cached by document content x recipe fingerprint, so
re-reading the same Document (or re-running the same recipe) is free.
"""

from __future__ import annotations

import threading
import time
from collections.abc import Callable
from datetime import datetime, timezone
from typing import Any, Generic, TypeVar

from pydantic import BaseModel

from .cache_store import CacheEntry, CacheStore, NullCache, cache_key
from .config import ExtractionConfig
from .document_store import DocumentStore, NullDocumentStore
from .loaders import file_messages, guess_mime_type, is_text_like, text_messages
from .prompts import compose_system_prompt
from .providers import build_chat_model
from .result import ExtractionResult, fingerprint, source_hash

T = TypeVar("T", bound=BaseModel)

# In-process in-flight registry: two concurrent calls for the same key share one
# model call. Multi-worker duplicate work is a performance cost, not a defect.
_KEY_LOCKS_GUARD = threading.Lock()
_KEY_LOCKS: dict[str, threading.Lock] = {}


def _lock_for(key: str) -> threading.Lock:
    with _KEY_LOCKS_GUARD:
        lock = _KEY_LOCKS.get(key)
        if lock is None:
            lock = threading.Lock()
            _KEY_LOCKS[key] = lock
        return lock


class Extractor(Generic[T]):
    def __init__(
        self,
        schema: type[T],
        config: ExtractionConfig | None = None,
        model: Any | None = None,
        cache: CacheStore | None = None,
        store: DocumentStore | None = None,
        domain_prompt: str | None = None,
    ):
        self.schema = schema
        self.config = config or ExtractionConfig.from_env()
        self._model = model
        self.cache: CacheStore = cache or NullCache()
        self.store: DocumentStore = store or NullDocumentStore()
        # Domain framing supplied by the caller; the engine itself is domain-free.
        self.system_prompt = compose_system_prompt(domain_prompt)

    @property
    def model(self) -> Any:
        if self._model is None:
            self._model = build_chat_model(self.config)
        return self._model

    def _structured(self) -> Any:
        return self.model.with_structured_output(self.schema)

    def _entry(self, result: ExtractionResult[T], data: T | None) -> CacheEntry:
        return CacheEntry(
            source_hash=result.source_hash,
            fingerprint=result.fingerprint,
            provider=self.config.provider,
            model=self.config.model,
            mime_type=result.mime_type,
            size_bytes=result.size_bytes,
            status=result.status,
            result=data.model_dump() if data is not None else None,
            schema_name=f"{self.schema.__module__}.{self.schema.__qualname__}",
            created_at=result.created_at,
            storage_path=result.storage_path,
        )

    def _extract(
        self,
        raw: bytes,
        mime_type: str,
        invoke: Callable[[], T | None],
        hint: str | None = None,
        persist: bool = False,
        force: bool = False,
    ) -> ExtractionResult[T]:
        started = time.perf_counter()
        content = source_hash(raw)
        recipe = fingerprint(self.config, self.schema, hint, self.system_prompt)

        with _lock_for(cache_key(content, recipe)):
            # force bypasses the read but not the write: the fresh result replaces
            # the entry for this recipe, so later reads see the re-extraction.
            hit = None if force else self.cache.get(content, recipe)
            if hit is not None:
                self.cache.touch(content, recipe)
                data = self.schema.model_validate(hit.result) if hit.result is not None else None
                storage_path = hit.storage_path
                if persist and not storage_path:
                    # A row cached before storage existed: keep the bytes now so the
                    # Document can be shown and re-extracted.
                    storage_path = self.store.put(content, raw, mime_type) or None
                return ExtractionResult(
                    data=data,
                    status=hit.status,  # type: ignore[arg-type]
                    source_hash=content,
                    fingerprint=recipe,
                    mime_type=hit.mime_type,
                    size_bytes=hit.size_bytes,
                    created_at=hit.created_at,
                    duration_ms=int((time.perf_counter() - started) * 1000),
                    cached=True,
                    storage_path=storage_path,
                )

            # A raising invoke() propagates before put(), so failures are never cached.
            data = invoke()
            storage_path = (self.store.put(content, raw, mime_type) or None) if persist else None
            result: ExtractionResult[T] = ExtractionResult(
                data=data,
                status="empty" if data is None else "ok",
                source_hash=content,
                fingerprint=recipe,
                mime_type=mime_type,
                size_bytes=len(raw),
                created_at=datetime.now(timezone.utc),
                duration_ms=int((time.perf_counter() - started) * 1000),
                storage_path=storage_path,
            )
            if force:
                # put() is insert-or-ignore, so drop the stale row first — a forced
                # re-run must be observable to the next reader.
                self.cache.delete(content, recipe)
            self.cache.put(self._entry(result, data))
            return result

    def extract_text(
        self,
        text: str,
        hint: str | None = None,
        *,
        mime_type: str = "text/plain",
        raw: bytes | None = None,
        persist: bool = False,
        force: bool = False,
    ) -> ExtractionResult[T]:
        raw_bytes = raw if raw is not None else text.encode("utf-8")
        return self._extract(
            raw_bytes,
            mime_type,
            lambda: self._structured().invoke(text_messages(text, hint, self.system_prompt)),
            hint,
            persist,
            force,
        )

    def extract_file(self, path: str, hint: str | None = None, *, force: bool = False) -> ExtractionResult[T]:
        mime_type = guess_mime_type(path)
        with open(path, "rb") as handle:
            raw = handle.read()
        return self._extract(
            raw,
            mime_type,
            lambda: self._structured().invoke(file_messages(mime_type, raw, hint, self.system_prompt)),
            hint,
            True,
            force,
        )

    def extract_bytes(
        self, data: bytes, mime_type: str, hint: str | None = None, *, force: bool = False
    ) -> ExtractionResult[T]:
        """Extract from in-memory Document bytes, e.g. a Document already stored."""
        return self._extract(
            data,
            mime_type,
            lambda: self._structured().invoke(file_messages(mime_type, data, hint, self.system_prompt)),
            hint,
            True,
            force,
        )

    def extract(self, source: str, hint: str | None = None, *, force: bool = False) -> ExtractionResult[T]:
        """Auto-route a file path: text-like is decoded and read as text, else inlined.

        Identity (``source_hash``, ``size_bytes``) is always computed from the raw
        file bytes, so a text-like source hashes the same as any other.
        """
        if is_text_like(source):
            with open(source, "rb") as handle:
                raw = handle.read()
            return self.extract_text(
                raw.decode("utf-8", errors="replace"),
                hint,
                mime_type=guess_mime_type(source),
                raw=raw,
                persist=True,
                force=force,
            )
        return self.extract_file(source, hint, force=force)
