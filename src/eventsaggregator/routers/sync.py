from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from eventsaggregator.deps import get_sync_service
from eventsaggregator.services.sync import SyncService

router = APIRouter(prefix="/sync/trigger", tags=["sync"])


@router.post("")
async def sync_trigger(sync_service: Annotated[SyncService, Depends(get_sync_service)]):
    if not await sync_service.sync_events():
        raise HTTPException(
            status_code=409,
            detail="Sync is already running",
        )
    return {"status": "success"}
