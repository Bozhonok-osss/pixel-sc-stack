# Pixel SC Integration Service

FastAPI service that accepts intake payloads from Pixel backend and creates tickets in Zammad, with optional Issue creation in ERPNext.

## Features

- `POST /api/intake`
- `POST /api/zammad/close-sync`
- Bearer token auth
- `Idempotency-Key` support
- SQLite persistence of results
- Zammad ticket creation
- Optional ERPNext Issue creation
- ERPNext close sync on ticket lifecycle completion

## Zammad channel mapping

If you created a custom Ticket field in Zammad for intake channel (for example `intake_channel`),
you can auto-mark Telegram tickets with:

- `ZAMMAD_INTAKE_CHANNEL_FIELD=intake_channel`
- `ZAMMAD_CHANNEL_TELEGRAM_VALUE=telegram`

## Zammad user Telegram mapping

If you added custom User fields in Zammad, you can map Telegram data into them:

- `ZAMMAD_USER_TG_USERNAME_FIELD=tg_username` (example)
- `ZAMMAD_USER_TG_ID_FIELD=tg_uid` (example)

Leave them empty to skip mapping.

## Close sync payload

Use this endpoint from a Zammad webhook/trigger when a ticket is completed.

`POST /api/zammad/close-sync`

Headers:

- `Authorization: Bearer <INTEGRATION_TOKEN>`
- `Content-Type: application/json`

Body example:

```json
{
  "zammad_ticket_number": "67021",
  "erp_issue_ref": "ISS-2026-00021",
  "status": "Issued to customer",
  "owner": "Master One",
  "approved_price": 12000,
  "repair_cost": 7000,
  "warranty_days": 30,
  "net_profit": 5000,
  "note": "Device tested, all functions OK"
}
```

`erp_issue_ref` is optional. If omitted, service tries to find ERP Issue by `zammad_ticket_number` using stored intake records in SQLite.

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
