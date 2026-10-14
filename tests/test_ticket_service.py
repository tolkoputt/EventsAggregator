from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from uuid import UUID

import pytest

from eventsaggregator.core.enums import EventStatus
from eventsaggregator.core.exceptions import (
    EventNotFound,
    EventNotPublished,
    InvalidSeat,
    RegistrationDeadlinePassed,
    TicketNotFound,
)
from eventsaggregator.schemas.ticket import TicketRequest
from eventsaggregator.services.ticket import TicketService


@pytest.fixture
def event_id():
    return UUID("1045417a-8597-4d37-9e7d-57c44576b871")


@pytest.fixture
def valid_event():
    return SimpleNamespace(
        status=EventStatus.PUBLISHED,
        registration_deadline=datetime.now(UTC) + timedelta(hours=1),
        place=SimpleNamespace(seats_pattern="A1-10,B1-5"),
    )


@pytest.fixture
def invalid_event():
    return SimpleNamespace(
        status="finished",
        registration_deadline=datetime.now(UTC) - timedelta(seconds=1),
        place=SimpleNamespace(seats_pattern="A1-10"),
    )


@pytest.fixture
def expired_event():
    return SimpleNamespace(
        status=EventStatus.PUBLISHED,
        registration_deadline=datetime.now(UTC) - timedelta(seconds=1),
        place=SimpleNamespace(seats_pattern="A1-10"),
    )


@pytest.fixture
def ticket_request(event_id):
    return TicketRequest(
        event_id=event_id,
        first_name="Ada",
        last_name="Lovelace",
        email="ada@example.com",
        seat="B1",
    )


class FakeRepo:
    def __init__(self, event):
        self.event = event
        self.merged_ticket = None
        self.committed = False
        self.event_id = None
        self.deleted_ticket = None

    async def one_event(self, event_id):
        return self.event

    async def merge_ticket(self, event_id, ticket_id, created_at):
        self.merged_ticket = (event_id, ticket_id, created_at)

    async def commit(self):
        self.committed = True

    async def get_event_id_by_ticket(self, ticket_id):
        return self.event_id

    async def delete_ticket(self, ticket_id):
        self.deleted_ticket = ticket_id


class FakeProvider:
    def __init__(self, ticket_id):
        self.ticket_id = ticket_id
        self.called = False
        self.delete_called = False

    async def register_ticket(self, event_id, seat, first_name, last_name, email):
        self.called = True
        return SimpleNamespace(ticket_id=self.ticket_id)

    async def delete_ticket(self, event_id, ticket_id):
        self.delete_called = True
        return SimpleNamespace(success=True)


@pytest.mark.asyncio
async def test_get_ticket_raises_when_event_is_missing(ticket_request):
    service = TicketService(events=FakeRepo(None), provider=None)

    with pytest.raises(EventNotFound):
        await service.get_ticket(data=ticket_request)


@pytest.mark.asyncio
async def test_get_ticket_raises_when_event_is_not_published(
    invalid_event, ticket_request
):
    repo = FakeRepo(invalid_event)

    service = TicketService(events=repo, provider=None)

    with pytest.raises(EventNotPublished):
        await service.get_ticket(data=ticket_request)


@pytest.mark.asyncio
async def test_get_ticket_raises_when_registration_deadline_passed(
    expired_event, ticket_request
):
    repo = FakeRepo(expired_event)
    service = TicketService(events=repo, provider=None)

    with pytest.raises(RegistrationDeadlinePassed):
        await service.get_ticket(data=ticket_request)


@pytest.mark.asyncio
async def test_get_ticket_raises_when_seat_is_invalid(ticket_request):
    event = SimpleNamespace(
        status=EventStatus.PUBLISHED,
        registration_deadline=datetime.now(UTC) + timedelta(hours=1),
        place=SimpleNamespace(seats_pattern="A1-10"),
    )
    repo = FakeRepo(event)
    service = TicketService(events=repo, provider=None)

    with pytest.raises(InvalidSeat):
        await service.get_ticket(data=ticket_request)


@pytest.mark.asyncio
async def test_get_ticket_registers_ticket_and_commits(
    event_id, ticket_request, valid_event
):
    ticket_id = UUID("d4f53b3c-1f70-4b5c-a63d-c25e1b488e76")

    repo = FakeRepo(valid_event)
    provider = FakeProvider(ticket_id)
    service = TicketService(events=repo, provider=provider)

    result = await service.get_ticket(data=ticket_request)

    assert result.ticket_id == ticket_id
    assert provider.called is True
    assert repo.merged_ticket[0] == event_id
    assert repo.merged_ticket[1] == ticket_id
    assert repo.committed is True


@pytest.mark.asyncio
async def test_delete_ticket_raises_when_ticket_is_missing():
    repo = FakeRepo(event=None)
    provider = FakeProvider(ticket_id=None)
    service = TicketService(events=repo, provider=provider)
    ticket_id = UUID("d4f53b3c-1f70-4b5c-a63d-c25e1b488e76")

    with pytest.raises(TicketNotFound):
        await service.delete_ticket(ticket_id)

    assert provider.delete_called is False
    assert repo.committed is False


@pytest.mark.asyncio
async def test_delete_ticket_deletes_and_commits(event_id):
    ticket_id = UUID("d4f53b3c-1f70-4b5c-a63d-c25e1b488e76")
    repo = FakeRepo(event=None)
    repo.event_id = event_id
    provider = FakeProvider(ticket_id=None)
    service = TicketService(events=repo, provider=provider)

    result = await service.delete_ticket(ticket_id)

    assert result.success is True
    assert provider.delete_called is True
    assert repo.deleted_ticket == ticket_id
    assert repo.committed is True
