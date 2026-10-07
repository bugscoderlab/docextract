"""Corrections and Revisions — the append-only human edit log.

A Correction is one field change (old -> new); a Revision groups the Corrections
saved in one commit. Corrections sit alongside the immutable cache: the effective
value of a field is the Extraction's value with Corrections applied in order.

Money is represented as integer minor units throughout — a monetary Correction
carries cents, never a float. Nothing here touches LangChain or SQLModel; the
SQLModel store lives in ``corrections_sqlmodel.py``.
"""

from __future__ import annotations

import copy
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Protocol
from uuid import uuid4


@dataclass
class Correction:
    field_path: str
    new_value: Any = None
    old_value: Any = None
    origin: str = "manual"  # "manual" | "model"
    actor: str = ""
    base_fingerprint: str = ""
    source_hash: str = ""
    revision_id: str = ""
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class Revision:
    id: str = field(default_factory=lambda: uuid4().hex)
    source_hash: str = ""
    actor: str = ""
    note: str | None = None
    base_fingerprint: str = ""
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    corrections: list[Correction] = field(default_factory=list)


class CorrectionStore(Protocol):
    def append(
        self,
        source_hash: str,
        actor: str,
        corrections: list[Correction],
        note: str | None = None,
        base_fingerprint: str = "",
    ) -> Revision: ...
    def revisions(self, source_hash: str) -> list[Revision]: ...
    def corrections_for(self, source_hash: str) -> list[Correction]: ...


def _new_revision(
    source_hash: str,
    actor: str,
    corrections: list[Correction],
    note: str | None,
    base_fingerprint: str,
) -> Revision:
    """Build a Revision and stamp its envelope onto every Correction."""
    revision = Revision(
        source_hash=source_hash,
        actor=actor,
        note=note,
        base_fingerprint=base_fingerprint,
        corrections=list(corrections),
    )
    for correction in revision.corrections:
        correction.source_hash = source_hash
        correction.revision_id = revision.id
        correction.actor = correction.actor or actor
        correction.base_fingerprint = correction.base_fingerprint or base_fingerprint
    return revision


class NullCorrectionStore:
    """Keeps nothing; appends still return a well-formed Revision."""

    def append(
        self,
        source_hash: str,
        actor: str,
        corrections: list[Correction],
        note: str | None = None,
        base_fingerprint: str = "",
    ) -> Revision:
        return _new_revision(source_hash, actor, corrections, note, base_fingerprint)

    def revisions(self, source_hash: str) -> list[Revision]:
        return []

    def corrections_for(self, source_hash: str) -> list[Correction]:
        return []


class MemoryCorrectionStore:
    """In-process store for tests."""

    def __init__(self) -> None:
        self._by_source: dict[str, list[Revision]] = {}

    def append(
        self,
        source_hash: str,
        actor: str,
        corrections: list[Correction],
        note: str | None = None,
        base_fingerprint: str = "",
    ) -> Revision:
        revision = _new_revision(source_hash, actor, corrections, note, base_fingerprint)
        self._by_source.setdefault(source_hash, []).append(revision)
        return revision

    def revisions(self, source_hash: str) -> list[Revision]:
        return list(self._by_source.get(source_hash, []))

    def corrections_for(self, source_hash: str) -> list[Correction]:
        return [c for revision in self._by_source.get(source_hash, []) for c in revision.corrections]


# --- effective values -------------------------------------------------------


def _key(part: str) -> Any:
    return int(part) if part.lstrip("-").isdigit() else part


def get_path(data: Any, path: str) -> Any:
    node = data
    for part in path.split("."):
        node = node[_key(part)]
    return node


def set_path(data: Any, path: str, value: Any) -> None:
    parts = path.split(".")
    node = data
    for part in parts[:-1]:
        node = node[_key(part)]
    node[_key(parts[-1])] = value


def apply_corrections(data: dict, corrections: list[Correction]) -> dict:
    """Return a deep copy of ``data`` with every Correction applied in order."""
    effective = copy.deepcopy(data)
    for correction in corrections:
        set_path(effective, correction.field_path, correction.new_value)
    return effective


def effective_values(store: CorrectionStore, source_hash: str, data: dict) -> dict:
    """The Extraction's data with everything recorded for this Document applied."""
    return apply_corrections(data, store.corrections_for(source_hash))
