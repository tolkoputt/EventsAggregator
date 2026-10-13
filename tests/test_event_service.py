import datetime
from uuid import UUID

import pytest

from eventsaggregator.core.exceptions import EventNotFound
from eventsaggregator.schemas.events import PageParams
from eventsaggregator.services.events import EventsService


class FakeRepo:
    def __init__(self, event):
        self.event = event
        self.list_events_args = None

    async def one_event(self, event_id):
        return self.event

    async def list_events(self, date_from, page_size, offset):
        self.list_events_args = (date_from, page_size, offset)
        return self.event


@pytest.mark.asyncio
async def test_get_event_raise_not_found():
    repo = FakeRepo(event=None)
    service = EventsService(events=repo)
    event_id = UUID("d4f53b3c-1f70-4b5c-a63d-c25e1b488e76")

    with pytest.raises(EventNotFound):
        await service.get_event(event_id)


@pytest.mark.asyncio
async def test_get_event_success():
    fake_event = {
        "id": UUID("d4f53b3c-1f70-4b5c-a63d-c25e1b488e76"),
    }
    repo = FakeRepo(event=fake_event)
    service = EventsService(events=repo)
    event_id = UUID("d4f53b3c-1f70-4b5c-a63d-c25e1b488e76")

    event = await service.get_event(event_id)
    assert event == fake_event


@pytest.mark.asyncio
async def test_list_events():
    date_from = datetime.datetime(2025, 1, 1, tzinfo=datetime.UTC)
    expected_result = ([], 25)
    repo = FakeRepo(event=expected_result)
    service = EventsService(events=repo)

    result = await service.list_events(
        PageParams(page=3, page_size=10, date_from=date_from)
    )

    assert repo.list_events_args == (date_from, 10, 20)
    assert result == expected_result
