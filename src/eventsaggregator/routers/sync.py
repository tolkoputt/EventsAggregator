from typing import Annotated

import httpx
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from eventsaggregator.db.db import get_async_session
from eventsaggregator.http.request import fetch_events, get_http
from eventsaggregator.http.schemas import SyncTriggerResponse
from eventsaggregator.services.sync import save_events

router = APIRouter(prefix="/sync/trigger", tags=["sync"])


@router.get("", response_model=SyncTriggerResponse)
async def sync_trigger_req(
    client: Annotated[httpx.AsyncClient, Depends(get_http)],
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> SyncTriggerResponse:
    data = await fetch_events(client)
    await save_events(session, data)
    return data
