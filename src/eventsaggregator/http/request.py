from uuid import UUID

import httpx
from fastapi import Request

from eventsaggregator.core.config import settings
from eventsaggregator.http.schemas import SeatsFromExtAPI, SyncTriggerResponse


def get_http(request: Request) -> httpx.AsyncClient:
    return request.app.state.http


async def fetch_events(
    client: httpx.AsyncClient, changed_at: str
) -> SyncTriggerResponse:
    response = await client.get(
        "/api/events/",
        params={"changed_at": changed_at},
        headers={"x-api-key": settings.EXTERNAL_API_KEY},
    )
    response.raise_for_status()
    return SyncTriggerResponse(**response.json())


async def fetch_next_events(
    client: httpx.AsyncClient, next_url: str
) -> SyncTriggerResponse:
    response = await client.get(
        next_url,
        headers={"x-api-key": settings.EXTERNAL_API_KEY},
    )
    response.raise_for_status()
    return SyncTriggerResponse(**response.json())


async def fetch_seats(client: httpx.AsyncClient, event_id: UUID) -> SeatsFromExtAPI:
    response = await client.get(
        f"/api/events/{event_id}/seats/",
        headers={"x-api-key": settings.EXTERNAL_API_KEY},
    )
    response.raise_for_status()
    print(response.json())
    return SeatsFromExtAPI(**response.json())
