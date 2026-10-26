from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from eventsaggregator.db.models import Event, OutBox, Place, Sync, Tickets


class EventRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def commit(self):
        await self.session.commit()

    async def flush(self):
        await self.session.flush()

    async def list_events(
        self, date_from: datetime | None = None, page_size: int = 10, offset: int = 0
    ) -> tuple[list[Event], int]:
        total = await self.session.scalar(
            select(func.count()).select_from(Event).where(Event.event_time >= date_from)
            if date_from
            else select(func.count()).select_from(Event)
        )

        stmt = (
            select(Event)
            .options(joinedload(Event.place))
            .order_by(Event.event_time)
            .limit(page_size)
            .offset(offset)
        )
        if date_from:
            stmt = stmt.where(Event.event_time >= date_from)
        items = (await self.session.scalars(stmt)).all()
        return list(items), total if total is not None else 0

    async def one_event(self, event_id: UUID) -> Event | None:
        stmt = (
            select(Event).options(joinedload(Event.place)).where(Event.id == event_id)
        )
        result = await self.session.scalar(stmt)
        return result

    async def event_status(self, event_id: UUID) -> str | None:
        stmt = select(Event.status).where(Event.id == event_id)
        result = await self.session.scalar(stmt)
        return result

    async def lock_db(self):
        return await self.session.scalar(
            text("SELECT pg_try_advisory_xact_lock(:id)"), {"id": 7_351_001}
        )

    async def get_last_changed_at(self):
        if not await self.lock_db():
            return False

        last_changed_at = await self.session.scalar(
            select(Sync.last_changed_at).where(Sync.id == 1)
        )
        return last_changed_at

    async def merge_place(self, place):
        await self.session.merge(Place(**place.model_dump()))

    async def merge_event(self, event):
        await self.session.merge(
            Event(**event.model_dump(exclude={"place"}), place_id=event.place.id)
        )

    async def merge_sync(self, now):
        await self.session.merge(
            Sync(
                id=1,
                last_sync_time=now,
                last_changed_at=now.strftime("%Y-%m-%d"),
                sync_status=True,
            )
        )

    async def get_reg_deadline(self, event_id: UUID) -> datetime | None:
        stmt = select(Event.registration_deadline).where(Event.id == event_id)
        result = await self.session.scalar(stmt)
        return result

    async def merge_ticket(
        self,
        ticket_id: UUID,
        event_id: UUID,
        payload: dict[str, Any],
        date: datetime,
        idempotency_key: str,
    ):
        await self.session.merge(
            Tickets(
                ticket_id=ticket_id,
                event_id=event_id,
                payload=payload,
                created_at=date,
                idempotency_key=idempotency_key,
            )
        )

    async def get_event_id_by_ticket(self, ticket_id: UUID) -> UUID | None:
        stmt = select(Tickets.event_id).where(Tickets.ticket_id == ticket_id)
        result = await self.session.scalar(stmt)
        return result

    async def delete_ticket(self, ticket_id: UUID):
        stmt = select(Tickets).where(Tickets.ticket_id == ticket_id)
        ticket = await self.session.scalar(stmt)
        if ticket:
            await self.session.delete(ticket)

    async def check_idempotency_ticket(self, idempotency_key: str):
        return await self.session.scalar(
            select(Tickets.idempotency_key).where(
                Tickets.idempotency_key == idempotency_key
            )
        )

    async def check_ticket_payload(self, idempotency_key: str):
        return await self.session.scalar(
            select(Tickets.payload).where(Tickets.idempotency_key == idempotency_key)
        )

    async def get_ticket_id(self, idempotency_key: str):
        return await self.session.scalar(
            select(Tickets.ticket_id).where(Tickets.idempotency_key == idempotency_key)
        )

    async def update_outbox(
        self,
        id: UUID,
        operation_type: str,
        payload: dict[str, Any],
        status: bool,
        last_sync_time: datetime,
    ):
        await self.session.merge(
            OutBox(
                id=id,
                operation_type=operation_type,
                payload=payload,
                status=status,
                last_sync_time=last_sync_time,
            )
        )

    async def get_outbox(self, max_attempts: int) -> OutBox | None:
        stmt = (
            select(OutBox)
            .where(
                OutBox.status.is_(False),
                OutBox.attempt_count < max_attempts,
            )
            .order_by(OutBox.last_sync_time, OutBox.id)
            .limit(1)
            .with_for_update(skip_locked=True)
        )
        return await self.session.scalar(stmt)
