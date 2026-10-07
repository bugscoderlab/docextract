"""Shared test doubles (no LangChain, no API key, no domain)."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel

from docextract.config import ExtractionConfig


class Widget(BaseModel):
    """A throwaway schema: the engine is domain-free, so tests use a toy model."""

    name: str = ""
    qty: float | None = None
    total: str | None = None
    note: str | None = None


class CountingModel:
    """Stands in for a chat model: records the bound schema and how often it ran."""

    def __init__(self, value: Any):
        self.value = value
        self.calls = 0
        self.bound: Any = None

    def with_structured_output(self, schema: Any) -> Any:
        self.bound = schema
        outer = self

        class _Runnable:
            def invoke(self, messages: Any) -> Any:
                outer.calls += 1
                return outer.value

        return _Runnable()


def stub_config(model: str = "stub-model") -> ExtractionConfig:
    return ExtractionConfig(provider="test", model=model, temperature=0.0)
