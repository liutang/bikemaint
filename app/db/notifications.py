"""Parameterized query functions for `notification`."""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone

from app.models.rows import Notification


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def get_by_id(conn: sqlite3.Connection, notification_id: int) -> Notification | None:
    row = conn.execute("SELECT * FROM notification WHERE id = ?", (notification_id,)).fetchone()
    return Notification.from_row(row) if row else None


def insert(
    conn: sqlite3.Connection, *, schedule_id: int, cycle_number: int, projected_due_at: str
) -> Notification | None:
    """Record a notification, or return None if one already exists for this
    `(schedule_id, cycle_number)` — the dedup guarantee of FR-015."""
    cursor = conn.execute(
        """
        INSERT OR IGNORE INTO notification (schedule_id, cycle_number, projected_due_at, created_at)
        VALUES (?, ?, ?, ?)
        """,
        (schedule_id, cycle_number, projected_due_at, _now()),
    )
    if cursor.rowcount == 0:
        return None
    return get_by_id(conn, cursor.lastrowid)


def list_unacknowledged(conn: sqlite3.Connection) -> list[Notification]:
    rows = conn.execute(
        "SELECT * FROM notification WHERE acknowledged_at IS NULL ORDER BY id"
    ).fetchall()
    return [Notification.from_row(row) for row in rows]


def mark_acknowledged(conn: sqlite3.Connection, notification_id: int) -> None:
    conn.execute(
        "UPDATE notification SET acknowledged_at = ? WHERE id = ? AND acknowledged_at IS NULL",
        (_now(), notification_id),
    )


def record_webhook_result(
    conn: sqlite3.Connection, notification_id: int, *, delivered: bool, error: str | None
) -> None:
    conn.execute(
        "UPDATE notification SET webhook_delivered = ?, webhook_delivery_error = ? WHERE id = ?",
        (1 if delivered else 0, error, notification_id),
    )
