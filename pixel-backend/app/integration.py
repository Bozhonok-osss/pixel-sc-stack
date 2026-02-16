from __future__ import annotations

from typing import Any
from uuid import uuid4

import httpx

from app.config import Settings


class IntegrationClient:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    async def create_intake(self, payload: dict[str, Any]) -> dict[str, Any] | None:
        if not self.settings.integration_url or not self.settings.integration_token:
            return None
        headers = {
            "Authorization": f"Bearer {self.settings.integration_token}",
            "Idempotency-Key": str(uuid4()),
        }
        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.post(
                f"{self.settings.integration_url.rstrip('/')}/api/intake",
                headers=headers,
                json=payload,
            )
            resp.raise_for_status()
            return resp.json()

