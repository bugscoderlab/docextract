"""Schema injection and the ExtractionResult the engine returns.

A stub model stands in for the provider, so these tests are deterministic and
need neither LangChain nor an API key. The schema is a throwaway `Widget` — the
engine carries no domain.
"""

from stubs import CountingModel, Widget, stub_config

from docextract import DiskDocumentStore, ExtractionResult, Extractor, fingerprint, source_hash


def test_extract_text_wraps_data_in_result():
    widget = Widget(name="gadget", total="50.00")
    model = CountingModel(widget)

    result = Extractor(Widget, config=stub_config(), model=model).extract_text("WIDGET total 50.00")

    assert isinstance(result, ExtractionResult)
    assert model.bound is Widget
    assert result.data is widget
    assert result.status == "ok"
    assert result.cached is False
    assert result.mime_type == "text/plain"
    assert result.size_bytes == len(b"WIDGET total 50.00")
    assert result.source_hash == source_hash(b"WIDGET total 50.00")
    assert result.fingerprint == fingerprint(stub_config(), Widget)
    assert result.created_at.tzinfo is not None
    assert result.duration_ms >= 0


def test_none_result_is_an_explicit_empty():
    result = Extractor(Widget, config=stub_config(), model=CountingModel(None)).extract_text("blank page")
    assert result.status == "empty"
    assert result.data is None


def test_schema_is_injected_not_hardcoded():
    model = CountingModel(Widget(name="gadget"))
    result = Extractor(Widget, config=stub_config(), model=model).extract_text("a gadget")

    assert model.bound is Widget
    assert result.data == Widget(name="gadget")
    assert result.fingerprint == fingerprint(stub_config(), Widget)


def test_extract_hashes_bytes_and_guesses_mime(tmp_path):
    path = tmp_path / "doc.pdf"
    path.write_bytes(b"%PDF-1.4 hello")

    result = Extractor(Widget, config=stub_config(), model=CountingModel(Widget())).extract(str(path))

    assert result.mime_type == "application/pdf"
    assert result.source_hash == source_hash(b"%PDF-1.4 hello")
    assert result.size_bytes == len(b"%PDF-1.4 hello")


def test_text_like_file_keeps_raw_identity(tmp_path):
    raw = b'{"total": "50.00"}\n'
    path = tmp_path / "data.json"
    path.write_bytes(raw)

    result = Extractor(Widget, config=stub_config(), model=CountingModel(Widget())).extract(str(path))

    assert result.mime_type == "application/json"
    assert result.source_hash == source_hash(raw)
    assert result.size_bytes == len(raw)


def test_extract_file_persists_the_source_with_a_store(tmp_path):
    raw = b"%PDF-1.4 hello"
    path = tmp_path / "doc.pdf"
    path.write_bytes(raw)
    store = DiskDocumentStore(tmp_path / "store")

    result = Extractor(Widget, config=stub_config(), model=CountingModel(Widget()), store=store).extract(str(path))

    digest = source_hash(raw)
    assert result.storage_path == f"{digest[:2]}/{digest}.pdf"
    assert store.get(digest) == raw


def test_extract_text_does_not_persist_by_default():
    result = Extractor(Widget, config=stub_config(), model=CountingModel(Widget())).extract_text("plain text")
    assert result.storage_path is None
