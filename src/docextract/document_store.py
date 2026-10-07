"""Source-Document storage — the contract and the local implementations.

A Document is stored once, addressed by the ``source_hash`` of its bytes, so
re-uploading the same file is a no-op and an Extraction can point back at the
bytes the model read. The database holds metadata only; the bytes live here.

The backend is chosen by configuration (``DOCUMENT_STORAGE``): ``disk`` writes
under a local directory; ``off`` disables storage. An S3-compatible backend is
provided separately.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Protocol

from .mime import extension_for, mime_for_extension


class DocumentStore(Protocol):
    def put(self, source_hash: str, data: bytes, mime_type: str) -> str: ...
    def get(self, source_hash: str) -> bytes | None: ...
    def exists(self, source_hash: str) -> bool: ...
    def content_type(self, source_hash: str) -> str | None: ...
    def url(self, source_hash: str) -> str | None: ...
    def delete(self, source_hash: str) -> bool: ...
    def list(self) -> list[str]: ...


class NullDocumentStore:
    """Storage disabled: nothing is written or read."""

    def put(self, source_hash: str, data: bytes, mime_type: str) -> str:
        return ""

    def get(self, source_hash: str) -> bytes | None:
        return None

    def exists(self, source_hash: str) -> bool:
        return False

    def content_type(self, source_hash: str) -> str | None:
        return None

    def url(self, source_hash: str) -> str | None:
        return None

    def delete(self, source_hash: str) -> bool:
        return False

    def list(self) -> list[str]:
        return []


class DiskDocumentStore:
    """Content-addressed storage on the local filesystem.

    Objects live at ``<root>/<first two hash chars>/<hash><ext>``; the extension
    comes from the MIME type, so the same bytes always resolve to one object.
    """

    def __init__(self, root: Path):
        self._root = Path(root)

    def _key(self, source_hash: str, mime_type: str) -> str:
        return f"{source_hash[:2]}/{source_hash}{extension_for(mime_type)}"

    def _find(self, source_hash: str) -> Path | None:
        folder = self._root / source_hash[:2]
        if not folder.is_dir():
            return None
        matches = sorted(p for p in folder.iterdir() if p.is_file() and p.stem == source_hash)
        return matches[0] if matches else None

    def put(self, source_hash: str, data: bytes, mime_type: str) -> str:
        existing = self._find(source_hash)  # same bytes are one object, whatever the MIME
        if existing is not None:
            return f"{existing.parent.name}/{existing.name}"
        key = self._key(source_hash, mime_type)
        path = self._root / key
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return key

    def get(self, source_hash: str) -> bytes | None:
        path = self._find(source_hash)
        return path.read_bytes() if path is not None else None

    def exists(self, source_hash: str) -> bool:
        return self._find(source_hash) is not None

    def content_type(self, source_hash: str) -> str | None:
        path = self._find(source_hash)
        return mime_for_extension(path.suffix) if path is not None else None

    def url(self, source_hash: str) -> str | None:
        return f"/extract/documents/{source_hash}" if self.exists(source_hash) else None

    def delete(self, source_hash: str) -> bool:
        path = self._find(source_hash)
        if path is None:
            return False
        path.unlink()
        return True

    def list(self) -> list[str]:
        if not self._root.is_dir():
            return []
        return sorted(f"{p.parent.name}/{p.name}" for p in self._root.glob("*/*") if p.is_file())


def build_document_store(default_root: Path | None = None) -> DocumentStore:
    """Pick a store from ``DOCUMENT_STORAGE`` (disk | off). Defaults to disk.

    The disk root is ``default_root``, else ``DOCUMENT_STORAGE_DIR``, else
    ``./data/documents`` relative to the working directory.
    """
    kind = os.getenv("DOCUMENT_STORAGE", "disk").strip().lower()
    if kind in ("off", "none", "disabled", "false", "0"):
        return NullDocumentStore()
    if kind == "s3":
        from .document_store_s3 import build_s3_document_store

        return build_s3_document_store()
    configured = os.getenv("DOCUMENT_STORAGE_DIR")
    root = default_root or (Path(configured) if configured else Path.cwd() / "data" / "documents")
    return DiskDocumentStore(root)
