from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from eventsaggregator.core.exceptions import (
    EventNotFound,
    EventNotPublished,
    InvalidSeat,
    RegistrationDeadlinePassed,
    TicketNotFound,
)
from eventsaggregator.deps import get_ticket_service
from eventsaggregator.schemas.ticket import (
    DeleteTicketResponse,
    TicketRequest,
    TicketResponse,
)
from eventsaggregator.services.ticket import TicketService

router = APIRouter(prefix="/tickets", tags=["tickets"])


@router.post("")
async def get_ticket(
    data: TicketRequest,
    ticket_service: Annotated[TicketService, Depends(get_ticket_service)],
) -> TicketResponse:
    try:
        return await ticket_service.get_ticket(data)
    except InvalidSeat:
        raise HTTPException(status_code=400, detail="Invalid seat")
    except EventNotPublished:
        raise HTTPException(status_code=400, detail="Event not published")
    except RegistrationDeadlinePassed:
        raise HTTPException(status_code=400, detail="Registration deadline passed")
    except EventNotFound:
        raise HTTPException(status_code=404, detail="Event not found")


@router.delete("/{ticket_id}")
async def delete_ticket(
    ticket_id: UUID,
    ticket_service: Annotated[TicketService, Depends(get_ticket_service)],
) -> DeleteTicketResponse:
    try:
        return await ticket_service.delete_ticket(ticket_id)
    except TicketNotFound:
        raise HTTPException(status_code=404, detail="Ticket not found")
