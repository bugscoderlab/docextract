"""MIME and file-extension helpers — no LangChain, no storage dependency.

Kept separate so the API layer can validate and label Documents without pulling
in the model framework.
"""

from __future__ import annotations

import mimetypes
import os

_EXT_BY_MIME = {
    "application/pdf": ".pdf",
    "image/png": ".png",
    "image/jpeg": ".jpg",
    "image/webp": ".webp",
    "image/gif": ".gif",
    "text/plain": ".txt",
    "application/json": ".json",
    "text/markdown": ".md",
    "text/csv": ".csv",
    "text/html": ".html",
}
_MIME_BY_EXT = {ext: mime for mime, ext in _EXT_BY_MIME.items()}
_TEXT_EXT = {".txt", ".md", ".csv", ".json", ".html"}


def extension_for(mime_type: str) -> str:
    """A file extension for a MIME type, or empty when unknown."""
    return _EXT_BY_MIME.get(mime_type, "")


def mime_for_extension(ext: str) -> str | None:
    """The MIME type for an extension such as ``.pdf``, or None when unknown."""
    return _MIME_BY_EXT.get((ext or "").lower())


def guess_mime_type(path: str) -> str:
    ext = os.path.splitext(path)[1].lower()
    return _EXT_BY_MIME.get(ext) or mimetypes.guess_type(path)[0] or "application/octet-stream"


def is_text_like(path: str) -> bool:
    """True when a file should be decoded and read as text rather than inlined."""
    return os.path.splitext(path)[1].lower() in _TEXT_EXT


def is_supported_mime(mime_type: str) -> bool:
    """True when the extractor can read this MIME type."""
    return mime_type in _EXT_BY_MIME


_TEXT_MIME = {"text/plain", "application/json", "text/markdown", "text/csv", "text/html"}

# Magic-byte prefixes for the binary families; text types have no signature.
_SIGNATURES = {
    "application/pdf": (b"%PDF",),
    "image/png": (b"\x89PNG\r\n\x1a\n",),
    "image/jpeg": (b"\xff\xd8\xff",),
    "image/gif": (b"GIF8",),
    "image/webp": (b"RIFF",),
}


def is_text_mime(mime_type: str) -> bool:
    """True when a Document of this MIME type should be read as decoded text."""
    return mime_type in _TEXT_MIME


def looks_like(mime_type: str, data: bytes) -> bool:
    """Cheap content sniff: does ``data`` plausibly match ``mime_type``?

    Text types and unknown types have no signature and always pass.
    """
    signatures = _SIGNATURES.get(mime_type)
    if not signatures:
        return True
    return any(data.startswith(signature) for signature in signatures)
