"""Corrections: append, group into Revisions, effective values, append-only."""

from docextract import Correction, MemoryCorrectionStore, NullCorrectionStore
from docextract.corrections import apply_corrections, effective_values


def test_revision_groups_and_stamps_corrections():
    store = MemoryCorrectionStore()
    revision = store.append(
        "doc",
        "alice",
        [
            Correction(field_path="fields.Currency", old_value="USD", new_value="MYR"),
            Correction(field_path="total", old_value=5000, new_value=5100),
        ],
        note="fix currency",
    )

    assert revision.source_hash == "doc"
    assert revision.actor == "alice"
    assert revision.note == "fix currency"
    assert all(c.revision_id == revision.id for c in revision.corrections)
    assert store.revisions("doc") == [revision]


def test_apply_corrections_is_a_delta_and_copies():
    data = {"fields": {"Currency": "USD"}, "total": 5000, "lines": [{"amount": 100}]}
    corrections = [
        Correction(field_path="fields.Currency", new_value="MYR"),
        Correction(field_path="total", new_value=5100),
        Correction(field_path="lines.0.amount", new_value=120),
    ]

    effective = apply_corrections(data, corrections)

    assert effective["fields"]["Currency"] == "MYR"
    assert effective["total"] == 5100
    assert effective["lines"][0]["amount"] == 120
    # the original is untouched
    assert data["fields"]["Currency"] == "USD"
    assert data["total"] == 5000


def test_effective_values_reads_the_store():
    store = MemoryCorrectionStore()
    store.append("doc", "alice", [Correction(field_path="total", old_value=5000, new_value=5100)])

    assert effective_values(store, "doc", {"total": 5000})["total"] == 5100


def test_store_is_append_only_across_revisions():
    store = MemoryCorrectionStore()
    store.append("doc", "alice", [Correction(field_path="a", new_value=1)])
    store.append("doc", "bob", [Correction(field_path="a", new_value=2)])

    assert len(store.revisions("doc")) == 2
    assert len(store.corrections_for("doc")) == 2


def test_null_store_keeps_nothing_but_returns_a_revision():
    store = NullCorrectionStore()
    revision = store.append("doc", "alice", [Correction(field_path="a", new_value=1)])

    assert revision.corrections[0].revision_id == revision.id
    assert store.revisions("doc") == []
