from __future__ import annotations

import json
from typing import Annotated

from fastapi import Depends, FastAPI, Header, HTTPException, status

from app.config import Settings, load_settings
from app.db import compute_hash, find_by_idempotency, init_db, save_error, save_success
from app.erpnext import ERPNextClient
from app.models import IntakeRequest, IntakeResponse
from app.zammad import ZammadClient

app = FastAPI(title="Pixel SC Integration Service", version="0.1.0")
settings = load_settings()
zammad = ZammadClient(settings)
erpnext = ERPNextClient(settings)


@app.on_event("startup")
def on_startup() -> None:
    init_db(settings.sqlite_path)


def require_token(authorization: Annotated[str | None, Header()] = None) -> None:
    if not settings.integration_token:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Server token is not configured")
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing bearer token")
    token = authorization.replace("Bearer ", "", 1).strip()
    if token != settings.integration_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/intake", response_model=IntakeResponse, dependencies=[Depends(require_token)])
async def intake(
    payload: IntakeRequest,
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
) -> IntakeResponse:
    body = payload.model_dump()
    body_hash = compute_hash(body)

    if idempotency_key:
        existing = find_by_idempotency(settings.sqlite_path, idempotency_key)
        if existing:
            if existing["request_hash"] != body_hash:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Idempotency-Key reused with different payload",
                )
            if existing["status"] == "success" and existing["response_body"]:
                response_data = json.loads(existing["response_body"])
                response_data["replayed"] = True
                return IntakeResponse(**response_data)

    try:
        zammad_result = await zammad.create_ticket(payload)
        erp_result = await erpnext.create_issue(payload, zammad_result.get("ticket_number"))
        response_data = {
            "success": True,
            "idempotency_key": idempotency_key,
            "zammad_ticket_id": zammad_result.get("ticket_id"),
            "zammad_ticket_number": zammad_result.get("ticket_number"),
            "erpnext_issue": erp_result.get("issue"),
            "replayed": False,
        }
        save_success(
            settings.sqlite_path,
            idempotency_key=idempotency_key,
            request_hash=body_hash,
            request_body=body,
            response_body=response_data,
        )
        return IntakeResponse(**response_data)
    except HTTPException:
        raise
    except Exception as exc:
        save_error(
            settings.sqlite_path,
            idempotency_key=idempotency_key,
            request_hash=body_hash,
            request_body=body,
            error_text=str(exc),
        )
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"Integration error: {exc}") from exc

