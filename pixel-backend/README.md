# Pixel Backend

FastAPI backend for Telegram bot.

## Endpoints used by bot

- `POST /api/orders`
- `GET /api/orders/{number_or_id}`
- `GET /api/orders`
- `POST /api/orders/{order_id}/update`
- `GET /api/branches/public`
- `GET /api/support-staff`
- `POST /api/support-staff`
- `GET /api/company-settings`
- `GET /api/analytics/summary`
- `GET /api/reports/csv`
- `GET /api/reports/xlsx`

## Local run

```bash
cd pixel-backend
python -m venv .venv
. .venv/Scripts/activate
pip install -r requirements.txt
copy .env.example .env
uvicorn app.main:app --reload --port 8000
```
