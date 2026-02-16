from __future__ import annotations

from typing import Any

import httpx

from app.config import Settings
from app.models import IntakeRequest


class ERPNextClient:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def is_enabled(self) -> bool:
        return (
            self.settings.enable_erp_issue
            and bool(self.settings.erpnext_api_key)
            and bool(self.settings.erpnext_api_secret)
        )

    async def create_issue(self, payload: IntakeRequest, zammad_ticket_number: str | None) -> dict[str, Any]:
        if not self.is_enabled():
            return {"issue": None, "skipped": True}

        headers = {
            "Authorization": f"token {self.settings.erpnext_api_key}:{self.settings.erpnext_api_secret}",
            "Content-Type": "application/json",
        }
        issue_payload = {
            "subject": f"Pixel SC / {payload.device} / {payload.customer_name}",
            "description": (
                f"Телефон: {payload.phone}\n"
                f"Устройство: {payload.device}\n"
                f"Проблема: {payload.problem}\n"
                f"Сервис-поинт: {payload.service_point}\n"
                f"Telegram: {payload.tg_user_id} (@{payload.tg_username or ''})\n"
                f"Zammad ticket: {zammad_ticket_number or '-'}"
            ),
        }

        url = f"{self.settings.erpnext_base_url.rstrip('/')}/api/resource/{self.settings.erpnext_issue_doctype}"
        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.post(url, headers=headers, json=issue_payload)
            resp.raise_for_status()
            data = resp.json()

        issue_name = ((data or {}).get("data") or {}).get("name")
        return {"issue": issue_name, "raw": data}

