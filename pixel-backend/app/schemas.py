from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class OrderCreate(BaseModel):
    branch_id: int
    client_name: str = Field(min_length=1, max_length=120)
    client_phone: str = Field(min_length=1, max_length=40)
    client_telegram: str = Field(min_length=1, max_length=64)
    device_type: str = Field(min_length=1, max_length=40)
    model: str | None = Field(default=None, max_length=120)
    problem_description: str = Field(min_length=1, max_length=3000)


class OrderUpdate(BaseModel):
    status: str | None = None
    price: float | None = None
    cost: float | None = None
    zammad_ticket_number: str | None = None
    erpnext_issue: str | None = None


class OrderOut(BaseModel):
    id: int
    number: str
    status: str
    created_at: datetime
    updated_at: datetime
    branch_id: int
    branch_name: str | None
    branch_address: str | None
    client_name: str
    client_phone: str
    client_telegram: str
    device_type: str
    model: str | None
    problem_description: str
    zammad_ticket_number: str | None
    erpnext_issue: str | None
    price: float
    cost: float


class BranchOut(BaseModel):
    id: int
    name: str
    address: str
    schedule: str
    lat: float | None
    lon: float | None


class SupportStaffCreate(BaseModel):
    telegram_id: int
    name: str | None = None


class SupportStaffOut(BaseModel):
    id: int
    telegram_id: int
    name: str | None
    created_at: datetime


class AnalyticsSummary(BaseModel):
    orders: int
    revenue: float
    costs: float
    profit: float

