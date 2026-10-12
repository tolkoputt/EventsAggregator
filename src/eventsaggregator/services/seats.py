from uuid import UUID

from eventsaggregator.client.provider import EventProviderClient
from eventsaggregator.core.exceptions import EventNotPublished
from eventsaggregator.db.repositories import EventRepository
from eventsaggregator.schemas.events import Seats


class SeatsService:
    def __init__(self, events: EventRepository, provider: EventProviderClient, cache):
        self.events = events
        self.provider = provider
        self.cache = cache

    async def get_seats(self, event_id: UUID) -> Seats:
        status = await self.events.event_status(event_id)
        if status != "published":
            raise EventNotPublished

        cached_seats = self.cache.get(str(event_id))
        if cached_seats is not None:
            return Seats(event_id=event_id, available_seats=cached_seats)

        result = await self.provider.fetch_seats(event_id)

        self.cache.set(str(event_id), result.seats)

        return Seats(event_id=event_id, available_seats=result.seats)
