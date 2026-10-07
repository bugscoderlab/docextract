"""SQLModel correction store: persistence, ordering, read-back."""

from sqlmodel import create_engine

from docextract.corrections import Correction
from docextract.corrections_sqlmodel import SQLModelCorrectionStore


def _engine(tmp_path):
    return create_engine(f"sqlite:///{tmp_path / 'corrections.db'}")


def test_append_and_read_back(tmp_path):
    store = SQLModelCorrectionStore(_engine(tmp_path))
    store.append("doc", "alice", [Correction(field_path="total", old_value=5000, new_value=5100)], note="fix")

    revisions = store.revisions("doc")

    assert len(revisions) == 1
    assert revisions[0].actor == "alice"
    assert revisions[0].note == "fix"
    assert revisions[0].corrections[0].field_path == "total"
    assert revisions[0].corrections[0].new_value == 5100


def test_multiple_revisions_are_ordered(tmp_path):
    store = SQLModelCorrectionStore(_engine(tmp_path))
    store.append("doc", "alice", [Correction(field_path="a", new_value=1)])
    store.append("doc", "bob", [Correction(field_path="b", new_value=2)])

    assert len(store.revisions("doc")) == 2
    assert [c.field_path for c in store.corrections_for("doc")] == ["a", "b"]
