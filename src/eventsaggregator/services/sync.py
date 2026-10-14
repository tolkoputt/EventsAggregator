from datetime import UTC, datetime

from eventsaggregator.client.paginator import EventsPaginator
from eventsaggregator.client.provider import EventProviderClient
from eventsaggregator.db.repositories import EventRepository


class SyncService:
    def __init__(self, events: EventRepository, client: EventProviderClient):
        self.events = events
        self.client = client

    async def sync_events(self) -> bool:
        last_changed_at = await self.events.get_last_changed_at()
        if last_changed_at is False:
            return False

        results = []
        async for page in EventsPaginator(self.client, last_changed_at or "2000-01-01"):
            results.extend(page.results)

        places = {item.place.id: item.place for item in results}
        for place in places.values():
            await self.events.merge_place(place)
        await self.events.flush()

        for item in results:
            await self.events.merge_event(item)

        now = datetime.now(UTC)
        await self.events.merge_sync(now)

        await self.events.commit()
        return True
