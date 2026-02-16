# Pixel SC Integration Service

FastAPI service that accepts intake payloads from Pixel backend and creates tickets in Zammad, with optional Issue creation in ERPNext.

## Features

- `POST /api/intake`
- Bearer token auth
- `Idempotency-Key` support
- SQLite persistence of results
- Zammad ticket creation
- Optional ERPNext Issue creation

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
