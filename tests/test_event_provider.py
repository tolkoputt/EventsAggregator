from uuid import UUID

import httpx
import pytest

from eventsaggregator.client.provider import EventProviderClient
from eventsaggregator.core.exceptions import ProviderError

API_KEY = "test-api-key"
EVENT_ID = UUID("1045417a-8597-4d37-9e7d-57c44576b871")
TICKET_ID = UUID("2045417a-8597-4d37-9e7d-57c44576b872")


def event_payload():
    return {
        "id": str(EVENT_ID),
        "name": "Test Event",
        "place": {
            "id": "3045417a-8597-4d37-9e7d-57c44576b873",
            "name": "Test Place",
            "city": "Yekaterinburg",
            "address": "1 Test Street",
            "seats_pattern": "A1-10",
            "changed_at": "2026-10-12T10:00:00Z",
            "created_at": "2026-10-11T10:00:00Z",
        },
        "event_time": "2026-11-01T18:00:00Z",
        "registration_deadline": "2026-10-31T18:00:00Z",
        "status": "published",
        "number_of_visitors": 10,
        "changed_at": "2026-10-12T10:00:00Z",
        "created_at": "2026-10-11T10:00:00Z",
        "status_changed_at": "2026-10-12T10:00:00Z",
    }


@pytest.mark.asyncio
async def test_fetch_events_sends_api_key_and_changed_at_parameter():
    requests = []

    def handler(request):
        requests.append(request)
        return httpx.Response(
            200,
            json={"next": None, "previous": None, "results": [event_payload()]},
        )

    async with httpx.AsyncClient(
        transport=httpx.MockTransport(handler),
        base_url="https://provider.test",
    ) as http_client:
        provider = EventProviderClient(http_client, API_KEY)

        result = await provider.fetch_events("2026-10-12")

    assert len(requests) == 1
    request = requests[0]
    assert request.method == "GET"
    assert request.url.path == "/api/events/"
    assert dict(request.url.params) == {"changed_at": "2026-10-12"}
    assert request.headers["x-api-key"] == API_KEY
    assert result.next is None
    assert result.previous is None
    assert len(result.results) == 1
    assert result.results[0].id == EVENT_ID
    assert result.results[0].place.name == "Test Place"


@pytest.mark.asyncio
async def test_fetch_next_events_requests_given_url():
    requests = []

    def handler(request):
        requests.append(request)
        return httpx.Response(
            200,
            json={"next": None, "previous": None, "results": []},
        )

    async with httpx.AsyncClient(
        transport=httpx.MockTransport(handler),
        base_url="https://provider.test",
    ) as http_client:
        provider = EventProviderClient(http_client, API_KEY)

        result = await provider.fetch_next_events(
            "https://provider.test/api/events/?cursor=next-page"
        )

    assert len(requests) == 1
    assert requests[0].method == "GET"
    assert str(requests[0].url) == (
        "https://provider.test/api/events/?cursor=next-page"
    )
    assert requests[0].headers["x-api-key"] == API_KEY
    assert result.results == []
    assert result.next is None


@pytest.mark.asyncio
async def test_fetch_seats_returns_parsed_seat_list():
    requests = []

    def handler(request):
        requests.append(request)
        return httpx.Response(200, json={"seats": ["A1", "A2", "B1"]})

    async with httpx.AsyncClient(
        transport=httpx.MockTransport(handler),
        base_url="https://provider.test",
    ) as http_client:
        provider = EventProviderClient(http_client, API_KEY)

        result = await provider.fetch_seats(EVENT_ID)

    assert len(requests) == 1
    assert requests[0].method == "GET"
    assert requests[0].url.path == f"/api/events/{EVENT_ID}/seats/"
    assert requests[0].headers["x-api-key"] == API_KEY
    assert result.seats == ["A1", "A2", "B1"]


@pytest.mark.asyncio
async def test_register_ticket_sends_ticket_data_and_parses_ticket_id():
    requests = []

    def handler(request):
        requests.append(request)
        return httpx.Response(200, json={"ticket_id": str(TICKET_ID)})

    async with httpx.AsyncClient(
        transport=httpx.MockTransport(handler),
        base_url="https://provider.test",
    ) as http_client:
        provider = EventProviderClient(http_client, API_KEY)

        result = await provider.register_ticket(
            EVENT_ID,
            "A1",
            "Ada",
            "Lovelace",
            "ada@example.com",
        )

    assert len(requests) == 1
    request = requests[0]
    assert request.method == "POST"
    assert request.url.path == f"/api/events/{EVENT_ID}/register/"
    assert request.headers["x-api-key"] == API_KEY
    assert request.read() == (
        b'{"first_name":"Ada","last_name":"Lovelace","seat":"A1",'
        b'"email":"ada@example.com"}'
    )
    assert result.ticket_id == TICKET_ID


@pytest.mark.asyncio
async def test_delete_ticket_sends_ticket_id_and_returns_success():
    requests = []

    def handler(request):
        requests.append(request)
        return httpx.Response(200, json={"success": True})

    async with httpx.AsyncClient(
        transport=httpx.MockTransport(handler),
        base_url="https://provider.test",
    ) as http_client:
        provider = EventProviderClient(http_client, API_KEY)

        result = await provider.delete_ticket(EVENT_ID, TICKET_ID)

    assert len(requests) == 1
    request = requests[0]
    assert request.method == "DELETE"
    assert request.url.path == f"/api/events/{EVENT_ID}/unregister/"
    assert request.headers["x-api-key"] == API_KEY
    assert request.read() == b'{"ticket_id":"' + str(TICKET_ID).encode() + b'"}'
    assert result.success is True


@pytest.mark.asyncio
async def test_http_error_is_raised_as_provider_error():
    def handler(request):
        return httpx.Response(503, json={"detail": "Unavailable"})

    async with httpx.AsyncClient(
        transport=httpx.MockTransport(handler),
        base_url="https://provider.test",
    ) as http_client:
        provider = EventProviderClient(http_client, API_KEY)

        with pytest.raises(ProviderError) as exc_info:
            await provider.fetch_seats(EVENT_ID)

    assert isinstance(exc_info.value.__cause__, httpx.HTTPStatusError)


@pytest.mark.asyncio
async def test_invalid_json_is_raised_as_provider_error():
    def handler(request):
        return httpx.Response(200, content=b"not-json")

    async with httpx.AsyncClient(
        transport=httpx.MockTransport(handler),
        base_url="https://provider.test",
    ) as http_client:
        provider = EventProviderClient(http_client, API_KEY)

        with pytest.raises(ProviderError) as exc_info:
            await provider.fetch_seats(EVENT_ID)

    assert isinstance(exc_info.value.__cause__, ValueError)
