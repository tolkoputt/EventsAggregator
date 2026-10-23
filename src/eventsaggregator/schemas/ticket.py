from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, field_validator


class TicketRequest(BaseModel):
    idempotency_key: str | None = Field(default=None, min_length=1, max_length=100)
    event_id: UUID
    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = Field(min_length=1, max_length=100)
    email: EmailStr
    seat: str = Field(pattern=r"^[A-Z]\d+$")

    @field_validator("first_name", "last_name")
    @classmethod
    def strip_name(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("must not be blank")
        return v


class TicketResponse(BaseModel):
    ticket_id: UUID


class DeleteTicketResponse(BaseModel):
    success: bool
