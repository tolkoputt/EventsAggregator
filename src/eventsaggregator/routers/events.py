from typing import Annotated
from uuid import UUID

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from eventsaggregator.core.cashe import EventsCache, get_cashe
from eventsaggregator.db.db import get_async_session
from eventsaggregator.db.query import event_status, list_events, one_event
from eventsaggregator.http.request import fetch_seats, get_http
from eventsaggregator.http.schemas import (
    EventOutSeatsPattern,
    Page,
    PageParams,
    Seats,
)

router = APIRouter(prefix="/events", tags=["events"])


@router.get("", response_model=Page)
async def get_events(
    request: Request,
    params: Annotated[PageParams, Query()],
    session: Annotated[AsyncSession, Depends(get_async_session)],
):
    items, total = await list_events(session, params)

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


@router.get("/{event_id}", response_model=EventOutSeatsPattern)
async def get_event(
    event_id: UUID,
    session: Annotated[AsyncSession, Depends(get_async_session)],
):
    result = await one_event(session, event_id)
    if not result:
        raise HTTPException(status_code=404, detail="Event not found")
    return result


@router.get("/{event_id}/seats", response_model=Seats)
async def get_event_seats(
    event_id: UUID,
    client: Annotated[httpx.AsyncClient, Depends(get_http)],
    session: Annotated[AsyncSession, Depends(get_async_session)],
    cashe: Annotated[EventsCache, Depends(get_cashe)],
) -> Seats:
    status = await event_status(session, event_id)
    if status != "published":
        raise HTTPException(status_code=404, detail="Event not published")

    result = await fetch_seats(client, event_id)
    if not result:
        raise HTTPException(status_code=404, detail="Event not found")

    cashe.set(str(event_id), result.seats)

    return Seats(event_id=event_id, available_seats=result.seats)
