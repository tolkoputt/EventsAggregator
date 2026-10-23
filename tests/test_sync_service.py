from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import UUID

import pytest

from eventsaggregator.services import sync as sync_module
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


class FakePaginator:
    def __init__(self, registry, client, changed_at):
        self.client = client
        self.changed_at = changed_at
        self._pages = iter(registry.pages)
        registry.instances.append(self)

    def __aiter__(self):
        return self

    async def __anext__(self):
        try:
            return next(self._pages)
        except StopIteration:
            raise StopAsyncIteration from None


class PaginatorRegistry:
    def __init__(self):
        self.pages = []
        self.instances = []

    def __call__(self, client, changed_at):
        return FakePaginator(self, client, changed_at)


@pytest.fixture
def paginator(monkeypatch):
    registry = PaginatorRegistry()
    monkeypatch.setattr(sync_module, "EventsPaginator", registry)
    return registry


def make_event(event_id, place):
    return SimpleNamespace(
        id=UUID(event_id),
        place=place,
    )


@pytest.mark.asyncio
async def test_sync_events_skips_sync_when_another_sync_holds_lock(paginator):
    repo = FakeRepo(last_changed_at=False)
    service = SyncService(events=repo, client=object())  # type: ignore

    result = await service.sync_events()

    assert result is False
    assert repo.calls == [("get_last_changed_at",)]
    assert paginator.instances == []


@pytest.mark.asyncio
async def test_sync_events_collects_all_pages_and_persists_events_and_places(paginator):
    place_a = SimpleNamespace(id=UUID("1045417a-8597-4d37-9e7d-57c44576b871"))
    place_b = SimpleNamespace(id=UUID("2045417a-8597-4d37-9e7d-57c44576b872"))
    event_a = make_event("3045417a-8597-4d37-9e7d-57c44576b873", place_a)
    event_b = make_event("4045417a-8597-4d37-9e7d-57c44576b874", place_a)
    event_c = make_event("5045417a-8597-4d37-9e7d-57c44576b875", place_b)
    repo = FakeRepo(last_changed_at="2026-10-12")
    client = object()
    paginator.pages = [
        SimpleNamespace(results=[event_a, event_b]),
        SimpleNamespace(results=[event_c]),
    ]
    service = SyncService(events=repo, client=client)  # type: ignore

    result = await service.sync_events()

    assert result is True
    assert len(paginator.instances) == 1
    assert paginator.instances[0].client is client
    assert paginator.instances[0].changed_at == "2026-10-12"
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
async def test_sync_events_uses_initial_date_when_no_previous_sync_exists(paginator):
    repo = FakeRepo(last_changed_at=None)
    paginator.pages = [SimpleNamespace(results=[])]
    service = SyncService(events=repo, client=object())  # type: ignore

    result = await service.sync_events()

    assert result is True
    assert paginator.instances[0].changed_at == "2000-01-01"
    assert repo.calls[1][0] == "flush"
    assert repo.calls[2][0] == "merge_sync"
    assert repo.calls[3] == ("commit",)
