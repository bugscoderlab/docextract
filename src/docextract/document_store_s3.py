"""S3-compatible Document store for the VPS.

Importing this module does not import boto3; the client is created lazily (or
injected, which is how tests exercise it). Same content-addressed layout as the
disk store: ``<prefix>/<hash><ext>``.
"""

from __future__ import annotations

import os
import posixpath
from typing import Any

from .mime import extension_for, mime_for_extension


class S3DocumentStore:
    def __init__(self, bucket: str, prefix: str = "", client: Any | None = None):
        self._bucket = bucket
        self._prefix = prefix.strip("/")
        self._client = client

    @property
    def client(self) -> Any:
        if self._client is None:
            import boto3  # lazy: only imported when S3 storage actually runs

            self._client = boto3.client("s3", endpoint_url=os.getenv("S3_ENDPOINT_URL") or None)
        return self._client

    def _key(self, source_hash: str, mime_type: str) -> str:
        name = f"{source_hash}{extension_for(mime_type)}"
        return f"{self._prefix}/{name}" if self._prefix else name

    def _locate(self, source_hash: str) -> str | None:
        prefix = f"{self._prefix}/{source_hash}" if self._prefix else source_hash
        response = self.client.list_objects_v2(Bucket=self._bucket, Prefix=prefix)
        for item in response.get("Contents", []):
            return str(item["Key"])
        return None

    def put(self, source_hash: str, data: bytes, mime_type: str) -> str:
        key = self._key(source_hash, mime_type)
        if not self.exists(source_hash):  # insert-or-ignore
            self.client.put_object(
                Bucket=self._bucket,
                Key=key,
                Body=data,
                ContentType=mime_type or "application/octet-stream",
            )
        return key

    def get(self, source_hash: str) -> bytes | None:
        key = self._locate(source_hash)
        if key is None:
            return None
        response = self.client.get_object(Bucket=self._bucket, Key=key)
        body = response["Body"]
        return body.read() if hasattr(body, "read") else bytes(body)

    def exists(self, source_hash: str) -> bool:
        return self._locate(source_hash) is not None

    def content_type(self, source_hash: str) -> str | None:
        key = self._locate(source_hash)
        return mime_for_extension(posixpath.splitext(key)[1]) if key is not None else None

    def url(self, source_hash: str) -> str | None:
        return f"/extract/documents/{source_hash}" if self.exists(source_hash) else None

    def delete(self, source_hash: str) -> bool:
        key = self._locate(source_hash)
        if key is None:
            return False
        self.client.delete_object(Bucket=self._bucket, Key=key)
        return True

    def list(self) -> list[str]:
        prefix = f"{self._prefix}/" if self._prefix else ""
        response = self.client.list_objects_v2(Bucket=self._bucket, Prefix=prefix)
        return sorted(str(item["Key"]) for item in response.get("Contents", []))


def build_s3_document_store() -> S3DocumentStore:
    """Build an S3 store from ``S3_BUCKET`` / ``S3_PREFIX`` / ``S3_ENDPOINT_URL``."""
    bucket = os.getenv("S3_BUCKET", "").strip()
    if not bucket:
        raise RuntimeError("S3_BUCKET is required for DOCUMENT_STORAGE=s3")
    return S3DocumentStore(bucket=bucket, prefix=os.getenv("S3_PREFIX", ""))
