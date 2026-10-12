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
