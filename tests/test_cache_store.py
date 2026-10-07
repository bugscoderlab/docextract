"""The cache store contract: Null and Memory implementations."""

from datetime import datetime, timezone

from docextract.cache_store import CacheEntry, MemoryCache, NullCache, cache_key


def _entry(source_hash="s", fingerprint="f", result=None, status="ok") -> CacheEntry:
    return CacheEntry(
        source_hash=source_hash,
        fingerprint=fingerprint,
        provider="p",
        model="m",
        mime_type="text/plain",
        size_bytes=1,
        status=status,
        result=result,
        schema_name="x.Y",
        created_at=datetime.now(timezone.utc),
    )


def test_null_cache_never_stores():
    cache = NullCache()
    cache.put(_entry())
    assert cache.get("s", "f") is None
    assert cache.delete("s", "f") is False
    assert cache.delete_source("s") == 0
    assert cache.delete_fingerprint("f") == 0


def test_memory_cache_round_trip_and_insert_or_ignore():
    cache = MemoryCache()
    entry = _entry(result={"a": 1})
    cache.put(entry)
    assert cache.get("s", "f") is entry

    cache.put(_entry(result={"a": 2}))  # insert-or-ignore keeps the first
    assert cache.get("s", "f").result == {"a": 1}


def test_memory_cache_delete_variants():
    cache = MemoryCache()
    cache.put(_entry(source_hash="s1", fingerprint="f1"))
    cache.put(_entry(source_hash="s1", fingerprint="f2"))
    cache.put(_entry(source_hash="s2", fingerprint="f1"))

    assert cache.delete("s1", "f1") is True
    assert cache.get("s1", "f1") is None
    assert cache.delete("nope", "nope") is False
    assert cache.delete_source("s1") == 1  # s1/f2 remains
    assert cache.delete_fingerprint("f1") == 1  # s2/f1 remains


def test_cache_key_is_pair_specific_and_stable():
    assert cache_key("a", "b") == cache_key("a", "b")
    assert cache_key("a", "b") != cache_key("b", "a")
