"""Parameterized query functions for `maintenance_log_entry`."""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone

from app.models.rows import MaintenanceLogEntry


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def create(
    conn: sqlite3.Connection,
    *,
    bike_id: int | None,
    component_id: int | None,
    description: str,
    performed_at: str,
    mileage_at_service: float,
    schedule_id: int | None = None,
) -> MaintenanceLogEntry:
    now = _now()
    cursor = conn.execute(
        """
        INSERT INTO maintenance_log_entry (
            bike_id, component_id, description, performed_at, mileage_at_service,
            schedule_id, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (bike_id, component_id, description, performed_at, mileage_at_service, schedule_id, now, now),
    )
    entry = get_by_id(conn, cursor.lastrowid)
    assert entry is not None
    return entry


def get_by_id(conn: sqlite3.Connection, entry_id: int) -> MaintenanceLogEntry | None:
    row = conn.execute(
        "SELECT * FROM maintenance_log_entry WHERE id = ?", (entry_id,)
    ).fetchone()
    return MaintenanceLogEntry.from_row(row) if row else None


def list_for_bike(conn: sqlite3.Connection, bike_id: int) -> list[MaintenanceLogEntry]:
    rows = conn.execute(
        "SELECT * FROM maintenance_log_entry WHERE bike_id = ? ORDER BY performed_at, id",
        (bike_id,),
    ).fetchall()
    return [MaintenanceLogEntry.from_row(row) for row in rows]


def list_for_component(conn: sqlite3.Connection, component_id: int) -> list[MaintenanceLogEntry]:
    rows = conn.execute(
        "SELECT * FROM maintenance_log_entry WHERE component_id = ? ORDER BY performed_at, id",
        (component_id,),
    ).fetchall()
    return [MaintenanceLogEntry.from_row(row) for row in rows]


def update(
    conn: sqlite3.Connection,
    entry_id: int,
    *,
    description: str,
    performed_at: str,
    mileage_at_service: float,
) -> MaintenanceLogEntry:
    conn.execute(
        """
        UPDATE maintenance_log_entry
        SET description = ?, performed_at = ?, mileage_at_service = ?, updated_at = ?
        WHERE id = ?
        """,
        (description, performed_at, mileage_at_service, _now(), entry_id),
    )
    entry = get_by_id(conn, entry_id)
    assert entry is not None
    return entry


def delete(conn: sqlite3.Connection, entry_id: int) -> None:
    conn.execute("DELETE FROM maintenance_log_entry WHERE id = ?", (entry_id,))


def has_entries_for_bike(conn: sqlite3.Connection, bike_id: int) -> bool:
    row = conn.execute(
        "SELECT 1 FROM maintenance_log_entry WHERE bike_id = ? LIMIT 1", (bike_id,)
    ).fetchone()
    return row is not None


def has_entries_for_component(conn: sqlite3.Connection, component_id: int) -> bool:
    row = conn.execute(
        "SELECT 1 FROM maintenance_log_entry WHERE component_id = ? LIMIT 1", (component_id,)
    ).fetchone()
    return row is not None
