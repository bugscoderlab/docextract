"""TODO: your domain rules.

Composed *ahead of* the engine's ``BASE_PROMPT`` (the universal rules). Put
everything domain-specific here: the document kinds, the field vocabulary, money
handling, and anything the engine cannot know.
"""

from __future__ import annotations

DOMAIN_PROMPT = """You extract <your document kind> documents.

Rules:
- Classify the document into `doc_type`.
- Put header values in `fields` under these keys: <canonical field list>.
- Return every monetary value as an exact decimal string (no symbol, no separators).
- Capture every line item in order; keep the code separate from the description.
- Record the total number of pages as a plain number in `Pages`.
- Set `type_label` to "<Kind> · <short party> → <currency>".
- Put anything ambiguous or low-confidence in `note`.
"""
