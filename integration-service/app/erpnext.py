from __future__ import annotations

from typing import Any

import httpx

from app.config import Settings
from app.models import CloseSyncRequest, IntakeRequest


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
            "raised_by": payload.customer_name,
            "description": (
                f"Phone: {payload.phone}\n"
                f"Device: {payload.device}\n"
                f"Problem: {payload.problem}\n"
                f"Service point: {payload.service_point}\n"
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

    async def sync_close(self, issue_name: str, payload: CloseSyncRequest) -> dict[str, Any]:
        if not self.is_enabled():
            return {"issue": None, "updated": False, "skipped": True}

        headers = {
            "Authorization": f"token {self.settings.erpnext_api_key}:{self.settings.erpnext_api_secret}",
            "Content-Type": "application/json",
        }
        patch_data: dict[str, Any] = {
            "status": "Closed",
            "description": self._build_close_description(payload),
        }
        if payload.owner:
            patch_data["custom_sc_owner"] = payload.owner
        if payload.approved_price is not None:
            patch_data["custom_sc_approved_price"] = payload.approved_price
        if payload.repair_cost is not None:
            patch_data["custom_sc_repair_cost"] = payload.repair_cost
        if payload.warranty_days is not None:
            patch_data["custom_sc_warranty_days"] = payload.warranty_days
        if payload.net_profit is not None:
            patch_data["custom_sc_net_profit"] = payload.net_profit

        url = f"{self.settings.erpnext_base_url.rstrip('/')}/api/resource/{self.settings.erpnext_issue_doctype}/{issue_name}"
        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.put(url, headers=headers, json=patch_data)
            if resp.status_code >= 400:
                # Fallback for installations without custom fields.
                fallback_patch = {
                    "status": "Closed",
                    "description": self._build_close_description(payload),
                }
                resp = await client.put(url, headers=headers, json=fallback_patch)
            resp.raise_for_status()
            data = resp.json()

        return {"issue": issue_name, "updated": True, "raw": data}

    def _build_close_description(self, payload: CloseSyncRequest) -> str:
        lines = [
            "Pixel SC close sync",
            f"Zammad ticket: {payload.zammad_ticket_number}",
            f"Status: {payload.status}",
        ]
        if payload.owner:
            lines.append(f"Owner: {payload.owner}")
        if payload.approved_price is not None:
            lines.append(f"Approved price: {payload.approved_price}")
        if payload.repair_cost is not None:
            lines.append(f"Repair cost: {payload.repair_cost}")
        if payload.net_profit is not None:
            lines.append(f"Net profit: {payload.net_profit}")
        if payload.warranty_days is not None:
            lines.append(f"Warranty days: {payload.warranty_days}")
        if payload.note:
            lines.append(f"Note: {payload.note}")
        return "\n".join(lines)
