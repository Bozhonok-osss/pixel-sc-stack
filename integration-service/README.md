# Pixel SC Integration Service

FastAPI service that accepts intake payloads from Pixel backend and creates tickets in Zammad, with optional Issue creation in ERPNext.

## Features

- `POST /api/intake`
- Bearer token auth
- `Idempotency-Key` support
- SQLite persistence of results
- Zammad ticket creation
- Optional ERPNext Issue creation

## Zammad channel mapping

If you created a custom Ticket field in Zammad for intake channel (for example `intake_channel`),
you can auto-mark Telegram tickets with:

- `ZAMMAD_INTAKE_CHANNEL_FIELD=intake_channel`
- `ZAMMAD_CHANNEL_TELEGRAM_VALUE=telegram`

## Zammad user Telegram mapping

If you added custom User fields in Zammad, you can map Telegram data into them:

- `ZAMMAD_USER_TG_USERNAME_FIELD=tg_username` (example)
- `ZAMMAD_USER_TG_ID_FIELD=tg_user_id` (example)

Leave them empty to skip mapping.

## Run locally

```bash
cd integration-service
python -m venv .venv
. .venv/Scripts/activate
pip install -r requirements.txt
copy .env.example .env
uvicorn app.main:app --reload --port 8090
```

## Run tests

```bash
cd integration-service
pytest -q
```
