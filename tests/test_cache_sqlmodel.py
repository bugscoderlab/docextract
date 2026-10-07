"""SQLModel-backed cache: persistence across extractors, delete, hit counting."""

from sqlmodel import create_engine
from stubs import CountingModel, Widget, stub_config

from docextract import Extractor
from docextract.cache_sqlmodel import SQLModelCache



def _engine(tmp_path):
    return create_engine(f"sqlite:///{tmp_path / 'cache.db'}")


def test_entry_survives_across_extractors(tmp_path):
    engine = _engine(tmp_path)
    Extractor(
        Widget, config=stub_config(), model=CountingModel(Widget(total="50.00")), cache=SQLModelCache(engine)
    ).extract_text("bytes")

    model = CountingModel(Widget(total="999.99"))
    result = Extractor(Widget, config=stub_config(), model=model, cache=SQLModelCache(engine)).extract_text("bytes")

    assert result.cached is True
    assert model.calls == 0
    assert result.data.total == "50.00"


def test_delete_removes_the_entry(tmp_path):
    cache = SQLModelCache(_engine(tmp_path))
    extractor = Extractor(Widget, config=stub_config(), model=CountingModel(Widget()), cache=cache)
    result = extractor.extract_text("bytes")

    assert cache.get(result.source_hash, result.fingerprint) is not None
    assert cache.delete(result.source_hash, result.fingerprint) is True
    assert cache.get(result.source_hash, result.fingerprint) is None


def test_hit_count_and_timestamp_persist(tmp_path):
    cache = SQLModelCache(_engine(tmp_path))
    extractor = Extractor(Widget, config=stub_config(), model=CountingModel(Widget()), cache=cache)
    first = extractor.extract_text("bytes")
    extractor.extract_text("bytes")

    entry = cache.get(first.source_hash, first.fingerprint)
    assert entry is not None and entry.hit_count == 1
    assert entry.last_hit_at is not None
