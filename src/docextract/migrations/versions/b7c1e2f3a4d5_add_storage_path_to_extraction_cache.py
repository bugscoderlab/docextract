"""add storage_path to extraction_cache

Revision ID: b7c1e2f3a4d5
Revises: 9d523dbb99d2
Create Date: 2026-10-06

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b7c1e2f3a4d5"
down_revision: str | Sequence[str] | None = "9d523dbb99d2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add the source-Document reference to the cache row."""
    op.add_column("extraction_cache", sa.Column("storage_path", sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column("extraction_cache", "storage_path")
