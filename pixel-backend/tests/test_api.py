from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from app import main as main_module


def _client(tmp_path: Path) -> TestClient:
    db_path = tmp_path / "backend-test.db"
    main_module.settings.sqlite_path = str(db_path)  # type: ignore[misc]
    main_module.settings.bot_api_token = "test-token"  # type: ignore[misc]
    main_module.startup()
    return TestClient(main_module.app)


def test_orders_lifecycle(monkeypatch, tmp_path: Path):
    async def fake_intake(payload):
        return {"zammad_ticket_number": "20001", "erpnext_issue": None}

    monkeypatch.setattr(main_module.integration_client, "create_intake", fake_intake)
    client = _client(tmp_path)
    headers = {"X-Bot-Token": "test-token"}

    create = client.post(
        "/api/orders",
        headers=headers,
        json={
            "branch_id": 1,
            "client_name": "Иван",
            "client_phone": "+79990000000",
            "client_telegram": "123",
            "device_type": "Смартфон",
            "model": "iPhone 13",
            "problem_description": "Не включается",
        },
    )
    assert create.status_code == 200
    number = create.json()["number"]
    assert number.startswith("PIX-")
    assert create.json()["zammad_ticket_number"] == "20001"

    get_one = client.get(f"/api/orders/{number}", headers=headers)
    assert get_one.status_code == 200
    assert get_one.json()["client_name"] == "Иван"

    list_resp = client.get("/api/orders", headers=headers, params={"client_telegram": "123"})
    assert list_resp.status_code == 200
    assert len(list_resp.json()) == 1

