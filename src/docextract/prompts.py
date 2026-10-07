"""Generic extraction prompts — the engine carries no domain knowledge.

A consumer supplies a *domain prompt* (schema field rules, domain vocabulary);
``compose_system_prompt`` places it ahead of these universal rules. The composed
prompt is part of the recipe fingerprint, so any wording change re-runs cached
Extractions.
"""

from __future__ import annotations

BASE_PROMPT = """You extract structured data from a document into the required schema.

Rules:
- Read the whole document — labelled pairs, address blocks, bullet lists, tables, \
headers and footers. Do not rely on "Label: value" lines alone.
- Transcribe only what is printed. Do not infer, correct, or compute values.
- Reproduce printed formats (dates, codes, identifiers, amounts) verbatim.
- Capture every item of a repeated group, in order.
- Flag anything ambiguous, missing, or low-confidence rather than guessing.
"""

FILE_INSTRUCTION = "Extract this document into the required structure."


def compose_system_prompt(domain_prompt: str | None = None) -> str:
    """Domain framing (if any) ahead of the generic rules."""
    if domain_prompt and domain_prompt.strip():
        return f"{domain_prompt.strip()}\n\n{BASE_PROMPT}"
    return BASE_PROMPT
