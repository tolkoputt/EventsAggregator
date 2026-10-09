"""Allow many events per place: move FK from places to events.

Revision ID: 0004
Revises: 0003
Create Date: 2026-10-10
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    # Данные — кэш внешнего API: очищаем и пересинхронизируем с нуля,
    # т.к. прежняя схема теряла связь события с местом.
    op.execute("TRUNCATE TABLE places, events, syncs")

    op.drop_index("ix_places_event_id", table_name="places")
    op.drop_column("places", "event_id")

    op.add_column("events", sa.Column("place_id", sa.Uuid(), nullable=False))
    op.create_index("ix_events_place_id", "events", ["place_id"])
    op.create_foreign_key(
        "fk_events_place_id", "events", "places", ["place_id"], ["id"]
    )


def downgrade() -> None:
    op.execute("TRUNCATE TABLE places, events, syncs")

    op.drop_constraint("fk_events_place_id", "events", type_="foreignkey")
    op.drop_index("ix_events_place_id", table_name="events")
    op.drop_column("events", "place_id")

    op.add_column("places", sa.Column("event_id", sa.Uuid(), nullable=False))
    op.create_foreign_key(
        "places_event_id_fkey", "places", "events", ["event_id"], ["id"]
    )
    op.create_index("ix_places_event_id", "places", ["event_id"], unique=True)
