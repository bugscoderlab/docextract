"""S3-compatible Document store, exercised with an injected fake S3 client."""

from docextract.document_store_s3 import S3DocumentStore


class _FakeBody:
    def __init__(self, data: bytes):
        self._data = data

    def read(self) -> bytes:
        return self._data


class _FakeS3:
    def __init__(self) -> None:
        self.objects: dict[str, bytes] = {}

    def put_object(self, **kwargs):
        self.objects[kwargs["Key"]] = kwargs["Body"]

    def get_object(self, **kwargs):
        return {"Body": _FakeBody(self.objects[kwargs["Key"]])}

    def delete_object(self, **kwargs):
        self.objects.pop(kwargs["Key"], None)

    def list_objects_v2(self, **kwargs):
        prefix = kwargs.get("Prefix", "")
        return {"Contents": [{"Key": key} for key in self.objects if key.startswith(prefix)]}


def _store() -> S3DocumentStore:
    return S3DocumentStore("bucket", prefix="docs", client=_FakeS3())


def test_round_trip():
    store = _store()
    digest = "12" * 32

    key = store.put(digest, b"%PDF-1.4 hello", "application/pdf")

    assert key == f"docs/{digest}.pdf"
    assert store.exists(digest) is True
    assert store.get(digest) == b"%PDF-1.4 hello"
    assert store.content_type(digest) == "application/pdf"
    assert store.list() == [key]


def test_put_is_idempotent():
    store = _store()
    digest = "34" * 32
    store.put(digest, b"first", "image/png")
    store.put(digest, b"second", "image/png")
    assert store.get(digest) == b"first"


def test_delete():
    store = _store()
    digest = "56" * 32
    store.put(digest, b"x", "application/pdf")
    assert store.delete(digest) is True
    assert store.exists(digest) is False
    assert store.delete(digest) is False
