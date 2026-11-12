from typing import Annotated

from fastapi import APIRouter, Depends, Response
from prometheus_client import REGISTRY, generate_latest

from eventsaggregator.db.repositories import EventRepository
from eventsaggregator.deps import get_event_repo
from eventsaggregator.services.metrics import (
    events_total,
    tickets_cancelled_total,
    tickets_created_total,
)

router = APIRouter(prefix="/metrics", tags=["metrics"])


@router.get("")
async def metrics(repository: Annotated[EventRepository, Depends(get_event_repo)]):

    db_metrics = await repository.metrics()
    tickets_created_total.set(db_metrics["tickets_created_total"])
    events_total.set(db_metrics["events_total"])
    tickets_cancelled_total.set(0)

    return Response(
        content=generate_latest(REGISTRY),
        media_type="text/plain",
    )
