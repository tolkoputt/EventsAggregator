from datetime import UTC, datetime
from uuid import UUID

from eventsaggregator.client.provider import EventProviderClient
from eventsaggregator.core.enums import EventStatus
from eventsaggregator.core.exceptions import (
    EventNotFound,
    EventNotPublished,
    InvalidSeat,
    RegistrationDeadlinePassed,
    TicketNotFound,
    TicketRegisterError,
    TicketUnequalPayload,
)
from eventsaggregator.db.repositories import EventRepository
from eventsaggregator.schemas.ticket import (
    DeleteTicketResponse,
    TicketRequest,
    TicketResponse,
)
from eventsaggregator.services.logic import is_valid_seat


class TicketService:
    def __init__(
        self,
        events: EventRepository,
        provider: EventProviderClient,
    ):
        self.events = events
        self.provider = provider

    async def get_ticket(self, data: TicketRequest):
        event = await self.events.one_event(data.event_id)
        if not event:
            raise EventNotFound
        if event.status != EventStatus.PUBLISHED:
            raise EventNotPublished
        if not event.registration_deadline > datetime.now(UTC):
            raise RegistrationDeadlinePassed

        try:
            if not is_valid_seat(event.place.seats_pattern, data.seat):
                raise InvalidSeat
        except ValueError:
            raise InvalidSeat

        registered_ticket = await self.provider.register_ticket(
            data.event_id,
            data.seat,
            data.first_name,
            data.last_name,
            data.email,
        )

        try:
            await self.events.merge_ticket(
                data.idempotency_key,
                data.event_id,
                registered_ticket.ticket_id,
                data.model_dump(),
                datetime.now(UTC),
            )
            await self.events.update_outbox(
                data.idempotency_key,
                "get",
                registered_ticket.model_dump(),
                False,
                datetime.now(UTC),
            )
        except Exception:  # noqa: BLE001
            await self.events.session.rollback()
            raise TicketRegisterError

        await self.events.session.commit()
        return TicketResponse(ticket_id=registered_ticket.ticket_id)

    async def delete_ticket(self, ticket_id: UUID):

        event_id = await self.events.get_event_id_by_ticket(ticket_id)
        if not event_id:
            raise TicketNotFound

        res = await self.provider.delete_ticket(event_id, ticket_id)
        if res.success:
            await self.events.delete_ticket(ticket_id)
            await self.events.commit()

        return DeleteTicketResponse(success=res.success)

    async def get_ticket_logic(self, data: TicketRequest) -> TicketResponse:
        if await self.events.check_idempotency_ticket(data.idempotency_key):
            payload = await self.events.check_ticket_payload(data.idempotency_key)
            if payload == data.model_dump():
                ticket_id = await self.events.get_ticket_id(data.idempotency_key)
                if ticket_id:
                    return TicketResponse(ticket_id=ticket_id)
                else:
                    raise TicketNotFound
            else:
                raise TicketUnequalPayload
        else:
            return await self.get_ticket(data)
