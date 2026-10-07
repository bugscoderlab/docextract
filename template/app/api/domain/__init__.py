"""The domain module: schema, prompt, record mapper, and wiring."""

from .prompt import DOMAIN_PROMPT
from .record import to_record
from .schema import Document, Item

__all__ = ["DOMAIN_PROMPT", "Document", "Item", "to_record"]
