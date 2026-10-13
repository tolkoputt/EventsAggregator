from typing import Annotated

import httpx
from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from eventsaggregator.client.provider import EventProviderClient
from eventsaggregator.core.config import settings
from eventsaggregator.db.db import get_async_session
from eventsaggregator.db.repositories import EventRepository
from eventsaggregator.services.cache import EventsCache
from eventsaggregator.services.events import EventsService
from eventsaggregator.services.seats import SeatsService
from eventsaggregator.services.sync import SyncService
from eventsaggregator.services.ticket import TicketService


def get_http(request: Request) -> httpx.AsyncClient:
    return request.app.state.http


def get_provider(
    http: Annotated[httpx.AsyncClient, Depends(get_http)],
) -> EventProviderClient:
    return EventProviderClient(http, settings.EXTERNAL_API_KEY)


def get_cache(request: Request) -> EventsCache:
    return request.app.state.cache


def get_event_repo(
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> EventRepository:
    return EventRepository(session)


def get_events_service(
    repository: Annotated[EventRepository, Depends(get_event_repo)],
) -> EventsService:
    return EventsService(repository)


def get_sync_service(
    events: Annotated[EventRepository, Depends(get_event_repo)],
    client: Annotated[EventProviderClient, Depends(get_provider)],
) -> SyncService:
    return SyncService(events=events, client=client)


def get_seats_service(
    events: Annotated[EventRepository, Depends(get_event_repo)],
    provider: Annotated[EventProviderClient, Depends(get_provider)],
    cache: Annotated[EventsCache, Depends(get_cache)],
) -> SeatsService:
    return SeatsService(events=events, provider=provider, cache=cache)


def get_ticket_service(
    events: Annotated[EventRepository, Depends(get_event_repo)],
    provider: Annotated[EventProviderClient, Depends(get_provider)],
) -> TicketService:
    return TicketService(events=events, provider=provider)
