from __future__ import annotations

from pydantic import BaseModel, Field


class IntakeRequest(BaseModel):
    customer_name: str = Field(min_length=1, max_length=120)
    phone: str = Field(min_length=1, max_length=40)
    device: str = Field(min_length=1, max_length=200)
    problem: str = Field(min_length=1, max_length=3000)
    service_point: str = Field(min_length=1, max_length=255)
    tg_user_id: int
    tg_username: str | None = Field(default=None, max_length=64)


class IntakeResponse(BaseModel):
    success: bool
    idempotency_key: str | None
    zammad_ticket_id: int | None = None
    zammad_ticket_number: str | None = None
    erpnext_issue: str | None = None
    replayed: bool = False

