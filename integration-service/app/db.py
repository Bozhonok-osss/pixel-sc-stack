from __future__ import annotations

import hashlib
import json
import sqlite3
from pathlib import Path
from typing import Any


def init_db(sqlite_path: str) -> None:
    db_file = Path(sqlite_path)
    db_file.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(sqlite_path) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS intake_requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                idempotency_key TEXT UNIQUE,
                request_hash TEXT NOT NULL,
                request_body TEXT NOT NULL,
                response_body TEXT,
                status TEXT NOT NULL,
                error_text TEXT,
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                updated_at TEXT NOT NULL DEFAULT (datetime('now'))
            )
            """
        )
        conn.execute(
            """
            CREATE TRIGGER IF NOT EXISTS set_intake_updated_at
            AFTER UPDATE ON intake_requests
            FOR EACH ROW
            BEGIN
                UPDATE intake_requests SET updated_at = datetime('now') WHERE id = OLD.id;
            END
            """
        )
        conn.commit()


def _json_dumps(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False, sort_keys=True)


def compute_hash(data: dict[str, Any]) -> str:
    return hashlib.sha256(_json_dumps(data).encode("utf-8")).hexdigest()


def find_by_idempotency(sqlite_path: str, idempotency_key: str) -> dict[str, Any] | None:
    with sqlite3.connect(sqlite_path) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            """
            SELECT id, idempotency_key, request_hash, request_body, response_body, status, error_text
            FROM intake_requests
            WHERE idempotency_key = ?
            """,
            (idempotency_key,),
        ).fetchone()
    return dict(row) if row else None


def save_success(
    sqlite_path: str,
    *,
    idempotency_key: str | None,
    request_hash: str,
    request_body: dict[str, Any],
    response_body: dict[str, Any],
) -> None:
    with sqlite3.connect(sqlite_path) as conn:
        if idempotency_key:
            conn.execute(
                """
                INSERT INTO intake_requests(idempotency_key, request_hash, request_body, response_body, status)
                VALUES(?, ?, ?, ?, 'success')
                ON CONFLICT(idempotency_key) DO UPDATE SET
                    request_hash = excluded.request_hash,
                    request_body = excluded.request_body,
                    response_body = excluded.response_body,
                    status = 'success',
                    error_text = NULL
                """,
                (idempotency_key, request_hash, _json_dumps(request_body), _json_dumps(response_body)),
            )
        else:
            conn.execute(
                """
                INSERT INTO intake_requests(idempotency_key, request_hash, request_body, response_body, status)
                VALUES(NULL, ?, ?, ?, 'success')
                """,
                (request_hash, _json_dumps(request_body), _json_dumps(response_body)),
            )
        conn.commit()


def save_error(
    sqlite_path: str,
    *,
    idempotency_key: str | None,
    request_hash: str,
    request_body: dict[str, Any],
    error_text: str,
) -> None:
    with sqlite3.connect(sqlite_path) as conn:
        if idempotency_key:
            conn.execute(
                """
                INSERT INTO intake_requests(idempotency_key, request_hash, request_body, status, error_text)
                VALUES(?, ?, ?, 'error', ?)
                ON CONFLICT(idempotency_key) DO UPDATE SET
                    request_hash = excluded.request_hash,
                    request_body = excluded.request_body,
                    status = 'error',
                    error_text = excluded.error_text
                """,
                (idempotency_key, request_hash, _json_dumps(request_body), error_text),
            )
        else:
            conn.execute(
                """
                INSERT INTO intake_requests(idempotency_key, request_hash, request_body, status, error_text)
                VALUES(NULL, ?, ?, 'error', ?)
                """,
                (request_hash, _json_dumps(request_body), error_text),
            )
        conn.commit()

