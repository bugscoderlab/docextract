"""Source-Document store: disk and null implementations."""

from docextract import DiskDocumentStore, NullDocumentStore
from docextract.document_store import build_document_store


def _disk(tmp_path) -> DiskDocumentStore:
    return DiskDocumentStore(tmp_path / "documents")


def test_put_then_get_round_trips(tmp_path):
    store = _disk(tmp_path)
    digest = "a" * 64

    key = store.put(digest, b"%PDF-1.4 hello", "application/pdf")

    assert key == f"aa/{digest}.pdf"
    assert store.get(digest) == b"%PDF-1.4 hello"
    assert store.exists(digest) is True


def test_identical_bytes_are_not_duplicated(tmp_path):
    store = _disk(tmp_path)
    digest = "b" * 64

    store.put(digest, b"same", "image/png")
    store.put(digest, b"same", "image/png")

    assert store.list() == [f"bb/{digest}.png"]


def test_same_bytes_under_a_different_mime_are_one_object(tmp_path):
    store = _disk(tmp_path)
    digest = "b" * 64

    first = store.put(digest, b"same bytes", "application/pdf")
    second = store.put(digest, b"same bytes", "image/png")

    assert first == second
    assert len(store.list()) == 1


def test_delete_removes_the_object(tmp_path):
    store = _disk(tmp_path)
    digest = "c" * 64
    store.put(digest, b"x", "application/pdf")

    assert store.delete(digest) is True
    assert store.exists(digest) is False
    assert store.get(digest) is None
    assert store.delete(digest) is False


def test_unknown_mime_has_no_extension(tmp_path):
    store = _disk(tmp_path)
    digest = "d" * 64

    key = store.put(digest, b"x", "application/octet-stream")

    assert key == f"dd/{digest}"
    assert store.get(digest) == b"x"


def test_null_store_keeps_nothing():
    store = NullDocumentStore()
    digest = "e" * 64

    assert store.put(digest, b"x", "application/pdf") == ""
    assert store.get(digest) is None
    assert store.exists(digest) is False
    assert store.delete(digest) is False
    assert store.list() == []


def test_build_document_store_honours_config(tmp_path, monkeypatch):
    monkeypatch.setenv("DOCUMENT_STORAGE", "off")
    assert isinstance(build_document_store(), NullDocumentStore)

    monkeypatch.setenv("DOCUMENT_STORAGE", "disk")
    assert isinstance(build_document_store(tmp_path / "root"), DiskDocumentStore)
