from datetime import UTC, datetime

from eventsaggregator.client.provider import EventProviderClient
from eventsaggregator.client.schemas import RegisterTicket
from eventsaggregator.core.exceptions import (
    EventNotPublished,
    RegistrationDeadlinePassed,
)
from eventsaggregator.db.repositories import EventRepository
from eventsaggregator.schemas.ticket import TicketRequest


class TicketService:
    def __init__(self, events: EventRepository, provider: EventProviderClient):
        self.events = events
        self.provider = provider

    async def validation_seat(self, data: TicketRequest):
        event = await self.events.one_event(data.event_id)
        seats_pattern = event.place.seats_pattern
        seats_pattern = seats_pattern.split(",")
        for patt in seats_pattern:
            start, count_seat = patt.split("-")
            letter = start[0]
            if letter == data.seat[0] and int(data.seat[1:]) <= int(count_seat):
                return True
        return False

    async def get_ticket(self, data: TicketRequest) -> RegisterTicket:
        if not await self.validation_seat(data):
            raise ValueError("Invalid seat")

        status = await self.events.event_status(data.event_id)
        if status != "published":
            raise EventNotPublished

        if not await self.events.get_reg_deadline(data.event_id) > datetime.now(UTC):
            raise RegistrationDeadlinePassed

        return await self.provider.register_ticket(
            data.event_id,
            data.seat,
            data.first_name,
            data.last_name,
            data.email,
        )
