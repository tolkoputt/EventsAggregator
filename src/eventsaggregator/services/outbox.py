from eventsaggregator.db.repositories import EventRepository


class OutBoxService:
    def __init__(self, events: EventRepository) -> None:
        self.events = events

    async def worker(self): ...
