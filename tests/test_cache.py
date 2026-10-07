"""Cache hit/miss, filename independence, recipe invalidation, empty, concurrency."""

import threading
import time

from stubs import CountingModel, Widget, stub_config

from docextract import Extractor, MemoryCache



def test_second_extraction_is_served_from_cache():
    model = CountingModel(Widget(total="50.00"))
    extractor = Extractor(Widget, config=stub_config(), model=model, cache=MemoryCache())

    first = extractor.extract_text("same bytes")
    second = extractor.extract_text("same bytes")

    assert first.cached is False
    assert second.cached is True
    assert model.calls == 1
    assert second.data == first.data
    assert second.source_hash == first.source_hash


def test_renamed_file_hits_the_same_entry(tmp_path):
    model = CountingModel(Widget())
    extractor = Extractor(Widget, config=stub_config(), model=model, cache=MemoryCache())
    a = tmp_path / "a.pdf"
    b = tmp_path / "b.pdf"
    a.write_bytes(b"%PDF same content")
    b.write_bytes(b"%PDF same content")

    extractor.extract(str(a))
    second = extractor.extract(str(b))

    assert second.cached is True
    assert model.calls == 1


def test_recipe_change_is_a_miss(tmp_path):
    cache = MemoryCache()
    path = tmp_path / "x.pdf"
    path.write_bytes(b"%PDF")

    Extractor(Widget, config=stub_config("model-a"), model=CountingModel(Widget()), cache=cache).extract(str(path))

    model_b = CountingModel(Widget())
    result = Extractor(Widget, config=stub_config("model-b"), model=model_b, cache=cache).extract(str(path))

    assert result.cached is False
    assert model_b.calls == 1


def test_empty_result_is_cached_and_not_rebilled():
    model = CountingModel(None)
    extractor = Extractor(Widget, config=stub_config(), model=model, cache=MemoryCache())

    first = extractor.extract_text("blank page")
    second = extractor.extract_text("blank page")

    assert first.status == "empty" and first.data is None
    assert second.status == "empty" and second.cached is True
    assert model.calls == 1


def test_force_bypasses_the_cache_and_replaces_the_entry():
    cache = MemoryCache()
    Extractor(Widget, config=stub_config(), model=CountingModel(Widget(total="50.00")), cache=cache).extract_text(
        "same bytes"
    )

    second_model = CountingModel(Widget(total="999.99"))
    forced = Extractor(Widget, config=stub_config(), model=second_model, cache=cache).extract_text(
        "same bytes", force=True
    )

    assert second_model.calls == 1
    assert forced.cached is False
    assert forced.data is not None and forced.data.total == "999.99"

    # the forced result replaced the entry — put() is insert-or-ignore, so a
    # later reader must see 999.99, not the original 50.00
    reader = CountingModel(Widget())
    after = Extractor(Widget, config=stub_config(), model=reader, cache=cache).extract_text("same bytes")
    assert after.cached is True
    assert reader.calls == 0
    assert after.data is not None and after.data.total == "999.99"


def test_hits_are_counted():
    cache = MemoryCache()
    extractor = Extractor(Widget, config=stub_config(), model=CountingModel(Widget()), cache=cache)

    first = extractor.extract_text("bytes")
    second = extractor.extract_text("bytes")
    entry = cache.get(first.source_hash, first.fingerprint)

    assert second.cached is True
    assert entry is not None and entry.hit_count == 1
    assert entry.last_hit_at is not None


def test_cache_hit_backfills_a_missing_source(tmp_path):
    from docextract import DiskDocumentStore

    cache = MemoryCache()
    store = DiskDocumentStore(tmp_path / "store")
    model = CountingModel(Widget())
    extractor = Extractor(Widget, config=stub_config(), model=model, cache=cache, store=store)
    path = tmp_path / "doc.pdf"
    path.write_bytes(b"%PDF-1.4 hello")

    first = extractor.extract(str(path))
    # Simulate a row cached before storage existed.
    cache.get(first.source_hash, first.fingerprint).storage_path = None
    store.delete(first.source_hash)

    second = extractor.extract(str(path))

    assert second.cached is True
    assert model.calls == 1
    assert second.storage_path is not None
    assert store.get(first.source_hash) == b"%PDF-1.4 hello"


def test_concurrent_same_document_makes_one_call():
    started = threading.Event()
    release = threading.Event()

    class _Blocking:
        calls = 0

        def with_structured_output(self, schema):
            outer = self

            class _Runnable:
                def invoke(self, messages):
                    outer.calls += 1
                    started.set()
                    release.wait(timeout=5)
                    return Widget()

            return _Runnable()

    model = _Blocking()
    extractor = Extractor(Widget, config=stub_config(), model=model, cache=MemoryCache())
    results = []

    first = threading.Thread(target=lambda: results.append(extractor.extract_text("same")))
    first.start()
    assert started.wait(timeout=5)

    second = threading.Thread(target=lambda: results.append(extractor.extract_text("same")))
    second.start()
    time.sleep(0.05)  # let the second thread block on the per-key lock
    release.set()
    first.join(timeout=5)
    second.join(timeout=5)

    assert model.calls == 1
    assert sorted(r.cached for r in results) == [False, True]
