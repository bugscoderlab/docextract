"""TODO: your domain's output shape.

Add ``Field(description=...)`` to every field — the model uses those descriptions.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class Item(BaseModel):
    code: str = Field(default="", description="Item identifier, or empty if none is printed")
    description: str = Field(default="", description="Line description exactly as printed")
    qty: float | None = Field(default=None, description="Quantity")
    amount: str | None = Field(default=None, description="Line amount as an exact decimal string")


class Document(BaseModel):
    doc_type: str = Field(default="", description="Short machine kind for this document")
    fields: dict[str, str] = Field(default_factory=dict, description="Header values, keyed by a short label")
    items: list[Item] = Field(default_factory=list)
    total: str | None = Field(default=None, description="Stated total as an exact decimal string")
    note: str | None = Field(default=None, description="Anything ambiguous, missing, or low-confidence")
