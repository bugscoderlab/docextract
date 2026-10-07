"""Content-addressed extraction cache — the store contract and light impls.

A cache entry is keyed by ``source_hash`` (document content) and ``fingerprint``
(extractor recipe). The derived ``cache_key`` is the single primary key. Nothing
here touches LangChain or SQLModel; the SQLModel-backed store lives in
``cache_sqlmodel.py`` so the engine stays importable without a database.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Protocol


def cache_key(source_hash: str, fingerprint: str) -> str:
    """The single primary key: a hash of the content hash and the recipe fingerprint."""
    return hashlib.sha256(f"{source_hash}|{fingerprint}".encode()).hexdigest()


@dataclass
class CacheEntry:
    source_hash: str
    fingerprint: str
    provider: str
    model: str
    mime_type: str
    size_bytes: int
    status: str  # "ok" | "empty"
    result: dict | None
    schema_name: str
    created_at: datetime
    hit_count: int = 0
    last_hit_at: datetime | None = None
    storage_path: str | None = None


class CacheStore(Protocol):
    def get(self, source_hash: str, fingerprint: str) -> CacheEntry | None: ...
    def put(self, entry: CacheEntry) -> None: ...  # insert-or-ignore on the key
    def touch(self, source_hash: str, fingerprint: str) -> None: ...  # record a hit
    def delete(self, source_hash: str, fingerprint: str) -> bool: ...
    def delete_source(self, source_hash: str) -> int: ...
    def delete_fingerprint(self, fingerprint: str) -> int: ...


class NullCache:
    """Caching disabled: every lookup misses, nothing is stored."""

    def get(self, source_hash: str, fingerprint: str) -> CacheEntry | None:
        return None

    def put(self, entry: CacheEntry) -> None:
        return None

    def touch(self, source_hash: str, fingerprint: str) -> None:
        return None

    def delete(self, source_hash: str, fingerprint: str) -> bool:
        return False

    def delete_source(self, source_hash: str) -> int:
        return 0

    def delete_fingerprint(self, fingerprint: str) -> int:
        return 0


class MemoryCache:
    """In-process cache for tests and cache-free runs that still want reuse."""

    def __init__(self) -> None:
        self._items: dict[tuple[str, str], CacheEntry] = {}

    def get(self, source_hash: str, fingerprint: str) -> CacheEntry | None:
        return self._items.get((source_hash, fingerprint))

    def put(self, entry: CacheEntry) -> None:
        self._items.setdefault((entry.source_hash, entry.fingerprint), entry)

    def touch(self, source_hash: str, fingerprint: str) -> None:
        entry = self._items.get((source_hash, fingerprint))
        if entry is not None:
            entry.hit_count += 1
            entry.last_hit_at = datetime.now(timezone.utc)

    def delete(self, source_hash: str, fingerprint: str) -> bool:
        return self._items.pop((source_hash, fingerprint), None) is not None

    def delete_source(self, source_hash: str) -> int:
        keys = [k for k in self._items if k[0] == source_hash]
        for key in keys:
            del self._items[key]
        return len(keys)

    def delete_fingerprint(self, fingerprint: str) -> int:
        keys = [k for k in self._items if k[1] == fingerprint]
        for key in keys:
            del self._items[key]
        return len(keys)
