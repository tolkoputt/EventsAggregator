from typing import Annotated

import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from eventsaggregator.db.db import get_async_session
from eventsaggregator.http.request import get_http
from eventsaggregator.services.sync import sync_events

router = APIRouter(prefix="/sync/trigger", tags=["sync"])


@router.post("")
async def sync_trigger_req(
    client: Annotated[httpx.AsyncClient, Depends(get_http)],
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> dict[str, str]:
    if not await sync_events(client, session):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Sync is already running",
        )
    return {"status": "success"}
