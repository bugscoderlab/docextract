"""TODO: map your schema to the stored record.

Money is not a domain — when a value is monetary, store it as an integer minor
unit with ``docextract.money.to_minor_units`` (never a float).
"""

from __future__ import annotations

from docextract.money import to_minor_units

from .schema import MyDocument


def to_record(document: MyDocument) -> dict:
    return {
        "doc_type": document.doc_type,
        "type_label": document.type_label,
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
        "total_minor": to_minor_units(document.total),
        "note": document.note,
    }
