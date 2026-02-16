import os
from dataclasses import dataclass
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parents[2]
ROOT_ENV = BASE_DIR / ".env"
BOT_ENV = BASE_DIR / "bot" / ".env"

# Keep Docker/env vars as source of truth; .env only fills missing values.
load_dotenv(ROOT_ENV, override=False)
load_dotenv(BOT_ENV, override=False)


def _parse_admin_ids(raw: str | None) -> set[int]:
    if not raw:
        return set()
    return {int(x.strip()) for x in raw.split(",") if x.strip().isdigit()}


@dataclass
class Settings:
    bot_token: str
    backend_url: str
    bot_api_token: str
    admin_ids: set[int]
    support_staff_ids: set[int]
    timezone: str
    support_phone: str
    company_name: str
    company_inn: str
    company_ogrn: str
    company_address: str
    company_phone: str


settings = Settings(
    bot_token=os.getenv("BOT_TOKEN_TELEGRAM", ""),
    backend_url=os.getenv("BACKEND_URL", "http://127.0.0.1:8000"),
    bot_api_token=os.getenv("BOT_API_TOKEN", ""),
    admin_ids=_parse_admin_ids(os.getenv("ADMIN_IDS")),
    support_staff_ids=_parse_admin_ids(os.getenv("SUPPORT_STAFF_IDS")),
    timezone=os.getenv("TIMEZONE", "Asia/Yekaterinburg"),
    support_phone=os.getenv("SUPPORT_PHONE", "+7XXXXXXXXXX"),
    company_name=os.getenv("COMPANY_NAME", "Pixel SC"),
    company_inn=os.getenv("COMPANY_INN", "0000000000"),
    company_ogrn=os.getenv("COMPANY_OGRN", ""),
    company_address=os.getenv("COMPANY_ADDRESS", ""),
    company_phone=os.getenv("COMPANY_PHONE", ""),
)
