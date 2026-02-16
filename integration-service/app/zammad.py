from __future__ import annotations

from typing import Any

import httpx

from app.config import Settings
from app.models import IntakeRequest


class ZammadClient:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    async def create_ticket(self, payload: IntakeRequest) -> dict[str, Any]:
        if not self.settings.zammad_token:
            raise RuntimeError("Zammad token is not configured")

        description = (
            "Новая заявка Pixel SC\n\n"
            f"Клиент: {payload.customer_name}\n"
            f"Телефон: {payload.phone}\n"
            f"Устройство: {payload.device}\n"
            f"Проблема: {payload.problem}\n"
            f"Сервис-поинт: {payload.service_point}\n"
            f"Telegram user id: {payload.tg_user_id}\n"
            f"Telegram username: {payload.tg_username or '-'}"
        )

        request_data = {
            "title": f"[Pixel SC] {payload.device} - {payload.customer_name}",
            "group": self.settings.zammad_group,
            "customer_id": self.settings.zammad_customer_id,
            "priority_id": self.settings.zammad_priority,
            "state": self.settings.zammad_state,
            "article": {
                "subject": "Заявка из Telegram-бота",
                "body": description,
                "type": "note",
                "internal": False,
            },
        }

        headers = {
            "Authorization": f"Token token={self.settings.zammad_token}",
            "Content-Type": "application/json",
        }

        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.post(
                f"{self.settings.zammad_base_url.rstrip('/')}/api/v1/tickets",
                headers=headers,
                json=request_data,
            )
            resp.raise_for_status()
            data = resp.json()

        return {
            "ticket_id": data.get("id"),
            "ticket_number": str(data.get("number") or ""),
            "raw": data,
        }

