from types import SimpleNamespace

import pytest

from eventsaggregator.client.paginator import EventsPaginator
from eventsaggregator.core.exceptions import ProviderError


class FakeClient:
    def __init__(self, first_page, next_pages=None):
        self.first_page = first_page
        self.next_pages = dict(next_pages or {})
        self.fetch_events_calls = []
        self.fetch_next_events_calls = []

    async def fetch_events(self, changed_at):
        self.fetch_events_calls.append(changed_at)
        return self.first_page

    async def fetch_next_events(self, next_url):
        self.fetch_next_events_calls.append(next_url)
        return self.next_pages[next_url]


def make_page(results, next_url=None):
    return SimpleNamespace(results=results, next=next_url)


@pytest.mark.asyncio
async def test_single_page_is_yielded_once():
    page = make_page(["a"])
    client = FakeClient(page)

    pages = [p async for p in EventsPaginator(client, "2026-10-12")]

    assert pages == [page]
    assert client.fetch_events_calls == ["2026-10-12"]
    assert client.fetch_next_events_calls == []


@pytest.mark.asyncio
async def test_follows_next_links_in_order():
    page1 = make_page(["a"], "url-2")
    page2 = make_page(["b"], "url-3")
    page3 = make_page(["c"])
    client = FakeClient(page1, {"url-2": page2, "url-3": page3})

    pages = [p async for p in EventsPaginator(client, "2000-01-01")]

    assert pages == [page1, page2, page3]
    assert client.fetch_events_calls == ["2000-01-01"]
    assert client.fetch_next_events_calls == ["url-2", "url-3"]


@pytest.mark.asyncio
async def test_empty_first_page_is_still_yielded():
    page = make_page([])
    client = FakeClient(page)

    pages = [p async for p in EventsPaginator(client, "2026-10-12")]

    assert pages == [page]


@pytest.mark.asyncio
async def test_stays_exhausted_after_last_page():
    client = FakeClient(make_page(["a"]))
    paginator = EventsPaginator(client, "2026-10-12")

    await paginator.__anext__()
    with pytest.raises(StopAsyncIteration):
        await paginator.__anext__()
    with pytest.raises(StopAsyncIteration):
        await paginator.__anext__()

    assert client.fetch_events_calls == ["2026-10-12"]
    assert client.fetch_next_events_calls == []


def test_no_requests_before_iteration_starts():
    client = FakeClient(make_page([]))

    EventsPaginator(client, "2026-10-12")

    assert client.fetch_events_calls == []
    assert client.fetch_next_events_calls == []


@pytest.mark.asyncio
async def test_client_error_propagates():
    class FailingClient(FakeClient):
        async def fetch_next_events(self, next_url):
            raise ProviderError("provider unavailable")

    client = FailingClient(make_page(["a"], "url-2"))
    paginator = EventsPaginator(client, "2026-10-12")

    await paginator.__anext__()
    with pytest.raises(ProviderError, match="provider unavailable"):
        await paginator.__anext__()
