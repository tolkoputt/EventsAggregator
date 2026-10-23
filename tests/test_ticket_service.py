from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from typing import Any
from uuid import UUID

import pytest

from eventsaggregator.client.schemas import DeleteTicket, RegisterTicket
from eventsaggregator.core.enums import EventStatus
from eventsaggregator.core.exceptions import (
    EventNotFound,
    EventNotPublished,
    InvalidSeat,
    RegistrationDeadlinePassed,
    TicketNotFound,
    TicketRegisterError,
    TicketUnequalPayload,
)
from eventsaggregator.schemas.ticket import TicketRequest
from eventsaggregator.services.ticket import TicketService


@pytest.fixture
def event_id():
    return UUID("1045417a-8597-4d37-9e7d-57c44576b871")


@pytest.fixture
def idempotency_key():
    return "client-request-123"


@pytest.fixture
def ticket_id():
    return UUID("d4f53b3c-1f70-4b5c-a63d-c25e1b488e76")


@pytest.fixture
def valid_event():
    return SimpleNamespace(
        status=EventStatus.PUBLISHED,
        registration_deadline=datetime.now(UTC) + timedelta(hours=1),
        place=SimpleNamespace(seats_pattern="A1-10,B1-5"),
    )


@pytest.fixture
def ticket_request(event_id, idempotency_key):
    return TicketRequest(
        idempotency_key=idempotency_key,
        event_id=event_id,
        first_name="Ada",
        last_name="Lovelace",
        email="ada@example.com",
        seat="B1",
    )


class FakeSession:
    def __init__(self):
        self.committed = False
        self.rolled_back = False

    async def commit(self):
        self.committed = True

    async def rollback(self):
        self.rolled_back = True


class FakeRepo:
    def __init__(self, event=None, fail_on=None):
        self.event = event
        self.fail_on = fail_on
        self.session = FakeSession()
        self.event_id = None
        self.existing_idempotency_key = False
        self.existing_payload: dict[str, Any] | None = None
        self.existing_ticket_id = None
        self.last_idempotency_key = None
        self.requested_event_id = None
        self.requested_ticket_id = None
        self.merged_ticket: dict[str, Any] | None = None
        self.outbox_entry: tuple[UUID, str, dict[str, Any], bool, datetime] | None = (
            None
        )
        self.deleted_ticket = None

    async def one_event(self, event_id):
        self.requested_event_id = event_id
        return self.event

    async def merge_ticket(self, **ticket_data):
        self.merged_ticket = ticket_data
        if self.fail_on == "merge_ticket":
            raise RuntimeError("ticket persistence failed")

    async def update_outbox(self, id, operation_type, payload, status, last_sync_time):
        self.outbox_entry = (
            id,
            operation_type,
            payload,
            status,
            last_sync_time,
        )
        if self.fail_on == "update_outbox":
            raise RuntimeError("outbox persistence failed")

    async def get_event_id_by_ticket(self, ticket_id):
        self.requested_ticket_id = ticket_id
        return self.event_id

    async def delete_ticket(self, ticket_id):
        self.deleted_ticket = ticket_id

    async def commit(self):
        await self.session.commit()

    async def check_idempotency_ticket(self, idempotency_key):
        self.last_idempotency_key = idempotency_key
        return self.existing_idempotency_key

    async def check_ticket_payload(self, idempotency_key):
        self.last_idempotency_key = idempotency_key
        return self.existing_payload

    async def get_ticket_id(self, idempotency_key):
        self.last_idempotency_key = idempotency_key
        return self.existing_ticket_id


class FakeProvider:
    def __init__(
        self,
        ticket_id: UUID | None = None,
        delete_success: bool = True,
    ):
        self.ticket_id = ticket_id or UUID("d4f53b3c-1f70-4b5c-a63d-c25e1b488e76")
        self.delete_success = delete_success
        self.register_called = False
        self.delete_called = False
        self.register_args = None
        self.delete_args = None

    async def register_ticket(self, event_id, seat, first_name, last_name, email):
        self.register_called = True
        self.register_args = (event_id, seat, first_name, last_name, email)
        return RegisterTicket(ticket_id=self.ticket_id)

    async def delete_ticket(self, event_id, ticket_id):
        self.delete_called = True
        self.delete_args = (event_id, ticket_id)
        return DeleteTicket(success=self.delete_success)


def make_service(repo, provider):
    return TicketService(events=repo, provider=provider)  # type: ignore[arg-type]


@pytest.mark.asyncio
async def test_get_ticket_raises_when_event_is_missing(ticket_request):
    service = make_service(FakeRepo(), FakeProvider())

    with pytest.raises(EventNotFound):
        await service.get_ticket(ticket_request)


@pytest.mark.asyncio
async def test_get_ticket_raises_when_event_is_not_published(ticket_request):
    event = SimpleNamespace(
        status="finished",
        registration_deadline=datetime.now(UTC) + timedelta(hours=1),
        place=SimpleNamespace(seats_pattern="A1-10"),
    )
    provider = FakeProvider()

    with pytest.raises(EventNotPublished):
        await make_service(FakeRepo(event), provider).get_ticket(ticket_request)

    assert not provider.register_called


@pytest.mark.asyncio
async def test_get_ticket_raises_when_registration_deadline_passed(ticket_request):
    event = SimpleNamespace(
        status=EventStatus.PUBLISHED,
        registration_deadline=datetime.now(UTC) - timedelta(seconds=1),
        place=SimpleNamespace(seats_pattern="A1-10"),
    )
    provider = FakeProvider()

    with pytest.raises(RegistrationDeadlinePassed):
        await make_service(FakeRepo(event), provider).get_ticket(ticket_request)

    assert not provider.register_called


@pytest.mark.asyncio
async def test_get_ticket_raises_when_seat_is_invalid(ticket_request):
    event = SimpleNamespace(
        status=EventStatus.PUBLISHED,
        registration_deadline=datetime.now(UTC) + timedelta(hours=1),
        place=SimpleNamespace(seats_pattern="A1-10"),
    )
    provider = FakeProvider()

    with pytest.raises(InvalidSeat):
        await make_service(FakeRepo(event), provider).get_ticket(ticket_request)

    assert not provider.register_called


@pytest.mark.asyncio
async def test_get_ticket_persists_ticket_and_outbox_and_commits(
    event_id, idempotency_key, ticket_id, ticket_request, valid_event
):
    repo = FakeRepo(valid_event)
    provider = FakeProvider(ticket_id)

    result = await make_service(repo, provider).get_ticket(ticket_request)

    assert result.ticket_id == ticket_id
    assert provider.register_args == (
        event_id,
        "B1",
        "Ada",
        "Lovelace",
        "ada@example.com",
    )
    assert repo.merged_ticket is not None
    assert repo.merged_ticket["ticket_id"] == ticket_id
    assert repo.merged_ticket["event_id"] == event_id
    assert repo.merged_ticket["payload"] == ticket_request.model_dump()
    assert repo.merged_ticket["idempotency_key"] == idempotency_key
    assert repo.merged_ticket["date"].tzinfo is UTC
    assert repo.outbox_entry is not None
    assert repo.outbox_entry[0] != idempotency_key
    assert repo.outbox_entry[:4] == (
        repo.outbox_entry[0],
        "get",
        {"ticket_id": ticket_id},
        False,
    )
    assert repo.outbox_entry[4].tzinfo is UTC
    assert repo.session.committed
    assert not repo.session.rolled_back


@pytest.mark.parametrize("fail_on", ["merge_ticket", "update_outbox"])
@pytest.mark.asyncio
async def test_get_ticket_rolls_back_and_raises_when_persistence_fails(
    fail_on, ticket_id, ticket_request, valid_event
):
    repo = FakeRepo(valid_event, fail_on=fail_on)
    provider = FakeProvider(ticket_id)

    with pytest.raises(TicketRegisterError):
        await make_service(repo, provider).get_ticket(ticket_request)

    assert provider.register_called
    assert repo.session.rolled_back
    assert not repo.session.committed


@pytest.mark.asyncio
async def test_delete_ticket_raises_when_ticket_is_missing(ticket_id):
    repo = FakeRepo()
    provider = FakeProvider()

    with pytest.raises(TicketNotFound):
        await make_service(repo, provider).delete_ticket(ticket_id)

    assert repo.requested_ticket_id == ticket_id
    assert not provider.delete_called
    assert not repo.session.committed


@pytest.mark.asyncio
async def test_delete_ticket_deletes_and_commits(event_id, ticket_id):
    repo = FakeRepo()
    repo.event_id = event_id
    provider = FakeProvider(delete_success=True)

    result = await make_service(repo, provider).delete_ticket(ticket_id)

    assert result.success
    assert repo.requested_ticket_id == ticket_id
    assert provider.delete_args == (event_id, ticket_id)
    assert repo.deleted_ticket == ticket_id
    assert repo.session.committed


@pytest.mark.asyncio
async def test_delete_ticket_does_not_delete_or_commit_when_provider_declines(
    event_id, ticket_id
):
    repo = FakeRepo()
    repo.event_id = event_id
    provider = FakeProvider(delete_success=False)

    result = await make_service(repo, provider).delete_ticket(ticket_id)

    assert not result.success
    assert provider.delete_called
    assert repo.deleted_ticket is None
    assert not repo.session.committed


@pytest.mark.asyncio
async def test_get_ticket_logic_returns_existing_ticket_for_same_payload(
    ticket_id, ticket_request
):
    repo = FakeRepo()
    repo.existing_idempotency_key = True
    repo.existing_payload = ticket_request.model_dump()
    repo.existing_ticket_id = ticket_id
    provider = FakeProvider()

    result = await make_service(repo, provider).get_ticket_logic(ticket_request)

    assert result.ticket_id == ticket_id
    assert not provider.register_called


@pytest.mark.asyncio
async def test_get_ticket_logic_raises_when_idempotency_payload_differs(
    ticket_request,
):
    repo = FakeRepo()
    repo.existing_idempotency_key = True
    repo.existing_payload = {**ticket_request.model_dump(), "seat": "B2"}

    with pytest.raises(TicketUnequalPayload):
        await make_service(repo, FakeProvider()).get_ticket_logic(ticket_request)


@pytest.mark.asyncio
async def test_get_ticket_logic_raises_when_existing_key_has_no_ticket(
    ticket_request,
):
    repo = FakeRepo()
    repo.existing_idempotency_key = True
    repo.existing_payload = ticket_request.model_dump()

    with pytest.raises(TicketNotFound):
        await make_service(repo, FakeProvider()).get_ticket_logic(ticket_request)


@pytest.mark.asyncio
async def test_get_ticket_logic_registers_ticket_for_new_key(
    ticket_id, ticket_request, valid_event
):
    repo = FakeRepo(valid_event)
    provider = FakeProvider(ticket_id)

    result = await make_service(repo, provider).get_ticket_logic(ticket_request)

    assert result.ticket_id == ticket_id
    assert provider.register_called
    assert repo.merged_ticket is not None


@pytest.mark.asyncio
async def test_get_ticket_without_idempotency_key_registers_and_persists_empty_key(
    ticket_id, event_id, valid_event
):
    request = TicketRequest(
        event_id=event_id,
        first_name="Ada",
        last_name="Lovelace",
        email="ada@example.com",
        seat="B1",
    )
    repo = FakeRepo(valid_event)
    provider = FakeProvider(ticket_id)

    result = await make_service(repo, provider).get_ticket_logic(request)

    assert result.ticket_id == ticket_id
    assert provider.register_called
    assert repo.merged_ticket is not None
    assert repo.merged_ticket["idempotency_key"] == ""
    assert repo.last_idempotency_key is None
