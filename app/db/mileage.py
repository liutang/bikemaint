"""Parameterized query functions for `ride_activity` and `mileage_adjustment`."""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone

from app.models.rows import MileageAdjustment, RideActivity


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def upsert_ride_activity(
    conn: sqlite3.Connection,
    *,
    strava_activity_id: int,
    strava_gear_id: str | None,
    bike_id: int | None,
    distance_miles: float,
    occurred_at: str,
) -> RideActivity:
    """Insert a synced ride, or update it in place if already synced (idempotent on
    `strava_activity_id`) — a re-sync can correct a previously-synced ride's distance."""
    now = _now()
    conn.execute(
        """
        INSERT INTO ride_activity (
            strava_activity_id, strava_gear_id, bike_id, distance_miles, occurred_at,
            is_deleted_upstream, synced_at
        ) VALUES (?, ?, ?, ?, ?, 0, ?)
        ON CONFLICT(strava_activity_id) DO UPDATE SET
            strava_gear_id = excluded.strava_gear_id,
            bike_id = excluded.bike_id,
            distance_miles = excluded.distance_miles,
            occurred_at = excluded.occurred_at,
            is_deleted_upstream = 0,
            synced_at = excluded.synced_at
        """,
        (strava_activity_id, strava_gear_id, bike_id, distance_miles, occurred_at, now),
    )
    row = conn.execute(
        "SELECT * FROM ride_activity WHERE strava_activity_id = ?", (strava_activity_id,)
    ).fetchone()
    return RideActivity.from_row(row)


def latest_ride_epoch(conn: sqlite3.Connection) -> int | None:
    """The Unix-epoch `occurred_at` of the most recently synced ride, or None if none yet.

    Used as the `after` cursor for an incremental sync (research.md §7) — there's no
    stored cursor column in data-model.md's `account` table, so it's derived instead.
    """
    row = conn.execute("SELECT MAX(occurred_at) AS latest FROM ride_activity").fetchone()
    if row is None or row["latest"] is None:
        return None
    dt = datetime.strptime(row["latest"], "%Y-%m-%dT%H:%M:%S.%fZ").replace(tzinfo=timezone.utc)
    return int(dt.timestamp())


def insert_mileage_adjustment(
    conn: sqlite3.Connection,
    *,
    bike_id: int | None,
    component_id: int | None,
    delta_miles: float,
    reason: str | None,
) -> MileageAdjustment:
    now = _now()
    cursor = conn.execute(
        """
        INSERT INTO mileage_adjustment (bike_id, component_id, delta_miles, reason, created_at)
        VALUES (?, ?, ?, ?, ?)
        """,
        (bike_id, component_id, delta_miles, reason, now),
    )
    row = conn.execute(
        "SELECT * FROM mileage_adjustment WHERE id = ?", (cursor.lastrowid,)
    ).fetchone()
    return MileageAdjustment.from_row(row)


def recompute_bike_total_mileage(conn: sqlite3.Connection, bike_id: int) -> float:
    """Recompute and persist `bike.total_mileage` = baseline + attributed rides + adjustments."""
    baseline_row = conn.execute(
        "SELECT manual_baseline_mileage FROM bike WHERE id = ?", (bike_id,)
    ).fetchone()
    if baseline_row is None:
        raise LookupError(f"No bike with id {bike_id}")
    rides = conn.execute(
        """
        SELECT COALESCE(SUM(distance_miles), 0) AS total FROM ride_activity
        WHERE bike_id = ? AND is_deleted_upstream = 0
        """,
        (bike_id,),
    ).fetchone()["total"]
    adjustments = conn.execute(
        "SELECT COALESCE(SUM(delta_miles), 0) AS total FROM mileage_adjustment WHERE bike_id = ?",
        (bike_id,),
    ).fetchone()["total"]
    total = baseline_row["manual_baseline_mileage"] + rides + adjustments
    conn.execute(
        "UPDATE bike SET total_mileage = ?, updated_at = ? WHERE id = ?",
        (total, _now(), bike_id),
    )
    return total


def recompute_component_total_mileage(conn: sqlite3.Connection, component_id: int) -> float:
    """Recompute and persist `component.total_mileage` = baseline + attributed rides
    (summed across every installation period, per FR-008) + adjustments."""
    baseline_row = conn.execute(
        "SELECT manual_baseline_mileage FROM component WHERE id = ?", (component_id,)
    ).fetchone()
    if baseline_row is None:
        raise LookupError(f"No component with id {component_id}")
    rides = conn.execute(
        """
        SELECT COALESCE(SUM(ride_activity.distance_miles), 0) AS total
        FROM component_installation_period
        JOIN ride_activity
          ON ride_activity.bike_id = component_installation_period.parent_bike_id
         AND ride_activity.occurred_at >= component_installation_period.installed_at
         AND (component_installation_period.removed_at IS NULL
              OR ride_activity.occurred_at < component_installation_period.removed_at)
        WHERE component_installation_period.component_id = ?
          AND ride_activity.is_deleted_upstream = 0
        """,
        (component_id,),
    ).fetchone()["total"]
    adjustments = conn.execute(
        "SELECT COALESCE(SUM(delta_miles), 0) AS total FROM mileage_adjustment WHERE component_id = ?",
        (component_id,),
    ).fetchone()["total"]
    total = baseline_row["manual_baseline_mileage"] + rides + adjustments
    conn.execute(
        "UPDATE component SET total_mileage = ?, updated_at = ? WHERE id = ?",
        (total, _now(), component_id),
    )
    return total


def recent_ride_stats_for_bike(conn: sqlite3.Connection, bike_id: int, *, since: str) -> tuple[float, int]:
    """(total miles, number of distinct ride days) for `bike_id` since the `since` timestamp.

    Feeds the trailing riding-pace estimate used for due-date projection (research.md §4).
    """
    row = conn.execute(
        """
        SELECT COALESCE(SUM(distance_miles), 0) AS miles,
               COUNT(DISTINCT substr(occurred_at, 1, 10)) AS ride_days
        FROM ride_activity
        WHERE bike_id = ? AND is_deleted_upstream = 0 AND occurred_at >= ?
        """,
        (bike_id, since),
    ).fetchone()
    return row["miles"], row["ride_days"]
