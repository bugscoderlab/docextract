"""SQLModel-backed correction store. Importing this module requires SQLModel."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import JSON, Column
from sqlmodel import Field, Session, SQLModel, col, select

from .corrections import Correction, Revision, _new_revision


class RevisionRow(SQLModel, table=True):
    __tablename__ = "revision"

    id: str = Field(primary_key=True)
    source_hash: str = Field(index=True)
    actor: str = ""
    note: str | None = Field(default=None, nullable=True)
    base_fingerprint: str = ""
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class CorrectionRow(SQLModel, table=True):
    __tablename__ = "correction"

    id: int | None = Field(default=None, primary_key=True)
    revision_id: str = Field(index=True, foreign_key="revision.id")
    source_hash: str = Field(index=True)
    base_fingerprint: str = ""
    field_path: str = ""
    old_value: Any | None = Field(default=None, sa_column=Column(JSON, nullable=True))
    new_value: Any | None = Field(default=None, sa_column=Column(JSON, nullable=True))
    actor: str = ""
    origin: str = "manual"
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


def _to_correction(row: CorrectionRow) -> Correction:
    return Correction(
        field_path=row.field_path,
        new_value=row.new_value,
        old_value=row.old_value,
        origin=row.origin,
        actor=row.actor,
        base_fingerprint=row.base_fingerprint,
        source_hash=row.source_hash,
        revision_id=row.revision_id,
        created_at=row.created_at,
    )


class SQLModelCorrectionStore:
    def __init__(self, engine: Any):
        self._engine = engine
        for name in ("revision", "correction"):
            SQLModel.metadata.tables[name].create(engine, checkfirst=True)

    def append(
        self,
        source_hash: str,
        actor: str,
        corrections: list[Correction],
        note: str | None = None,
        base_fingerprint: str = "",
    ) -> Revision:
        revision = _new_revision(source_hash, actor, corrections, note, base_fingerprint)
        with Session(self._engine) as session:
            session.add(
                RevisionRow(
                    id=revision.id, source_hash=source_hash, actor=actor, note=note,
                    base_fingerprint=base_fingerprint, created_at=revision.created_at,
                )
            )
            for correction in revision.corrections:
                session.add(
                    CorrectionRow(
                        revision_id=revision.id, source_hash=source_hash,
                        base_fingerprint=correction.base_fingerprint, field_path=correction.field_path,
                        old_value=correction.old_value, new_value=correction.new_value,
                        actor=correction.actor, origin=correction.origin, created_at=correction.created_at,
                    )
                )
            session.commit()
        return revision

    def revisions(self, source_hash: str) -> list[Revision]:
        with Session(self._engine) as session:
            rows = session.exec(
                select(RevisionRow)
                .where(RevisionRow.source_hash == source_hash)
                .order_by(col(RevisionRow.created_at))
            ).all()
            revisions = [
                Revision(
                    id=row.id, source_hash=row.source_hash, actor=row.actor, note=row.note,
                    base_fingerprint=row.base_fingerprint, created_at=row.created_at,
                )
                for row in rows
            ]
            by_id = {revision.id: revision for revision in revisions}
            correction_rows = session.exec(
                select(CorrectionRow)
                .where(CorrectionRow.source_hash == source_hash)
                .order_by(col(CorrectionRow.created_at), col(CorrectionRow.id))
            ).all()
            for row in correction_rows:
                revision = by_id.get(row.revision_id)
                if revision is not None:
                    revision.corrections.append(_to_correction(row))
            return revisions

    def corrections_for(self, source_hash: str) -> list[Correction]:
        return [c for revision in self.revisions(source_hash) for c in revision.corrections]
