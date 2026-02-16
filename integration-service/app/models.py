from __future__ import annotations

from pydantic import BaseModel, Field


class IntakeRequest(BaseModel):
    customer_name: str = Field(min_length=1, max_length=120)
    phone: str = Field(min_length=1, max_length=40)
    device: str = Field(min_length=1, max_length=200)
    device_type: str | None = Field(default=None, max_length=40)
    model: str | None = Field(default=None, max_length=120)
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


class CloseSyncRequest(BaseModel):
    zammad_ticket_number: str = Field(min_length=1, max_length=64)
    erp_issue_ref: str | None = Field(default=None, max_length=140)
    status: str = Field(min_length=1, max_length=80)
    owner: str | None = Field(default=None, max_length=140)
    approved_price: float | None = None
    repair_cost: float | None = None
    warranty_days: int | None = None
    net_profit: float | None = None
    note: str | None = Field(default=None, max_length=4000)


class CloseSyncResponse(BaseModel):
    success: bool
    zammad_ticket_number: str
    erpnext_issue: str | None = None
    updated: bool = False


class CreateSyncRequest(BaseModel):
    zammad_ticket_id: int
    zammad_ticket_number: str = Field(min_length=1, max_length=64)
    customer_name: str = Field(min_length=1, max_length=120)
    phone: str | None = Field(default=None, max_length=40)
    device: str | None = Field(default=None, max_length=200)
    problem: str | None = Field(default=None, max_length=3000)
    service_point: str | None = Field(default=None, max_length=255)
    tg_user_id: int | None = None
    tg_username: str | None = Field(default=None, max_length=64)
    erp_issue_ref: str | None = Field(default=None, max_length=140)


class CreateSyncResponse(BaseModel):
    success: bool
    zammad_ticket_id: int
    zammad_ticket_number: str
    erpnext_issue: str | None = None
    created: bool = False
