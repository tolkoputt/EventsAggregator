from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from eventsaggregator.db.models import Event, Place, Sync
from eventsaggregator.schemas.events import PageParams


class EventRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def list_events(self, params: PageParams) -> tuple[list[Event], int]:
        total = await self.session.scalar(
            select(func.count())
            .select_from(Event)
            .where(Event.event_time >= params.date_from)
            if params.date_from
            else select(func.count()).select_from(Event)
        )

        stmt = (
            select(Event)
            .options(joinedload(Event.place))
            .order_by(Event.event_time)
            .limit(params.page_size)
            .offset(params.offset)
        )
        if params.date_from:
            stmt = stmt.where(Event.event_time >= params.date_from)
        items = (await self.session.scalars(stmt)).all()
        return list(items), total

    async def one_event(self, event_id: int) -> Event | None:
        stmt = (
            select(Event).options(joinedload(Event.place)).where(Event.id == event_id)
        )
        result = await self.session.scalar(stmt)
        return result

    async def event_status(self, event_id: int) -> str | None:
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
        self.session.merge(Place(**place.model_dump()))

    async def merge_event(self, event):
        self.session.merge(
            Event(**event.model_dump(exclude={"place"}), place_id=event.place.id)
        )

    async def merge_sync(self, now):
        self.session.merge(
            Sync(
                id=1,
                last_sync_time=now,
                last_changed_at=now.strftime("%Y-%m-%d"),
                sync_status=True,
            )
        )
