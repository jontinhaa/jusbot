"""add metadata JSONB to documents

Revision ID: 0002
Revises: 0001
Create Date: 2026-06-05
"""

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.add_column("documents", sa.Column("metadata", JSONB, nullable=True))


def downgrade() -> None:
    op.drop_column("documents", "metadata")
