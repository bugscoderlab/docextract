"""Alembic migrations for the engine's own tables.

The engine owns the schema for ``extraction_cache``, ``revision`` and
``correction``. A consumer points its Alembic ``version_locations`` at
``version_locations()`` so these run alongside (or instead of) its own.
"""

from __future__ import annotations

from pathlib import Path


def version_locations() -> str:
    """Absolute path to the engine's migration scripts."""
    return str(Path(__file__).resolve().parent / "versions")
