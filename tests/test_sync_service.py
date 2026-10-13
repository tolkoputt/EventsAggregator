from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import UUID

import pytest

from eventsaggregator.services.sync import SyncService


class FakeRepo:
    def __init__(self, last_changed_at):
        self.last_changed_at = last_changed_at
        self.calls = []

    async def get_last_changed_at(self):
        self.calls.append(("get_last_changed_at",))
        return self.last_changed_at

    async def merge_place(self, place):
        self.calls.append(("merge_place", place))

    async def flush(self):
        self.calls.append(("flush",))

    async def merge_event(self, event):
        self.calls.append(("merge_event", event))

    async def merge_sync(self, sync_time):
        self.calls.append(("merge_sync", sync_time))

    async def commit(self):
        self.calls.append(("commit",))


class FakeClient:
    def __init__(self, pages):
        self.pages = iter(pages)
        self.fetch_events_calls = []
        self.fetch_next_events_calls = []

    async def fetch_events(self, changed_at):
        self.fetch_events_calls.append(changed_at)
        return next(self.pages)

    async def fetch_next_events(self, next_url):
        self.fetch_next_events_calls.append(next_url)
        return next(self.pages)


def make_event(event_id, place):
    return SimpleNamespace(
        id=UUID(event_id),
        place=place,
    )


@pytest.mark.asyncio
async def test_sync_events_skips_sync_when_another_sync_holds_lock():
    repo = FakeRepo(last_changed_at=False)
    client = FakeClient(pages=[])
    service = SyncService(events=repo, client=client)

    result = await service.sync_events()

    assert result is False
    assert repo.calls == [("get_last_changed_at",)]
    assert client.fetch_events_calls == []
    assert client.fetch_next_events_calls == []


@pytest.mark.asyncio
async def test_sync_events_fetches_all_pages_and_persists_events_and_places():
    place_a = SimpleNamespace(id=UUID("1045417a-8597-4d37-9e7d-57c44576b871"))
    place_b = SimpleNamespace(id=UUID("2045417a-8597-4d37-9e7d-57c44576b872"))
    event_a = make_event("3045417a-8597-4d37-9e7d-57c44576b873", place_a)
    event_b = make_event("4045417a-8597-4d37-9e7d-57c44576b874", place_a)
    event_c = make_event("5045417a-8597-4d37-9e7d-57c44576b875", place_b)
    repo = FakeRepo(last_changed_at="2026-10-12")
    client = FakeClient(
        pages=[
            SimpleNamespace(results=[event_a, event_b], next="next-page"),
            SimpleNamespace(results=[event_c], next=None),
        ]
    )
    service = SyncService(events=repo, client=client)

    result = await service.sync_events()

    assert result is True
    assert client.fetch_events_calls == ["2026-10-12"]
    assert client.fetch_next_events_calls == ["next-page"]
    assert repo.calls[:4] == [
        ("get_last_changed_at",),
        ("merge_place", place_a),
        ("merge_place", place_b),
        ("flush",),
    ]
    assert repo.calls[4:7] == [
        ("merge_event", event_a),
        ("merge_event", event_b),
        ("merge_event", event_c),
    ]
    assert repo.calls[7][0] == "merge_sync"
    assert isinstance(repo.calls[7][1], datetime)
    assert repo.calls[7][1].tzinfo == UTC
    assert repo.calls[8] == ("commit",)


@pytest.mark.asyncio
async def test_sync_events_uses_initial_date_when_no_previous_sync_exists():
    repo = FakeRepo(last_changed_at=None)
    client = FakeClient(pages=[SimpleNamespace(results=[], next=None)])
    service = SyncService(events=repo, client=client)

    result = await service.sync_events()

    assert result is True
    assert client.fetch_events_calls == ["2000-01-01"]
    assert client.fetch_next_events_calls == []
    assert repo.calls[1][0] == "flush"
    assert repo.calls[2][0] == "merge_sync"
    assert repo.calls[3] == ("commit",)
