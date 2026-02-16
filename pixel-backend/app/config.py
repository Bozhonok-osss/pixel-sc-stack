from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Settings:
    bot_api_token: str
    sqlite_path: str
    timezone: str
    integration_url: str
    integration_token: str
    company_name: str
    company_inn: str
    company_ogrn: str
    company_address: str
    company_phone: str


def load_settings() -> Settings:
    default_db = str(Path(__file__).resolve().parents[1] / "data" / "backend.db")
    return Settings(
        bot_api_token=os.getenv("BOT_API_TOKEN", ""),
        sqlite_path=os.getenv("SQLITE_PATH", default_db),
        timezone=os.getenv("TIMEZONE", "Asia/Yekaterinburg"),
        integration_url=os.getenv("INTEGRATION_URL", "http://integration-service:8090"),
        integration_token=os.getenv("INTEGRATION_TOKEN", ""),
        company_name=os.getenv("COMPANY_NAME", "Pixel SC"),
        company_inn=os.getenv("COMPANY_INN", "0000000000"),
        company_ogrn=os.getenv("COMPANY_OGRN", ""),
        company_address=os.getenv("COMPANY_ADDRESS", ""),
        company_phone=os.getenv("COMPANY_PHONE", ""),
    )

