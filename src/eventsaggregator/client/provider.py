from uuid import UUID

import httpx

from eventsaggregator.client.schemas import (
    RegisterTicket,
    SeatsFromExtAPI,
    SyncTriggerResponse,
)


class EventProviderClient:
    def __init__(self, client: httpx.AsyncClient, api_key: str):
        self.client = client
        self.api_key = api_key

    async def fetch_events(self, changed_at: str) -> SyncTriggerResponse:
        response = await self.client.get(
            "/api/events/",
            params={"changed_at": changed_at},
            headers={"x-api-key": self.api_key},
        )
        response.raise_for_status()
        return SyncTriggerResponse(**response.json())

    async def fetch_next_events(self, next_url: str) -> SyncTriggerResponse:
        response = await self.client.get(
            next_url,
            headers={"x-api-key": self.api_key},
        )
        response.raise_for_status()
        return SyncTriggerResponse(**response.json())

    async def fetch_seats(self, event_id: UUID) -> SeatsFromExtAPI:
        response = await self.client.get(
            f"/api/events/{event_id}/seats/",
            headers={"x-api-key": self.api_key},
        )
        response.raise_for_status()
        print(response.json())
        return SeatsFromExtAPI(**response.json())

    async def register_ticket(
        self, event_id: UUID, seat: str, first_name: str, last_name: str, email: str
    ) -> None:
        response = await self.client.post(
            f"/api/events/{event_id}/register/",
            json={
                "first_name": first_name,
                "last_name": last_name,
                "seat": seat,
                "email": email,
            },
            headers={"x-api-key": self.api_key},
        )
        response.raise_for_status()
        return RegisterTicket(**response.json())
