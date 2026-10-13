from types import SimpleNamespace
from uuid import UUID

import pytest

from eventsaggregator.core.exceptions import (
    EventNotPublished,
)
from eventsaggregator.services.seats import SeatsService


class FakeRepo:
    def __init__(self, event):
        self.event = event
        self.requested_event_id = None

    async def event_status(self, event_id):
        self.requested_event_id = event_id
        return self.event


class FakeProvider:
    def __init__(self, seats):
        self.seats = seats
        self.requested_event_id = None

    async def fetch_seats(self, event_id):
        self.requested_event_id = event_id
        return SimpleNamespace(seats=self.seats)


class FakeCache:
    def __init__(self, cache=None):
        self.cache = cache or {}
        self.set_calls = []

    def get(self, key):
        return self.cache.get(key)

    def set(self, key, value):
        self.set_calls.append((key, value))
        self.cache[key] = value


@pytest.mark.asyncio
async def test_get_seats_raises_when_event_is_not_published():
    repo = FakeRepo("finished")

    event_id = UUID("1045417a-8597-4d37-9e7d-57c44576b871")

    service = SeatsService(
        events=repo,
        provider=FakeProvider(seats=[]),
        cache=FakeCache(),
    )

    with pytest.raises(EventNotPublished):
        await service.get_seats(event_id=event_id)

    assert repo.requested_event_id == event_id


@pytest.mark.asyncio
async def test_get_seats_fetches_and_caches_seats_when_cache_is_empty():
    event_id = UUID("1045417a-8597-4d37-9e7d-57c44576b871")
    available_seats = ["A1", "A2"]
    repo = FakeRepo("published")
    provider = FakeProvider(seats=available_seats)
    cache = FakeCache()
    service = SeatsService(events=repo, provider=provider, cache=cache)

    result = await service.get_seats(event_id=event_id)

    assert result.event_id == event_id
    assert result.available_seats == available_seats
    assert repo.requested_event_id == event_id
    assert provider.requested_event_id == event_id
    assert cache.set_calls == [(str(event_id), available_seats)]


@pytest.mark.asyncio
async def test_get_seats_returns_cached_seats_without_calling_provider():
    event_id = UUID("1045417a-8597-4d37-9e7d-57c44576b871")
    available_seats = ["B1", "B2"]
    repo = FakeRepo("published")
    provider = FakeProvider(seats=["C1"])
    cache = FakeCache({str(event_id): available_seats})
    service = SeatsService(events=repo, provider=provider, cache=cache)

    result = await service.get_seats(event_id=event_id)

    assert result.event_id == event_id
    assert result.available_seats == available_seats
    assert repo.requested_event_id == event_id
    assert provider.requested_event_id is None
    assert cache.set_calls == []
