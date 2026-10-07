"""SQLModel-backed cache store. Importing this module requires SQLModel.

Runs unchanged on SQLite (development, tests) and PostgreSQL (production). The
table is created idempotently on construction so the store is self-contained.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, cast

from sqlalchemy import JSON, Column, CursorResult, delete, update
from sqlalchemy.exc import IntegrityError
from sqlmodel import Field, Session, SQLModel, col

from .cache_store import CacheEntry, cache_key


class ExtractionCacheRow(SQLModel, table=True):
    __tablename__ = "extraction_cache"

    cache_key: str = Field(primary_key=True)
    source_hash: str = Field(index=True)
    fingerprint: str = Field(index=True)
    provider: str = ""
    model: str = ""
    mime_type: str = ""
    size_bytes: int = 0
    status: str = "ok"
    result: dict[str, Any] | None = Field(default=None, sa_column=Column(JSON, nullable=True))
    schema_name: str = ""
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    hit_count: int = 0
    last_hit_at: datetime | None = Field(default=None, nullable=True)
    storage_path: str | None = Field(default=None, nullable=True)


class SQLModelCache:
    def __init__(self, engine: Any):
        self._engine = engine
        SQLModel.metadata.tables["extraction_cache"].create(engine, checkfirst=True)

    @staticmethod
    def _to_entry(row: ExtractionCacheRow) -> CacheEntry:
        return CacheEntry(
            source_hash=row.source_hash,
            fingerprint=row.fingerprint,
            provider=row.provider,
            model=row.model,
            mime_type=row.mime_type,
            size_bytes=row.size_bytes,
            status=row.status,
            result=row.result,
            schema_name=row.schema_name,
            created_at=row.created_at,
            hit_count=row.hit_count,
            last_hit_at=row.last_hit_at,
            storage_path=row.storage_path,
        )

    def get(self, source_hash: str, fingerprint: str) -> CacheEntry | None:
        with Session(self._engine) as session:
            row = session.get(ExtractionCacheRow, cache_key(source_hash, fingerprint))
            return self._to_entry(row) if row is not None else None

    def put(self, entry: CacheEntry) -> None:
        row = ExtractionCacheRow(
            cache_key=cache_key(entry.source_hash, entry.fingerprint),
            source_hash=entry.source_hash,
            fingerprint=entry.fingerprint,
            provider=entry.provider,
            model=entry.model,
            mime_type=entry.mime_type,
            size_bytes=entry.size_bytes,
            status=entry.status,
            result=entry.result,
            schema_name=entry.schema_name,
            created_at=entry.created_at,
            hit_count=entry.hit_count,
            last_hit_at=entry.last_hit_at,
            storage_path=entry.storage_path,
        )
        with Session(self._engine) as session:
            session.add(row)
            try:
                session.commit()
            except IntegrityError:  # insert-or-ignore on the primary key
                session.rollback()

    def touch(self, source_hash: str, fingerprint: str) -> None:
        with Session(self._engine) as session:
            session.execute(
                update(ExtractionCacheRow)
                .where(col(ExtractionCacheRow.cache_key) == cache_key(source_hash, fingerprint))
                .values(
                    hit_count=col(ExtractionCacheRow.hit_count) + 1,
                    last_hit_at=datetime.now(timezone.utc),
                )
            )
            session.commit()

    def _delete_where(self, *criteria: Any) -> int:
        with Session(self._engine) as session:
            result = cast(CursorResult, session.execute(delete(ExtractionCacheRow).where(*criteria)))
            session.commit()
            return result.rowcount or 0

    def delete(self, source_hash: str, fingerprint: str) -> bool:
        return self._delete_where(
            ExtractionCacheRow.source_hash == source_hash,
            ExtractionCacheRow.fingerprint == fingerprint,
        ) > 0

    def delete_source(self, source_hash: str) -> int:
        return self._delete_where(ExtractionCacheRow.source_hash == source_hash)

    def delete_fingerprint(self, fingerprint: str) -> int:
        return self._delete_where(ExtractionCacheRow.fingerprint == fingerprint)
