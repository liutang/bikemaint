"""Parameterized query functions for the bike table."""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone

from app.models.rows import Bike


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def create(
    conn: sqlite3.Connection,
    *,
    name: str,
    bike_type: str | None = None,
    manual_baseline_mileage: float = 0.0,
) -> Bike:
    now = _now()
    cursor = conn.execute(
        """
        INSERT INTO bike (
            name, bike_type, manual_baseline_mileage, total_mileage, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?)
        """,
        (name, bike_type, manual_baseline_mileage, manual_baseline_mileage, now, now),
    )
    bike = get_by_id(conn, cursor.lastrowid)
    assert bike is not None
    return bike


def get_by_id(conn: sqlite3.Connection, bike_id: int) -> Bike | None:
    row = conn.execute(
        "SELECT * FROM bike WHERE id = ? AND is_deleted = 0", (bike_id,)
    ).fetchone()
    return Bike.from_row(row) if row else None


def list_active(conn: sqlite3.Connection) -> list[Bike]:
    rows = conn.execute("SELECT * FROM bike WHERE is_deleted = 0 ORDER BY id").fetchall()
    return [Bike.from_row(row) for row in rows]


def get_by_strava_gear_id(conn: sqlite3.Connection, strava_gear_id: str) -> Bike | None:
    row = conn.execute(
        "SELECT * FROM bike WHERE strava_gear_id = ? AND is_deleted = 0", (strava_gear_id,)
    ).fetchone()
    return Bike.from_row(row) if row else None


def set_strava_pairing(
    conn: sqlite3.Connection, bike_id: int, *, strava_gear_id: str, strava_paired_at: str
) -> Bike:
    conn.execute(
        """
        UPDATE bike
        SET strava_gear_id = ?, strava_paired_at = ?, updated_at = ?
        WHERE id = ?
        """,
        (strava_gear_id, strava_paired_at, _now(), bike_id),
    )
    bike = get_by_id(conn, bike_id)
    assert bike is not None
    return bike


def update(
    conn: sqlite3.Connection,
    bike_id: int,
    *,
    name: str,
    bike_type: str | None,
    manual_baseline_mileage: float,
    total_mileage: float,
) -> Bike:
    conn.execute(
        """
        UPDATE bike
        SET name = ?, bike_type = ?, manual_baseline_mileage = ?, total_mileage = ?, updated_at = ?
        WHERE id = ?
        """,
        (name, bike_type, manual_baseline_mileage, total_mileage, _now(), bike_id),
    )
    bike = get_by_id(conn, bike_id)
    assert bike is not None
    return bike


def soft_delete(conn: sqlite3.Connection, bike_id: int) -> None:
    conn.execute(
        "UPDATE bike SET is_deleted = 1, updated_at = ? WHERE id = ?", (_now(), bike_id)
    )
