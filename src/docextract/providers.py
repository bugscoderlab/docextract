"""Provider factory — the single place that knows about LangChain.

``init_chat_model`` already supports OpenAI, Anthropic, Google, Groq, Ollama and
more, provided the matching package is installed. So "changing the model in the
future" is a config change, not a code change:

    EXTRACTION_MODEL=gemini-2.5-flash
    EXTRACTION_MODEL=openai:gpt-4o-mini
    EXTRACTION_MODEL=ollama:llama3.1

Importing this module does not import LangChain; that happens inside the
function, so the app boots without the extraction extras installed.
"""

from __future__ import annotations

from typing import Any

from .config import ExtractionConfig


def build_chat_model(config: ExtractionConfig) -> Any:
    """Return a LangChain chat model for ``config``."""
    from langchain.chat_models import init_chat_model

    kwargs: dict[str, Any] = {
        "model": config.model,
        "model_provider": config.provider,
        "temperature": config.temperature,
    }
    if config.max_tokens is not None:
        kwargs["max_tokens"] = config.max_tokens
    if config.timeout is not None:
        kwargs["timeout"] = config.timeout
    return init_chat_model(**kwargs)
