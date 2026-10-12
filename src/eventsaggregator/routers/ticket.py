from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from eventsaggregator.core.exceptions import (
    EventNotPublished,
    RegistrationDeadlinePassed,
)
from eventsaggregator.deps import get_ticket_service
from eventsaggregator.schemas.ticket import TicketRequest, TicketResponse
from eventsaggregator.services.ticket import TicketService

router = APIRouter(prefix="/tickets", tags=["tickets"])


@router.post("")
async def get_ticket(
    data: TicketRequest,
    ticket_service: Annotated[TicketService, Depends(get_ticket_service)],
) -> TicketResponse:
    try:
        return await ticket_service.get_ticket(data)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid seat")
    except EventNotPublished:
        raise HTTPException(status_code=400, detail="Event not published")
    except RegistrationDeadlinePassed:
        raise HTTPException(status_code=400, detail="Registration deadline passed")
