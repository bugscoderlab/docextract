"""TODO: map the schema to the record the UI reads: { fields, items, meta }.

Money is not a domain — store it as an integer minor unit via to_minor_units.
"""

from __future__ import annotations

from docextract.money import to_minor_units

from .schema import Document


def to_record(document: Document) -> dict:
    label = document.doc_type or (next(iter(document.fields.values()), ""))
    return {
        "fields": dict(document.fields),
        "items": [
            {
                "code": item.code,
                "description": item.description,
                "qty": item.qty,
                "amount_minor": to_minor_units(item.amount),
            }
            for item in document.items
        ],
        "meta": {
            "label": label,
            "total_minor": to_minor_units(document.total),
            "note": document.note,
        },
    }
