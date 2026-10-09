import httpx
from fastapi import Request

from eventsaggregator.core.config import settings
from eventsaggregator.http.schemas import SyncTriggerResponse


def get_http(request: Request) -> httpx.AsyncClient:
    return request.app.state.http


async def fetch_events(client: httpx.AsyncClient) -> SyncTriggerResponse:
    response = await client.get(
        "/api/events/",
        params={"changed_at": "2026-01-01"},
        headers={"x-api-key": settings.EXTERNAL_API_KEY},
    )
    response.raise_for_status()
    return SyncTriggerResponse(**response.json())
