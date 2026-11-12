import time
from uuid import UUID

import httpx

from eventsaggregator.client.schemas import (
    DeleteTicket,
    RegisterTicket,
    SeatsFromExtAPI,
    SyncTriggerResponse,
)
from eventsaggregator.core.exceptions import ProviderError
from eventsaggregator.services.metrics import (
    events_provider_request_duration_seconds,
    events_provider_requests_total,
)


class EventProviderClient:
    def __init__(self, client: httpx.AsyncClient, api_key: str):
        self.client = client
        self.api_key = api_key

    async def _request(self, method: str, url: str, **kwargs) -> dict:
        try:
            start_time = time.monotonic()
            response = await self.client.request(
                method, url, headers={"x-api-key": self.api_key}, **kwargs
            )
            response.raise_for_status()
            duration = time.monotonic() - start_time

            events_provider_requests_total.labels(
                endpoint=url, status=response.status_code
            ).inc()
            events_provider_request_duration_seconds.labels(
                endpoint=url,
            ).observe(duration)

            return response.json()
        except httpx.HTTPError as e:
            raise ProviderError(str(e)) from e
        except ValueError as e:
            raise ProviderError(str(e)) from e

    async def fetch_events(self, changed_at: str) -> SyncTriggerResponse:
        resp = await self._request(
            "GET",
            "/api/events/",
            params={"changed_at": changed_at},
        )
        return SyncTriggerResponse(**resp)

    async def fetch_next_events(self, next_url: str) -> SyncTriggerResponse:
        resp = await self._request(
            "GET",
            next_url,
        )
        return SyncTriggerResponse(**resp)

    async def fetch_seats(self, event_id: UUID) -> SeatsFromExtAPI:
        resp = await self._request("GET", f"/api/events/{event_id}/seats/")
        return SeatsFromExtAPI(**resp)

    async def register_ticket(
        self, event_id: UUID, seat: str, first_name: str, last_name: str, email: str
    ) -> RegisterTicket:
        resp = await self._request(
            "POST",
            f"/api/events/{event_id}/register/",
            json={
                "first_name": first_name,
                "last_name": last_name,
                "seat": seat,
                "email": email,
            },
        )
        return RegisterTicket(**resp)

    async def delete_ticket(self, event_id: UUID, ticket_id: UUID) -> DeleteTicket:
        resp = await self._request(
            "DELETE",
            f"/api/events/{event_id}/unregister/",
            json={"ticket_id": str(ticket_id)},
        )
        return DeleteTicket(**resp)
