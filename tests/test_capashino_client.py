from datetime import UTC, datetime
from uuid import UUID

import httpx
import pytest

from eventsaggregator.client.capashino import (
    CapashinoPermanentError,
    CapashinoProviderClient,
    CapashinoTransientError,
    NotificationAlreadyExists,
    NotificationCreated,
)

API_KEY = "test-api-key"
REFERENCE_ID = UUID("6d31a6f3-4190-4558-90b1-9c72d6e85111")
IDEMPOTENCY_KEY = "c3b459bb-bb37-4538-8a66-d8429cadf6ea"


def notification_payload():
    return {
        "id": "notification-1",
        "user_id": "user-1",
        "message": "Registered",
        "reference_id": str(REFERENCE_ID),
        "created_at": datetime.now(UTC).isoformat(),
        "idempotency_key": IDEMPOTENCY_KEY,
    }


@pytest.mark.asyncio
async def test_create_notification_sends_json_serializable_uuid_and_parses_created():
    requests = []

    def handler(request):
        requests.append(request)
        return httpx.Response(201, json=notification_payload())

    async with httpx.AsyncClient(
        transport=httpx.MockTransport(handler),
        base_url="https://capashino.test",
    ) as http_client:
        provider = CapashinoProviderClient(http_client, API_KEY)

        result = await provider.create_notifi(
            "Registered", REFERENCE_ID, IDEMPOTENCY_KEY
        )

    assert len(requests) == 1
    request = requests[0]
    assert request.method == "POST"
    assert request.url.path == "/api/notifications"
    assert request.headers["X-API-Key"] == API_KEY
    assert request.read() == (
        b'{"message":"Registered","reference_id":"'
        + str(REFERENCE_ID).encode()
        + b'","idempotency_key":"'
        + IDEMPOTENCY_KEY.encode()
        + b'"}'
    )
    assert isinstance(result, NotificationCreated)
    assert result.response.reference_id == REFERENCE_ID


@pytest.mark.asyncio
async def test_create_notification_treats_conflict_as_already_exists():
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(
            lambda request: httpx.Response(409, json={"detail": "duplicate"})
        ),
        base_url="https://capashino.test",
    ) as http_client:
        provider = CapashinoProviderClient(http_client, API_KEY)

        result = await provider.create_notifi(
            "Registered", REFERENCE_ID, IDEMPOTENCY_KEY
        )

    assert isinstance(result, NotificationAlreadyExists)


@pytest.mark.parametrize("status_code", [400, 401, 422])
@pytest.mark.asyncio
async def test_create_notification_treats_client_errors_as_permanent(status_code):
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(
            lambda request: httpx.Response(status_code, json={"detail": "rejected"})
        ),
        base_url="https://capashino.test",
    ) as http_client:
        provider = CapashinoProviderClient(http_client, API_KEY)

        with pytest.raises(CapashinoPermanentError):
            await provider.create_notifi("Registered", REFERENCE_ID, IDEMPOTENCY_KEY)


@pytest.mark.parametrize("status_code", [408, 429, 500, 503])
@pytest.mark.asyncio
async def test_create_notification_treats_temporary_statuses_as_retryable(status_code):
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(
            lambda request: httpx.Response(status_code, json={"detail": "temporary"})
        ),
        base_url="https://capashino.test",
    ) as http_client:
        provider = CapashinoProviderClient(http_client, API_KEY)

        with pytest.raises(CapashinoTransientError):
            await provider.create_notifi("Registered", REFERENCE_ID, IDEMPOTENCY_KEY)


@pytest.mark.asyncio
async def test_create_notification_treats_invalid_created_payload_as_transient():
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(
            lambda request: httpx.Response(201, json={"unexpected": "payload"})
        ),
        base_url="https://capashino.test",
    ) as http_client:
        provider = CapashinoProviderClient(http_client, API_KEY)

        with pytest.raises(CapashinoTransientError):
            await provider.create_notifi("Registered", REFERENCE_ID, IDEMPOTENCY_KEY)


@pytest.mark.asyncio
async def test_create_notification_wraps_transport_errors_as_transient():
    def handler(request):
        raise httpx.ConnectError("connection failed", request=request)

    async with httpx.AsyncClient(
        transport=httpx.MockTransport(handler),
        base_url="https://capashino.test",
    ) as http_client:
        provider = CapashinoProviderClient(http_client, API_KEY)

        with pytest.raises(CapashinoTransientError):
            await provider.create_notifi("Registered", REFERENCE_ID, IDEMPOTENCY_KEY)
