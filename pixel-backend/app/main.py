from __future__ import annotations

import csv
import io
from datetime import datetime
from typing import Annotated

from fastapi import Depends, FastAPI, Header, HTTPException, Query, Response, status
from openpyxl import Workbook

from app.config import Settings, load_settings
from app.db import get_conn, init_db, next_order_number
from app.integration import IntegrationClient
from app.schemas import (
    AnalyticsSummary,
    BranchOut,
    OrderCreate,
    OrderOut,
    OrderUpdate,
    SupportStaffCreate,
    SupportStaffOut,
)

app = FastAPI(title="Pixel SC Backend", version="0.1.0")
settings = load_settings()
integration_client = IntegrationClient(settings)


@app.on_event("startup")
def startup() -> None:
    init_db(settings.sqlite_path)


def require_bot_token(x_bot_token: Annotated[str | None, Header()] = None) -> None:
    if settings.bot_api_token and x_bot_token != settings.bot_api_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid bot token")


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/orders", response_model=OrderOut, dependencies=[Depends(require_bot_token)])
async def create_order(payload: OrderCreate) -> OrderOut:
    with get_conn(settings.sqlite_path) as conn:
        branch = conn.execute("SELECT * FROM branches WHERE id = ?", (payload.branch_id,)).fetchone()
        if not branch:
            raise HTTPException(status_code=404, detail="Branch not found")
        number = next_order_number(conn)
        cur = conn.execute(
            """
            INSERT INTO orders(
                number, status, branch_id, branch_name, branch_address, client_name, client_phone,
                client_telegram, device_type, model, problem_description
            ) VALUES(?, 'new', ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                number,
                payload.branch_id,
                branch["name"],
                branch["address"],
                payload.client_name,
                payload.client_phone,
                payload.client_telegram,
                payload.device_type,
                payload.model,
                payload.problem_description,
            ),
        )
        order_id = cur.lastrowid
        conn.commit()

        intake_payload = {
            "customer_name": payload.client_name,
            "phone": payload.client_phone,
            "device": f"{payload.device_type} {(payload.model or '').strip()}".strip(),
            "problem": payload.problem_description,
            "service_point": branch["name"],
            "tg_user_id": int(payload.client_telegram) if payload.client_telegram.isdigit() else 0,
            "tg_username": "",
        }
        zammad_ticket_number = None
        erpnext_issue = None
        try:
            intake_result = await integration_client.create_intake(intake_payload)
            if intake_result:
                zammad_ticket_number = intake_result.get("zammad_ticket_number")
                erpnext_issue = intake_result.get("erpnext_issue")
        except Exception:
            pass

        conn.execute(
            "UPDATE orders SET zammad_ticket_number = ?, erpnext_issue = ? WHERE id = ?",
            (zammad_ticket_number, erpnext_issue, order_id),
        )
        conn.commit()
        row = conn.execute("SELECT * FROM orders WHERE id = ?", (order_id,)).fetchone()
        return OrderOut(**dict(row))


@app.get("/api/orders/{number_or_id}", response_model=OrderOut, dependencies=[Depends(require_bot_token)])
def get_order(number_or_id: str) -> OrderOut:
    with get_conn(settings.sqlite_path) as conn:
        if number_or_id.isdigit():
            row = conn.execute("SELECT * FROM orders WHERE id = ?", (int(number_or_id),)).fetchone()
        else:
            row = conn.execute("SELECT * FROM orders WHERE number = ?", (number_or_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Order not found")
        return OrderOut(**dict(row))


@app.get("/api/orders", response_model=list[OrderOut], dependencies=[Depends(require_bot_token)])
def list_orders(client_telegram: str | None = Query(default=None)) -> list[OrderOut]:
    with get_conn(settings.sqlite_path) as conn:
        if client_telegram:
            rows = conn.execute(
                "SELECT * FROM orders WHERE client_telegram = ? ORDER BY id DESC",
                (client_telegram,),
            ).fetchall()
        else:
            rows = conn.execute("SELECT * FROM orders ORDER BY id DESC").fetchall()
        return [OrderOut(**dict(r)) for r in rows]


@app.post("/api/orders/{order_id}/update", response_model=OrderOut, dependencies=[Depends(require_bot_token)])
def update_order(order_id: int, payload: OrderUpdate) -> OrderOut:
    updates: list[str] = []
    params: list[object] = []
    data = payload.model_dump(exclude_none=True)
    for key, value in data.items():
        updates.append(f"{key} = ?")
        params.append(value)
    if not updates:
        return get_order(str(order_id))
    params.append(order_id)
    with get_conn(settings.sqlite_path) as conn:
        conn.execute(f"UPDATE orders SET {', '.join(updates)} WHERE id = ?", params)
        conn.commit()
        row = conn.execute("SELECT * FROM orders WHERE id = ?", (order_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Order not found")
        return OrderOut(**dict(row))


@app.get("/api/branches/public", response_model=list[BranchOut], dependencies=[Depends(require_bot_token)])
def list_branches_public() -> list[BranchOut]:
    with get_conn(settings.sqlite_path) as conn:
        rows = conn.execute("SELECT * FROM branches ORDER BY id ASC").fetchall()
        return [BranchOut(**dict(r)) for r in rows]


@app.get("/api/support-staff", response_model=list[SupportStaffOut], dependencies=[Depends(require_bot_token)])
def list_support_staff() -> list[SupportStaffOut]:
    with get_conn(settings.sqlite_path) as conn:
        rows = conn.execute("SELECT * FROM support_staff ORDER BY id ASC").fetchall()
        return [SupportStaffOut(**dict(r)) for r in rows]


@app.post("/api/support-staff", response_model=SupportStaffOut, dependencies=[Depends(require_bot_token)])
def add_support_staff(payload: SupportStaffCreate) -> SupportStaffOut:
    with get_conn(settings.sqlite_path) as conn:
        conn.execute(
            """
            INSERT INTO support_staff(telegram_id, name)
            VALUES(?, ?)
            ON CONFLICT(telegram_id) DO UPDATE SET name = COALESCE(excluded.name, support_staff.name)
            """,
            (payload.telegram_id, payload.name),
        )
        conn.commit()
        row = conn.execute("SELECT * FROM support_staff WHERE telegram_id = ?", (payload.telegram_id,)).fetchone()
        return SupportStaffOut(**dict(row))


@app.get("/api/company-settings", dependencies=[Depends(require_bot_token)])
def company_settings() -> dict[str, str]:
    return {
        "name": settings.company_name,
        "inn": settings.company_inn,
        "ogrn": settings.company_ogrn,
        "address": settings.company_address,
        "phone": settings.company_phone,
    }


@app.get("/api/analytics/summary", response_model=AnalyticsSummary, dependencies=[Depends(require_bot_token)])
def analytics_summary(date_from: str, date_to: str) -> AnalyticsSummary:
    try:
        dt_from = datetime.fromisoformat(date_from)
        dt_to = datetime.fromisoformat(date_to)
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"Invalid datetime format: {exc}") from exc
    with get_conn(settings.sqlite_path) as conn:
        row = conn.execute(
            """
            SELECT
                COUNT(*) AS orders,
                COALESCE(SUM(price), 0) AS revenue,
                COALESCE(SUM(cost), 0) AS costs
            FROM orders
            WHERE datetime(created_at) BETWEEN datetime(?) AND datetime(?)
            """,
            (dt_from.isoformat(), dt_to.isoformat()),
        ).fetchone()
        revenue = float(row["revenue"] or 0)
        costs = float(row["costs"] or 0)
        return AnalyticsSummary(
            orders=int(row["orders"] or 0),
            revenue=revenue,
            costs=costs,
            profit=revenue - costs,
        )


def _orders_for_report() -> list[dict]:
    with get_conn(settings.sqlite_path) as conn:
        rows = conn.execute("SELECT * FROM orders ORDER BY id DESC").fetchall()
        return [dict(r) for r in rows]


@app.get("/api/reports/csv", dependencies=[Depends(require_bot_token)])
def export_csv() -> Response:
    rows = _orders_for_report()
    header = [
        "id",
        "number",
        "status",
        "created_at",
        "branch_name",
        "client_name",
        "client_phone",
        "device_type",
        "model",
        "problem_description",
        "price",
        "cost",
    ]
    stream = io.StringIO()
    writer = csv.DictWriter(stream, fieldnames=header)
    writer.writeheader()
    for row in rows:
        writer.writerow({k: row.get(k) for k in header})
    return Response(content=stream.getvalue(), media_type="text/csv; charset=utf-8")


@app.get("/api/reports/xlsx", dependencies=[Depends(require_bot_token)])
def export_xlsx() -> Response:
    rows = _orders_for_report()
    wb = Workbook()
    ws = wb.active
    ws.title = "orders"
    header = [
        "id",
        "number",
        "status",
        "created_at",
        "branch_name",
        "client_name",
        "client_phone",
        "device_type",
        "model",
        "problem_description",
        "price",
        "cost",
    ]
    ws.append(header)
    for row in rows:
        ws.append([row.get(k) for k in header])
    output = io.BytesIO()
    wb.save(output)
    return Response(
        content=output.getvalue(),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
