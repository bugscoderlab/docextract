"""Turn a source (text / PDF / image) into LangChain messages.

The multimodal content-block shape is LangChain's provider-agnostic standard and
is isolated in ``file_content_block`` — if a future provider needs a different
shape, change only that one function. MIME helpers live in ``mime.py`` and are
re-exported here for callers that already depend on this module.
"""

from __future__ import annotations

import base64

from langchain_core.messages import HumanMessage, SystemMessage

from .mime import guess_mime_type, is_text_like
from .prompts import BASE_PROMPT, FILE_INSTRUCTION

__all__ = ["file_content_block", "file_messages", "guess_mime_type", "is_text_like", "text_messages"]


def file_content_block(mime_type: str, data: bytes) -> dict:
    """Inline a file/image as a LangChain standard content block."""
    kind = "image" if mime_type.startswith("image/") else "file"
    return {
        "type": kind,
        "source_type": "base64",
        "data": base64.b64encode(data).decode("ascii"),
        "mime_type": mime_type,
    }


def text_messages(text: str, hint: str | None = None, system_prompt: str = BASE_PROMPT):
    return [
        SystemMessage(system_prompt),
        HumanMessage(f"{hint or 'Extract the following document.'}\n\n---\n{text}"),
    ]


def file_messages(
    mime_type: str, data: bytes, hint: str | None = None, system_prompt: str = BASE_PROMPT
):
    return [
        SystemMessage(system_prompt),
        HumanMessage(
            content=[
                {"type": "text", "text": hint or FILE_INSTRUCTION},
                file_content_block(mime_type, data),
            ]
        ),
    ]
