from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, Uuid
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Sync(Base):
    __tablename__ = "syncs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    last_sync_time: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    last_changed_at: Mapped[str] = mapped_column(String(), index=True)
    sync_status: Mapped[bool] = mapped_column(Boolean())


class Place(Base):
    __tablename__ = "places"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    name: Mapped[str] = mapped_column(String())
    city: Mapped[str] = mapped_column(String())
    address: Mapped[str] = mapped_column(String())
    seats_pattern: Mapped[str] = mapped_column(Text)
    changed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    events: Mapped[list[Event]] = relationship(back_populates="place")


class Event(Base):
    __tablename__ = "events"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    name: Mapped[str] = mapped_column(String())
    event_time: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    registration_deadline: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String())
    number_of_visitors: Mapped[int] = mapped_column(Integer)
    changed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    status_changed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    place_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("places.id"),
        index=True,
    )

    place: Mapped[Place] = relationship(back_populates="events")
