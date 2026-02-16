from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def _as_bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass
class Settings:
    integration_token: str
    webhook_basic_user: str
    webhook_basic_password: str
    sqlite_path: str
    zammad_base_url: str
    zammad_token: str
    zammad_customer_id: int
    zammad_group: str
    zammad_priority: int
    zammad_state: str
    zammad_intake_channel_field: str
    zammad_channel_telegram_value: str
    zammad_user_tg_username_field: str
    zammad_user_tg_id_field: str
    zammad_erp_issue_field: str
    enable_erp_issue: bool
    erpnext_base_url: str
    erpnext_api_key: str
    erpnext_api_secret: str
    erpnext_issue_doctype: str


def load_settings() -> Settings:
    default_db = str(Path(__file__).resolve().parents[1] / "data" / "integration.db")
    return Settings(
        integration_token=os.getenv("INTEGRATION_TOKEN", ""),
        webhook_basic_user=os.getenv("WEBHOOK_BASIC_USER", ""),
        webhook_basic_password=os.getenv("WEBHOOK_BASIC_PASSWORD", ""),
        sqlite_path=os.getenv("SQLITE_PATH", default_db),
        zammad_base_url=os.getenv("ZAMMAD_BASE_URL", "http://127.0.0.1:8080"),
        zammad_token=os.getenv("ZAMMAD_TOKEN", ""),
        zammad_customer_id=int(os.getenv("ZAMMAD_CUSTOMER_ID", "1")),
        zammad_group=os.getenv("ZAMMAD_GROUP", "Users"),
        zammad_priority=int(os.getenv("ZAMMAD_PRIORITY_ID", "2")),
        zammad_state=os.getenv("ZAMMAD_STATE", "new"),
        zammad_intake_channel_field=os.getenv("ZAMMAD_INTAKE_CHANNEL_FIELD", ""),
        zammad_channel_telegram_value=os.getenv("ZAMMAD_CHANNEL_TELEGRAM_VALUE", "telegram"),
        zammad_user_tg_username_field=os.getenv("ZAMMAD_USER_TG_USERNAME_FIELD", ""),
        zammad_user_tg_id_field=os.getenv("ZAMMAD_USER_TG_ID_FIELD", ""),
        zammad_erp_issue_field=os.getenv("ZAMMAD_ERP_ISSUE_FIELD", "erp_issue_ref"),
        enable_erp_issue=_as_bool(os.getenv("ENABLE_ERP_ISSUE"), default=False),
        erpnext_base_url=os.getenv("ERPNEXT_BASE_URL", "http://127.0.0.1:8081"),
        erpnext_api_key=os.getenv("ERPNEXT_API_KEY", ""),
        erpnext_api_secret=os.getenv("ERPNEXT_API_SECRET", ""),
        erpnext_issue_doctype=os.getenv("ERPNEXT_ISSUE_DOCTYPE", "Issue"),
    )
