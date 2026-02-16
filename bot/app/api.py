from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import aiohttp

from app.config import settings


@dataclass
class ApiClient:
    base_url: str
    bot_token: str

    async def _request(self, method: str, path: str, **kwargs: Any) -> Any:
        url = f"{self.base_url}{path}"
        headers = kwargs.pop("headers", {})
        headers["X-Bot-Token"] = self.bot_token
        async with aiohttp.ClientSession() as session:
            async with session.request(method, url, headers=headers, **kwargs) as resp:
                if resp.status >= 400:
                    text = await resp.text()
                    raise RuntimeError(f"API {resp.status}: {text}")
                content_type = resp.headers.get("Content-Type", "")
                if "application/json" in content_type:
                    return await resp.json()
                return await resp.read()

    async def create_order(self, payload: dict) -> dict:
        return await self._request("POST", "/api/orders", json=payload)

    async def get_order(self, number_or_id: str) -> dict:
        return await self._request("GET", f"/api/orders/{number_or_id}")

    async def list_orders(self, params: dict) -> list[dict]:
        return await self._request("GET", "/api/orders", params=params)

    async def update_order(self, order_id: int, payload: dict) -> dict:
        return await self._request("POST", f"/api/orders/{order_id}/update", json=payload)

    async def analytics_summary(self, date_from: str, date_to: str) -> dict:
        return await self._request(
            "GET",
            "/api/analytics/summary",
            params={"date_from": date_from, "date_to": date_to},
        )

    async def export_csv(self) -> bytes:
        return await self._request("GET", "/api/reports/csv")

    async def export_xlsx(self) -> bytes:
        return await self._request("GET", "/api/reports/xlsx")

    async def get_company_settings(self) -> dict:
        return await self._request("GET", "/api/company-settings")

    async def list_branches_public(self) -> list[dict]:
        return await self._request("GET", "/api/branches/public")

    async def list_support_staff(self) -> list[dict]:
        return await self._request("GET", "/api/support-staff")

    async def add_support_staff(self, telegram_id: int, name: str | None = None) -> dict:
        payload = {"telegram_id": telegram_id, "name": name}
        return await self._request("POST", "/api/support-staff", json=payload)


api = ApiClient(settings.backend_url, settings.bot_api_token)
