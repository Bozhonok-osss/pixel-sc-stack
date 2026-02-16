from __future__ import annotations

import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any

BRANCH_SEED = [
    (
        1,
        "Белореченская",
        "ул. Белореченская, 28, 1 этаж, салон связи МОТИВ (ТЦ GOODMART)",
        "09:00-21:00",
        56.8168,
        60.5625,
    ),
    (
        2,
        "Дирижабль",
        "ТЦ Дирижабль, 1 этаж, салон связи МОТИВ (ул. Академика Шварца, 17)",
        "10:00-22:00",
        56.7969,
        60.6268,
    ),
    (
        3,
        "Титова",
        "ул. Титова, 26, салон связи МОТИВ",
        "09:00-20:00",
        56.7798,
        60.6096,
    ),
]


def get_conn(sqlite_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(sqlite_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(sqlite_path: str) -> None:
    db_file = Path(sqlite_path)
    db_file.parent.mkdir(parents=True, exist_ok=True)
    with get_conn(sqlite_path) as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS branches (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                address TEXT NOT NULL,
                schedule TEXT NOT NULL,
                lat REAL,
                lon REAL
            );

            CREATE TABLE IF NOT EXISTS support_staff (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER UNIQUE NOT NULL,
                name TEXT,
                created_at TEXT NOT NULL DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                number TEXT UNIQUE NOT NULL,
                status TEXT NOT NULL DEFAULT 'new',
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                updated_at TEXT NOT NULL DEFAULT (datetime('now')),
                branch_id INTEGER NOT NULL,
                branch_name TEXT,
                branch_address TEXT,
                client_name TEXT NOT NULL,
                client_phone TEXT NOT NULL,
                client_telegram TEXT NOT NULL,
                device_type TEXT NOT NULL,
                model TEXT,
                problem_description TEXT NOT NULL,
                zammad_ticket_number TEXT,
                erpnext_issue TEXT,
                price REAL NOT NULL DEFAULT 0,
                cost REAL NOT NULL DEFAULT 0,
                FOREIGN KEY(branch_id) REFERENCES branches(id)
            );

            CREATE TRIGGER IF NOT EXISTS set_orders_updated_at
            AFTER UPDATE ON orders
            FOR EACH ROW
            BEGIN
                UPDATE orders SET updated_at = datetime('now') WHERE id = OLD.id;
            END;
            """
        )
        for branch in BRANCH_SEED:
            conn.execute(
                """
                INSERT INTO branches(id, name, address, schedule, lat, lon)
                VALUES(?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO NOTHING
                """,
                branch,
            )
        conn.commit()


def next_order_number(conn: sqlite3.Connection) -> str:
    prefix = datetime.now().strftime("PIX-%Y%m-")
    row = conn.execute(
        "SELECT number FROM orders WHERE number LIKE ? ORDER BY id DESC LIMIT 1",
        (f"{prefix}%",),
    ).fetchone()
    if row and row["number"]:
        last_seq = int(row["number"].split("-")[-1])
    else:
        last_seq = 0
    return f"{prefix}{last_seq + 1:04d}"


def row_to_dict(row: sqlite3.Row | None) -> dict[str, Any] | None:
    return dict(row) if row else None

