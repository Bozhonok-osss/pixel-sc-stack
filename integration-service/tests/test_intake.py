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

    async def fake_set_ticket_erp_issue(ticket_id, issue_ref):
        raise AssertionError("set_ticket_erp_issue should not be called when ERP issue is missing")

    monkeypatch.setattr(main_module.zammad, "create_ticket", fake_zammad_create)
    monkeypatch.setattr(main_module.zammad, "set_ticket_erp_issue", fake_set_ticket_erp_issue)
    monkeypatch.setattr(main_module.erpnext, "create_issue", fake_erp_create)

    client = _client(tmp_path)
    headers = {
        "Authorization": "Bearer test-token",
        "Idempotency-Key": "abc-1",
    }
    payload = {
        "customer_name": "Ivan",
        "phone": "+79990000000",
        "device": "iPhone 13",
        "device_type": "Smartphone",
        "model": "A2633",
        "problem": "Does not power on",
        "service_point": "Belorechenskaya",
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


def test_intake_sets_erp_issue_ref_in_zammad(monkeypatch, tmp_path: Path):
    async def fake_zammad_create(payload):
        return {"ticket_id": 202, "ticket_number": "67022"}

    async def fake_erp_create(payload, zammad_ticket_number):
        return {"issue": "ISS-2026-00001"}

    calls: list[tuple[int, str]] = []

    async def fake_set_ticket_erp_issue(ticket_id, issue_ref):
        calls.append((ticket_id, issue_ref))

    monkeypatch.setattr(main_module.zammad, "create_ticket", fake_zammad_create)
    monkeypatch.setattr(main_module.zammad, "set_ticket_erp_issue", fake_set_ticket_erp_issue)
    monkeypatch.setattr(main_module.erpnext, "create_issue", fake_erp_create)

    client = _client(tmp_path)
    headers = {
        "Authorization": "Bearer test-token",
        "Idempotency-Key": "erp-link-1",
    }
    payload = {
        "customer_name": "Ivan",
        "phone": "+79990000000",
        "device": "iPhone 13",
        "problem": "Does not power on",
        "service_point": "Belorechenskaya",
        "tg_user_id": 123,
        "tg_username": "ivan",
    }
    resp = client.post("/api/intake", json=payload, headers=headers)
    assert resp.status_code == 200
    assert calls == [(202, "ISS-2026-00001")]


def test_intake_requires_token(tmp_path: Path):
    client = _client(tmp_path)
    payload = {
        "customer_name": "Ivan",
        "phone": "+79990000000",
        "device": "iPhone 13",
        "problem": "Does not power on",
        "service_point": "Belorechenskaya",
        "tg_user_id": 123,
        "tg_username": "ivan",
    }
    resp = client.post("/api/intake", json=payload)
    assert resp.status_code == 401


def test_close_sync_updates_erp_issue(monkeypatch, tmp_path: Path):
    async def fake_sync_close(issue_name, payload):
        assert issue_name == "ISS-2026-00099"
        return {"issue": issue_name, "updated": True}

    monkeypatch.setattr(main_module, "find_erp_issue_by_ticket_number", lambda *_: "ISS-2026-00099")
    monkeypatch.setattr(main_module.erpnext, "sync_close", fake_sync_close)

    client = _client(tmp_path)
    headers = {"Authorization": "Bearer test-token"}
    payload = {
        "zammad_ticket_number": "67099",
        "status": "Issued to customer",
        "owner": "Master One",
        "approved_price": 12000,
        "repair_cost": 7000,
        "warranty_days": 30,
        "net_profit": 5000,
    }
    resp = client.post("/api/zammad/close-sync", json=payload, headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert body["updated"] is True
    assert body["erpnext_issue"] == "ISS-2026-00099"


def test_close_sync_skips_when_issue_not_found(monkeypatch, tmp_path: Path):
    async def fake_sync_close(issue_name, payload):
        raise AssertionError("sync_close should not be called")

    monkeypatch.setattr(main_module, "find_erp_issue_by_ticket_number", lambda *_: None)
    monkeypatch.setattr(main_module.erpnext, "sync_close", fake_sync_close)

    client = _client(tmp_path)
    headers = {"Authorization": "Bearer test-token"}
    payload = {
        "zammad_ticket_number": "67111",
        "status": "Closed",
    }
    resp = client.post("/api/zammad/close-sync", json=payload, headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert body["updated"] is False
    assert body["erpnext_issue"] is None
