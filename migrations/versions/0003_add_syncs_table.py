"""Add syncs table.

Revision ID: 0003
Revises: 0002
Create Date: 2026-10-10
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "syncs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("last_sync_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_changed_at", sa.String(), nullable=False),
        sa.Column("sync_status", sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_syncs_last_changed_at", "syncs", ["last_changed_at"])


def downgrade() -> None:
    op.drop_index("ix_syncs_last_changed_at", table_name="syncs")
    op.drop_table("syncs")
