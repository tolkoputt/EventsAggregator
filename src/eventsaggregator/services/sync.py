from sqlalchemy.ext.asyncio import AsyncSession

from eventsaggregator.db.models import Event, Place
from eventsaggregator.http.schemas import SyncTriggerResponse


async def save_events(session: AsyncSession, data: SyncTriggerResponse) -> None:
    for item in data.results:
        place = item.place
        await session.merge(
            Event(
                **item.model_dump(exclude={"place"}),
            )
        )
        await session.merge(Place(**place.model_dump(), event_id=item.id))
    await session.commit()
