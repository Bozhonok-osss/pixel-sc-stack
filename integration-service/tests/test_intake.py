from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from app import main as main_module


def _client(tmp_path: Path) -> TestClient:
    db_path = tmp_path / "integration-test.db"
    main_module.settings.sqlite_path = str(db_path)  # type: ignore[misc]
    main_module.settings.integration_token = "test-token"  # type: ignore[misc]
    main_module.on_startup()
    return TestClient(main_module.app)


def test_intake_success_and_replay(monkeypatch, tmp_path: Path):
    async def fake_zammad_create(payload):
        return {"ticket_id": 101, "ticket_number": "101"}

    async def fake_erp_create(payload, zammad_ticket_number):
        return {"issue": None}

    monkeypatch.setattr(main_module.zammad, "create_ticket", fake_zammad_create)
    monkeypatch.setattr(main_module.erpnext, "create_issue", fake_erp_create)

    client = _client(tmp_path)
    headers = {
        "Authorization": "Bearer test-token",
        "Idempotency-Key": "abc-1",
    }
    payload = {
        "customer_name": "Иван",
        "phone": "+79990000000",
        "device": "iPhone 13",
        "problem": "Не включается",
        "service_point": "Белореченская",
        "tg_user_id": 123,
        "tg_username": "ivan",
    }

    first = client.post("/api/intake", json=payload, headers=headers)
    assert first.status_code == 200
    assert first.json()["zammad_ticket_number"] == "101"
    assert first.json()["replayed"] is False

    second = client.post("/api/intake", json=payload, headers=headers)
    assert second.status_code == 200
    assert second.json()["replayed"] is True


def test_intake_requires_token(tmp_path: Path):
    client = _client(tmp_path)
    payload = {
        "customer_name": "Иван",
        "phone": "+79990000000",
        "device": "iPhone 13",
        "problem": "Не включается",
        "service_point": "Белореченская",
        "tg_user_id": 123,
        "tg_username": "ivan",
    }
    resp = client.post("/api/intake", json=payload)
    assert resp.status_code == 401

