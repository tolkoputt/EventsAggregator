"""Use string idempotency keys for tickets.

Revision ID: 0007
Revises: 0006
Create Date: 2026-10-24
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0007"
down_revision: str | None = "0006"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "tickets",
        sa.Column("idempotency_key", sa.String(), nullable=True),
    )
    op.execute(
        """
        UPDATE tickets
        SET idempotency_key = CASE
            WHEN id IS NOT NULL AND id <> ticket_id THEN id::text
            ELSE ''
        END
        """
    )
    op.alter_column("tickets", "idempotency_key", nullable=False)

    op.drop_index("ix_tickets_id", table_name="tickets")
    op.drop_column("tickets", "id")
    op.create_index(
        "ix_tickets_idempotency_key",
        "tickets",
        ["idempotency_key"],
    )


def downgrade() -> None:
    op.add_column("tickets", sa.Column("id", sa.Uuid(), nullable=True))
    op.execute("UPDATE tickets SET id = ticket_id")
    op.alter_column("tickets", "id", nullable=False)

    op.drop_index("ix_tickets_idempotency_key", table_name="tickets")
    op.drop_column("tickets", "idempotency_key")
    op.create_index("ix_tickets_id", "tickets", ["id"])
