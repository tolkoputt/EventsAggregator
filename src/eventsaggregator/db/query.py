from sqlalchemy import func, select
from sqlalchemy.orm import joinedload

from eventsaggregator.db.models import Event
from eventsaggregator.http.schemas import PageParams


async def list_events(session, params: PageParams) -> tuple[list[Event], int]:
    total = await session.scalar(
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
    items = (await session.scalars(stmt)).all()
    return list(items), total


async def one_event(session, event_id: int) -> Event | None:
    stmt = select(Event).options(joinedload(Event.place)).where(Event.id == event_id)
    result = await session.scalar(stmt)
    return result


async def event_status(session, event_id: int) -> str | None:
    stmt = select(Event.status).where(Event.id == event_id)
    result = await session.scalar(stmt)
    return result
