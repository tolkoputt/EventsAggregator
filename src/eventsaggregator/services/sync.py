from datetime import UTC, datetime

from httpx import AsyncClient
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from eventsaggregator.db.models import Event, Place, Sync
from eventsaggregator.http.request import fetch_events, fetch_next_events

SYNC_ROW_ID = 1
DEFAULT_CHANGED_AT = "2000-01-01"
SYNC_LOCK_ID = 7_351_001


async def sync_events(http: AsyncClient, session: AsyncSession) -> bool:
    locked = await session.scalar(
        text("SELECT pg_try_advisory_xact_lock(:id)"), {"id": SYNC_LOCK_ID}
    )
    if not locked:
        return False

    last_changed_at = await session.scalar(
        select(Sync.last_changed_at).where(Sync.id == SYNC_ROW_ID)
    )

    data = await fetch_events(http, last_changed_at or DEFAULT_CHANGED_AT)
    results = data.results
    next_url = data.next
    while next_url:
        page = await fetch_next_events(http, next_url)
        results.extend(page.results)
        next_url = page.next

    places = {item.place.id: item.place for item in results}
    for place in places.values():
        await session.merge(Place(**place.model_dump()))
    await session.flush()

    for item in results:
        await session.merge(
            Event(**item.model_dump(exclude={"place"}), place_id=item.place.id)
        )

    now = datetime.now(UTC)
    await session.merge(
        Sync(
            id=SYNC_ROW_ID,
            last_sync_time=now,
            last_changed_at=now.strftime("%Y-%m-%d"),
            sync_status=True,
        )
    )
    await session.commit()
    return True
