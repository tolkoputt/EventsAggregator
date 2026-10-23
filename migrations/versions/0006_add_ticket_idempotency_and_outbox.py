"""Add ticket idempotency data and outbox table.

Revision ID: 0006
Revises: 0005
Create Date: 2026-10-24
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0006"
down_revision: str | None = "0005"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("tickets", sa.Column("id", sa.Uuid(), nullable=True))
    op.add_column("tickets", sa.Column("payload", sa.JSON(), nullable=True))

    op.execute("UPDATE tickets SET id = ticket_id WHERE id IS NULL")
    op.execute("UPDATE tickets SET payload = '{}' WHERE payload IS NULL")

    op.alter_column("tickets", "id", nullable=False)
    op.alter_column("tickets", "payload", nullable=False)
    op.create_index("ix_tickets_id", "tickets", ["id"])

    op.create_table(
        "outbox",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("operation_type", sa.String(), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("status", sa.Boolean(), nullable=False),
        sa.Column("last_sync_time", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_outbox_status", "outbox", ["status"])


def downgrade() -> None:
    op.drop_index("ix_outbox_status", table_name="outbox")
    op.drop_table("outbox")
    op.drop_index("ix_tickets_id", table_name="tickets")
    op.drop_column("tickets", "payload")
    op.drop_column("tickets", "id")
