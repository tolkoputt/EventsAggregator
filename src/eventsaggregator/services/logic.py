# import typing
# from eventsaggregator.models import Event, EventStatus


# class EventsProviderClient(typing.Protocol):
#     async def register(self, event_id: str, first_name: str, seat: str) -> str: ...


# class TicketRepository(typing.Protocol):
#     async def create(self, event_id: str, ticket_id: str): ...


# class EventRepository(typing.Protocol):
#     async def get(self, event_id: str) -> Event | None: ...


# class CreateTicketUsecase:
#     def __init__(
#         self,
#         client: EventsProviderClient,
#         events: EventRepository,
#         tickets: TicketRepository,
#     ): ...

#     async def do(self, event_id: str, first_name: str, seat: str):
#         # Делаем дополнительную валидацию на своей стороне
#         event = await self.events.get(event_id)
#         if not event:
#             raise EventNotFound

#         if not event.status == EventStatus.published:
#             raise EventUnexpectedStatus

#         # Делаем запрос в сторонний сервис
#         ticket_id = await self.client.register(event.id, first_name, seat)

#         # Сохраняем в нашей БД
#         await self.tickets.create(event.id, ticket_id, first_name)
