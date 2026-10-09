"""Enforce one place per event.

Revision ID: 0002
Revises: 0001
Create Date: 2026-10-09
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.drop_index("ix_places_event_id", table_name="places")
    op.create_index("ix_places_event_id", "places", ["event_id"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_places_event_id", table_name="places")
    op.create_index("ix_places_event_id", "places", ["event_id"])
