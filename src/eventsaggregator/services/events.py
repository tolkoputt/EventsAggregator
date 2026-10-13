from uuid import UUID

from eventsaggregator.core.exceptions import EventNotFound
from eventsaggregator.db.models import Event
from eventsaggregator.db.repositories import EventRepository
from eventsaggregator.schemas.events import PageParams


class EventsService:
    def __init__(self, events: EventRepository):
        self.events = events

    async def get_event(self, event_id: UUID) -> Event:
        result = await self.events.one_event(event_id)
        if not result:
            raise EventNotFound
        return result

    async def list_events(self, params: PageParams) -> tuple[list[Event], int]:
        return await self.events.list_events(
            params.date_from, params.page_size, params.offset
        )
