from __future__ import annotations

import re
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
            "New Pixel SC intake\n\n"
            f"Customer: {payload.customer_name}\n"
            f"Phone: {payload.phone}\n"
            f"Device: {payload.device}\n"
            f"Problem: {payload.problem}\n"
            f"Service point: {payload.service_point}\n"
            f"Telegram user id: {payload.tg_user_id}\n"
            f"Telegram username: {payload.tg_username or '-'}"
        )

        headers = {
            "Authorization": f"Token token={self.settings.zammad_token}",
            "Content-Type": "application/json",
        }

        async with httpx.AsyncClient(timeout=20) as client:
            customer_id = await self._resolve_customer_id(client, headers, payload)
            request_data = {
                "title": f"[Pixel SC] {payload.device} - {payload.customer_name}",
                "group": self.settings.zammad_group,
                "customer_id": customer_id,
                "priority_id": self.settings.zammad_priority,
                "state": self.settings.zammad_state,
                "article": {
                    "subject": "Intake from Telegram bot",
                    "body": description,
                    "type": "note",
                    "internal": False,
                },
            }
            if self.settings.zammad_intake_channel_field:
                request_data[self.settings.zammad_intake_channel_field] = (
                    self.settings.zammad_channel_telegram_value
                )
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

    async def _resolve_customer_id(
        self,
        client: httpx.AsyncClient,
        headers: dict[str, str],
        payload: IntakeRequest,
    ) -> int:
        email = self._build_customer_email(payload)
        user_payload = self._build_customer_payload(payload, email)
        user_id = await self._find_user_id_by_email(client, headers, email)
        if user_id is not None:
            await client.put(
                f"{self.settings.zammad_base_url.rstrip('/')}/api/v1/users/{user_id}",
                headers=headers,
                json=user_payload,
            )
            return user_id

        create_resp = await client.post(
            f"{self.settings.zammad_base_url.rstrip('/')}/api/v1/users",
            headers=headers,
            json=user_payload,
        )
        if create_resp.status_code >= 400:
            existing_id = await self._find_user_id_by_email(client, headers, email)
            if existing_id is not None:
                return existing_id
            # Keep old behavior as fallback if dynamic customer creation fails.
            return self.settings.zammad_customer_id

        create_data = create_resp.json()
        created_id = create_data.get("id")
        if isinstance(created_id, int):
            return created_id
        return self.settings.zammad_customer_id

    async def _find_user_id_by_email(
        self,
        client: httpx.AsyncClient,
        headers: dict[str, str],
        email: str,
    ) -> int | None:
        search_resp = await client.get(
            f"{self.settings.zammad_base_url.rstrip('/')}/api/v1/users/search",
            headers=headers,
            params={"query": f"email:{email}"},
        )
        if search_resp.status_code >= 400:
            return None

        data = search_resp.json()
        if not isinstance(data, list) or not data:
            return None

        first = data[0]
        if not isinstance(first, dict):
            return None

        user_id = first.get("id")
        if isinstance(user_id, int):
            return user_id
        return None

    def _build_customer_payload(self, payload: IntakeRequest, email: str) -> dict[str, Any]:
        firstname, lastname = self._split_name(payload.customer_name)
        username = (payload.tg_username or "").lstrip("@")
        note_lines = [f"Telegram user id: {payload.tg_user_id}"]
        if username:
            note_lines.append(f"Telegram username: @{username}")

        return {
            "firstname": firstname,
            "lastname": lastname,
            "email": email,
            "mobile": payload.phone,
            "phone": payload.phone,
            "note": "\n".join(note_lines),
        }

    def _build_customer_email(self, payload: IntakeRequest) -> str:
        if payload.tg_user_id > 0:
            return f"tg_{payload.tg_user_id}@local.invalid"
        digits = re.sub(r"\D", "", payload.phone)
        if digits:
            return f"phone_{digits}@local.invalid"
        return f"customer_{abs(hash(payload.customer_name))}@local.invalid"

    def _split_name(self, customer_name: str) -> tuple[str, str]:
        parts = customer_name.strip().split()
        if not parts:
            return "Customer", ""
        if len(parts) == 1:
            return parts[0], ""
        return parts[0], " ".join(parts[1:])
