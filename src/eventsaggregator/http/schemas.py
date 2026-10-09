from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class SyncTriggerResponse(BaseModel):
    next: str | None
    previous: str | None
    results: list["EventResponse"]


class PlaceResponse(BaseModel):
    id: UUID
    name: str
    city: str
    address: str
    seats_pattern: str
    changed_at: datetime
    created_at: datetime


class EventResponse(BaseModel):
    id: UUID
    name: str
    place: PlaceResponse
    event_time: datetime
    registration_deadline: datetime
    status: str
    number_of_visitors: int
    changed_at: datetime
    created_at: datetime
    status_changed_at: datetime
