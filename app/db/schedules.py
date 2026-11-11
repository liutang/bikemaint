"""Parameterized query functions for `maintenance_schedule`."""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone

from app.models.rows import MaintenanceSchedule


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def create(
    conn: sqlite3.Connection,
    *,
    bike_id: int | None,
    component_id: int | None,
    name: str,
    interval_miles: float | None,
    interval_days: int | None,
    baseline_mileage: float,
    baseline_date: str,
) -> MaintenanceSchedule:
    now = _now()
    cursor = conn.execute(
        """
        INSERT INTO maintenance_schedule (
            bike_id, component_id, name, interval_miles, interval_days,
            baseline_mileage, baseline_date, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            bike_id, component_id, name, interval_miles, interval_days,
            baseline_mileage, baseline_date, now, now,
        ),
    )
    schedule = get_by_id(conn, cursor.lastrowid)
    assert schedule is not None
    return schedule


def get_by_id(conn: sqlite3.Connection, schedule_id: int) -> MaintenanceSchedule | None:
    row = conn.execute(
        "SELECT * FROM maintenance_schedule WHERE id = ?", (schedule_id,)
    ).fetchone()
    return MaintenanceSchedule.from_row(row) if row else None


def list_active_for_bike(conn: sqlite3.Connection, bike_id: int) -> list[MaintenanceSchedule]:
    rows = conn.execute(
        "SELECT * FROM maintenance_schedule WHERE bike_id = ? AND is_active = 1 ORDER BY id",
        (bike_id,),
    ).fetchall()
    return [MaintenanceSchedule.from_row(row) for row in rows]


def list_active_for_component(
    conn: sqlite3.Connection, component_id: int
) -> list[MaintenanceSchedule]:
    rows = conn.execute(
        "SELECT * FROM maintenance_schedule WHERE component_id = ? AND is_active = 1 ORDER BY id",
        (component_id,),
    ).fetchall()
    return [MaintenanceSchedule.from_row(row) for row in rows]


def list_all_active(conn: sqlite3.Connection) -> list[MaintenanceSchedule]:
    rows = conn.execute(
        "SELECT * FROM maintenance_schedule WHERE is_active = 1 ORDER BY id"
    ).fetchall()
    return [MaintenanceSchedule.from_row(row) for row in rows]


def has_active_for_bike(conn: sqlite3.Connection, bike_id: int) -> bool:
    return (
        conn.execute(
            "SELECT 1 FROM maintenance_schedule WHERE bike_id = ? AND is_active = 1 LIMIT 1",
            (bike_id,),
        ).fetchone()
        is not None
    )


def has_active_for_component(conn: sqlite3.Connection, component_id: int) -> bool:
    return (
        conn.execute(
            "SELECT 1 FROM maintenance_schedule WHERE component_id = ? AND is_active = 1 LIMIT 1",
            (component_id,),
        ).fetchone()
        is not None
    )


def update(
    conn: sqlite3.Connection,
    schedule_id: int,
    *,
    name: str,
    interval_miles: float | None,
    interval_days: int | None,
    is_active: bool,
) -> MaintenanceSchedule:
    conn.execute(
        """
        UPDATE maintenance_schedule
        SET name = ?, interval_miles = ?, interval_days = ?, is_active = ?, updated_at = ?
        WHERE id = ?
        """,
        (name, interval_miles, interval_days, 1 if is_active else 0, _now(), schedule_id),
    )
    schedule = get_by_id(conn, schedule_id)
    assert schedule is not None
    return schedule


def complete(
    conn: sqlite3.Connection, schedule_id: int, *, baseline_mileage: float, baseline_date: str
) -> MaintenanceSchedule:
    """Start the next cycle: bump `cycle_number` and reset the baseline (FR-016)."""
    conn.execute(
        """
        UPDATE maintenance_schedule
        SET cycle_number = cycle_number + 1, baseline_mileage = ?, baseline_date = ?, updated_at = ?
        WHERE id = ?
        """,
        (baseline_mileage, baseline_date, _now(), schedule_id),
    )
    schedule = get_by_id(conn, schedule_id)
    assert schedule is not None
    return schedule


def deactivate(conn: sqlite3.Connection, schedule_id: int) -> None:
    """'Delete' a schedule: stop projecting/notifying but keep its history (data-model.md)."""
    conn.execute(
        "UPDATE maintenance_schedule SET is_active = 0, updated_at = ? WHERE id = ?",
        (_now(), schedule_id),
    )
