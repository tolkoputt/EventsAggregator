from eventsaggregator.client.provider import EventProviderClient


class EventsPaginator:
    def __init__(self, client: EventProviderClient, changed_at: str):
        self.client = client
        self.changed_at = changed_at
        self.next_url = None
        self.is_first_page = True

    def __aiter__(self):
        return self

    async def __anext__(self):
        if self.is_first_page:
            page = await self.client.fetch_events(self.changed_at)
            self.is_first_page = False
        else:
            if self.next_url is None:
                raise StopAsyncIteration
            page = await self.client.fetch_next_events(self.next_url)

        self.next_url = page.next
        return page
