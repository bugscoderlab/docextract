"""TODO: your domain rules. Composed ahead of the engine's BASE_PROMPT."""

from __future__ import annotations

DOMAIN_PROMPT = """You extract <your document kind> documents.

Rules:
- Classify the document into `doc_type`.
- Put header values in `fields` under short, consistent keys.
- Return every monetary value as an exact decimal string (no symbol, no separators).
- Capture every line item in order; keep the code separate from the description.
- Put anything ambiguous or low-confidence in `note`.
"""
