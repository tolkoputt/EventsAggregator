from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


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


class PlaceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    name: str
    city: str
    address: str


class PlaceOutSeatsPattern(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    name: str
    city: str
    address: str
    seats_pattern: str


class EventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    name: str
    place: PlaceOut
    event_time: datetime
    registration_deadline: datetime
    status: str
    number_of_visitors: int


class EventOutSeatsPattern(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    name: str
    place: PlaceOutSeatsPattern
    event_time: datetime
    registration_deadline: datetime
    status: str
    number_of_visitors: int


class SeatsFromExtAPI(BaseModel):
    seats: list[str]


class Seats(BaseModel):
    event_id: UUID
    available_seats: list[str]


class PageParams(BaseModel):
    page: int = Field(1, ge=1)
    page_size: int = Field(10, ge=1, le=100)
    date_from: datetime | None = None

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size


class Page(BaseModel):
    count: int
    next: str | None
    previous: str | None
    results: list[EventOut]
