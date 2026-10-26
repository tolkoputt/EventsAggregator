from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import UUID

import pytest

from eventsaggregator.client.capashino import (
    CapashinoPermanentError,
    CapashinoTransientError,
    NotificationAlreadyExists,
    NotificationCreated,
)
from eventsaggregator.client.schemas import CapashinoResponse
from eventsaggregator.services.outbox import MAX_ATTEMPTS, OutBoxService

TICKET_ID = UUID("6d31a6f3-4190-4558-90b1-9c72d6e85111")
OUTBOX_ID = UUID("c3b459bb-bb37-4538-8a66-d8429cadf6ea")


class FakeSession:
    async def commit(self):
        pass


class RecordingSession(FakeSession):
    def __init__(self):
        self.commit_count = 0

    async def commit(self):
        self.commit_count += 1


class FakeRepository:
    def __init__(self, payload):
        self.session = RecordingSession()
        self.entry = SimpleNamespace(
            id=OUTBOX_ID,
            operation_type="get",
            payload=payload,
            status=False,
            last_sync_time=datetime.now(UTC),
            attempt_count=0,
        )

    async def get_outbox(self, max_attempts):
        if not self.entry.status and self.entry.attempt_count < max_attempts:
            return self.entry
        return None

    async def get_event_id_by_ticket(self, ticket_id):
        return UUID("1045417a-8597-4d37-9e7d-57c44576b871")

    async def one_event(self, event_id):
        return SimpleNamespace(name="Concert")


class FakeClient:
    def __init__(self, outcomes):
        self.outcomes = iter(outcomes)
        self.keys = []

    async def create_notifi(self, message, reference_id, idempotency_key):
        self.keys.append(idempotency_key)
        outcome = next(self.outcomes)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


def valid_payload():
    return {"ticket_id": str(TICKET_ID)}


def created_result():
    return NotificationCreated(
        CapashinoResponse(
            id="notification-1",
            user_id="user-1",
            message="Registered",
            reference_id=TICKET_ID,
            created_at=datetime.now(UTC),
            idempotency_key=str(OUTBOX_ID),
        )
    )


@pytest.mark.asyncio
async def test_worker_stops_retrying_after_max_attempts():
    repo = FakeRepository(valid_payload())
    client = FakeClient(
        [CapashinoTransientError("temporary") for _ in range(MAX_ATTEMPTS)]
    )

    await OutBoxService(repo, client).worker()

    assert repo.entry.attempt_count == MAX_ATTEMPTS
    assert repo.entry.status is False
    assert len(client.keys) == MAX_ATTEMPTS
    assert set(client.keys) == {str(OUTBOX_ID)}


@pytest.mark.asyncio
async def test_worker_completes_existing_idempotent_notification():
    repo = FakeRepository(valid_payload())

    await OutBoxService(repo, FakeClient([NotificationAlreadyExists()])).worker()

    assert repo.entry.status is True
    assert repo.entry.payload == valid_payload()


@pytest.mark.asyncio
async def test_worker_stops_retrying_permanent_error():
    repo = FakeRepository(valid_payload())
    client = FakeClient([CapashinoPermanentError("bad request")])

    await OutBoxService(repo, client).worker()

    assert repo.entry.attempt_count == MAX_ATTEMPTS
    assert repo.entry.status is False
    assert len(client.keys) == 1


@pytest.mark.asyncio
async def test_worker_completes_created_notification():
    repo = FakeRepository(valid_payload())

    await OutBoxService(repo, FakeClient([created_result()])).worker()

    assert repo.entry.status is True
    assert repo.entry.payload["id"] == "notification-1"
