from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from eventsaggregator.core.exceptions import EventNotFound, EventNotPublished
from eventsaggregator.deps import get_events_service, get_seats_service
from eventsaggregator.schemas.events import (
    EventOutSeatsPattern,
    Page,
    PageParams,
    Seats,
)
from eventsaggregator.services.events import EventsService
from eventsaggregator.services.seats import SeatsService

router = APIRouter(prefix="/events", tags=["events"])


@router.get("/{event_id}", response_model=EventOutSeatsPattern)
async def get_event(
    event_id: UUID,
    event_service: Annotated[EventsService, Depends(get_events_service)],
) -> EventOutSeatsPattern:
    result = await event_service.get_event(event_id)
    if not result:
        raise HTTPException(status_code=404, detail="Event not found")
    return result


@router.get("", response_model=Page)
async def get_events(
    request: Request,
    params: Annotated[PageParams, Query()],
    event_service: Annotated[EventsService, Depends(get_events_service)],
):
    items, total = await event_service.list_events(params)

    def link(page: int) -> str:
        return str(request.url.include_query_params(page=page))

    return Page(
        count=total,
        next=link(params.page + 1)
        if (params.page + 1) * params.page_size < total
        else None,
        previous=link(params.page - 1) if params.page > 1 else None,
        results=items,
    )


@router.get("/{event_id}/seats", response_model=Seats)
async def get_event_seats(
    event_id: UUID, seats_service: Annotated[SeatsService, Depends(get_seats_service)]
):
    try:
        return await seats_service.get_seats(event_id)
    except EventNotFound:
        raise HTTPException(404, "Event not found")
    except EventNotPublished:
        raise HTTPException(404, "Event not published")
