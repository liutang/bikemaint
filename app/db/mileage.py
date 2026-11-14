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
    moving_time_seconds: int | None = None,
) -> RideActivity:
    """Insert a synced ride, or update it in place if already synced (idempotent on
    `strava_activity_id`) — a re-sync can correct a previously-synced ride's distance."""
    now = _now()
    conn.execute(
        """
        INSERT INTO ride_activity (
            strava_activity_id, strava_gear_id, bike_id, distance_miles, occurred_at,
            is_deleted_upstream, synced_at, moving_time_seconds
        ) VALUES (?, ?, ?, ?, ?, 0, ?, ?)
        ON CONFLICT(strava_activity_id) DO UPDATE SET
            strava_gear_id = excluded.strava_gear_id,
            bike_id = excluded.bike_id,
            distance_miles = excluded.distance_miles,
            occurred_at = excluded.occurred_at,
            is_deleted_upstream = 0,
            synced_at = excluded.synced_at,
            moving_time_seconds = COALESCE(excluded.moving_time_seconds, ride_activity.moving_time_seconds)
        WHERE ride_activity.user_modified = 0 AND ride_activity.deleted_by_user = 0
        """,
        (strava_activity_id, strava_gear_id, bike_id, distance_miles, occurred_at, now, moving_time_seconds),
    )
    row = conn.execute(
        "SELECT * FROM ride_activity WHERE strava_activity_id = ?", (strava_activity_id,)
    ).fetchone()
    return RideActivity.from_row(row)


def get_ride(conn: sqlite3.Connection, ride_id: int) -> RideActivity | None:
    row = conn.execute("SELECT * FROM ride_activity WHERE id = ?", (ride_id,)).fetchone()
    return RideActivity.from_row(row) if row else None


def create_manual_ride(
    conn: sqlite3.Connection,
    *,
    bike_id: int,
    distance_miles: float,
    occurred_at: str,
    note: str | None,
    moving_time_seconds: int | None = None,
) -> RideActivity:
    """A ride the rider added by hand (not tracked on Strava)."""
    cursor = conn.execute(
        """
        INSERT INTO ride_activity (source, bike_id, distance_miles, occurred_at, note, user_modified,
                                   moving_time_seconds)
        VALUES ('manual', ?, ?, ?, ?, 1, ?)
        """,
        (bike_id, distance_miles, occurred_at, note, moving_time_seconds),
    )
    ride = get_ride(conn, cursor.lastrowid)
    assert ride is not None
    return ride


def update_ride(
    conn: sqlite3.Connection,
    ride_id: int,
    *,
    bike_id: int,
    distance_miles: float,
    occurred_at: str,
    note: str | None,
    moving_time_seconds: int | None = None,
) -> RideActivity:
    """Edit a ride (miles, time, bike, note). Marks it so Strava sync never overwrites it."""
    conn.execute(
        """
        UPDATE ride_activity
        SET bike_id = ?, distance_miles = ?, occurred_at = ?, note = ?, moving_time_seconds = ?,
            user_modified = 1
        WHERE id = ?
        """,
        (bike_id, distance_miles, occurred_at, note, moving_time_seconds, ride_id),
    )
    ride = get_ride(conn, ride_id)
    assert ride is not None
    return ride


def delete_ride(conn: sqlite3.Connection, ride_id: int) -> None:
    """Remove a ride. A Strava ride is kept as a tombstone so the next sync cannot restore it."""
    ride = get_ride(conn, ride_id)
    if ride is None:
        return
    if ride.source == "manual":
        conn.execute("DELETE FROM ride_activity WHERE id = ?", (ride_id,))
    else:
        conn.execute(
            "UPDATE ride_activity SET deleted_by_user = 1, user_modified = 1 WHERE id = ?",
            (ride_id,),
        )


def list_rides_for_bike(conn: sqlite3.Connection, bike_id: int) -> list[RideActivity]:
    """A bike's live rides, oldest first (deleted ones are excluded)."""
    rows = conn.execute(
        """
        SELECT * FROM ride_activity
        WHERE bike_id = ? AND is_deleted_upstream = 0 AND deleted_by_user = 0
        ORDER BY occurred_at, id
        """,
        (bike_id,),
    ).fetchall()
    return [RideActivity.from_row(row) for row in rows]


def latest_ride_epoch(conn: sqlite3.Connection) -> int | None:
    """The Unix-epoch `occurred_at` of the most recently synced ride, or None if none yet.

    Used as the `after` cursor for an incremental sync (research.md §7) — there's no
    stored cursor column in data-model.md's `account` table, so it's derived instead.
    """
    row = conn.execute(
        "SELECT MAX(occurred_at) AS latest FROM ride_activity WHERE source = 'strava'"
    ).fetchone()
    if row is None or row["latest"] is None:
        return None
    dt = datetime.strptime(row["latest"], "%Y-%m-%dT%H:%M:%S.%fZ").replace(tzinfo=timezone.utc)
    return int(dt.timestamp())


def latest_synced_at(conn: sqlite3.Connection) -> str | None:
    """When a ride was most recently synced from Strava, or None if none has been yet."""
    row = conn.execute("SELECT MAX(synced_at) AS latest FROM ride_activity").fetchone()
    return None if row is None else row["latest"]


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
        WHERE bike_id = ? AND is_deleted_upstream = 0 AND deleted_by_user = 0
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
          AND ride_activity.deleted_by_user = 0
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


def list_rides_for_component(conn: sqlite3.Connection, component_id: int) -> list[RideActivity]:
    """Live rides that happened while `component_id` was installed on a bike (oldest first)."""
    rows = conn.execute(
        """
        SELECT DISTINCT ride_activity.*
        FROM component_installation_period AS period
        JOIN ride_activity
          ON ride_activity.bike_id = period.parent_bike_id
         AND ride_activity.occurred_at >= period.installed_at
         AND (period.removed_at IS NULL OR ride_activity.occurred_at < period.removed_at)
        WHERE period.component_id = ?
          AND ride_activity.is_deleted_upstream = 0
          AND ride_activity.deleted_by_user = 0
        ORDER BY ride_activity.occurred_at, ride_activity.id
        """,
        (component_id,),
    ).fetchall()
    return [RideActivity.from_row(row) for row in rows]


def list_adjustments(
    conn: sqlite3.Connection, *, bike_id: int | None = None, component_id: int | None = None
) -> list[MileageAdjustment]:
    """Manual mileage corrections for a bike or a component, oldest first."""
    if bike_id is not None:
        rows = conn.execute(
            "SELECT * FROM mileage_adjustment WHERE bike_id = ? ORDER BY created_at, id", (bike_id,)
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM mileage_adjustment WHERE component_id = ? ORDER BY created_at, id",
            (component_id,),
        ).fetchall()
    return [MileageAdjustment.from_row(row) for row in rows]


def component_ids_with_history_on(conn: sqlite3.Connection, bike_ids: set[int]) -> list[int]:
    """Live components that are, or ever were, installed on any of these bikes."""
    if not bike_ids:
        return []
    marks = ",".join("?" for _ in bike_ids)
    rows = conn.execute(
        f"""
        SELECT DISTINCT period.component_id AS id
        FROM component_installation_period AS period
        JOIN component ON component.id = period.component_id AND component.is_deleted = 0
        WHERE period.parent_bike_id IN ({marks})
        """,
        tuple(sorted(bike_ids)),
    ).fetchall()
    return [row["id"] for row in rows]


def recent_ride_stats_for_bike(conn: sqlite3.Connection, bike_id: int, *, since: str) -> tuple[float, int]:
    """(total miles, number of distinct ride days) for `bike_id` since the `since` timestamp.

    Feeds the trailing riding-pace estimate used for due-date projection (research.md §4).
    """
    row = conn.execute(
        """
        SELECT COALESCE(SUM(distance_miles), 0) AS miles,
               COUNT(DISTINCT substr(occurred_at, 1, 10)) AS ride_days
        FROM ride_activity
        WHERE bike_id = ? AND is_deleted_upstream = 0 AND deleted_by_user = 0 AND occurred_at >= ?
        """,
        (bike_id, since),
    ).fetchone()
    return row["miles"], row["ride_days"]


def bike_mileage_at(conn: sqlite3.Connection, bike_id: int, at: str) -> float:
    """A bike's mileage as of `at` (stored format): baseline, live rides up to then, adjustments.

    Adjustments carry no effective date, so all of them count (specs/038).
    """
    baseline = conn.execute(
        "SELECT manual_baseline_mileage FROM bike WHERE id = ?", (bike_id,)
    ).fetchone()
    if baseline is None:
        raise LookupError(f"No bike with id {bike_id}")
    rides = conn.execute(
        """
        SELECT COALESCE(SUM(distance_miles), 0) AS total FROM ride_activity
        WHERE bike_id = ? AND occurred_at <= ? AND is_deleted_upstream = 0 AND deleted_by_user = 0
        """,
        (bike_id, at),
    ).fetchone()["total"]
    adjustments = conn.execute(
        "SELECT COALESCE(SUM(delta_miles), 0) AS total FROM mileage_adjustment WHERE bike_id = ?",
        (bike_id,),
    ).fetchone()["total"]
    return baseline["manual_baseline_mileage"] + rides + adjustments


def component_mileage_at(conn: sqlite3.Connection, component_id: int, at: str) -> float:
    """A part's mileage as of `at`: baseline, rides during its installation periods up to then, adjustments."""
    baseline = conn.execute(
        "SELECT manual_baseline_mileage FROM component WHERE id = ?", (component_id,)
    ).fetchone()
    if baseline is None:
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
          AND ride_activity.occurred_at <= ?
          AND ride_activity.is_deleted_upstream = 0
          AND ride_activity.deleted_by_user = 0
        """,
        (component_id, at),
    ).fetchone()["total"]
    adjustments = conn.execute(
        "SELECT COALESCE(SUM(delta_miles), 0) AS total FROM mileage_adjustment WHERE component_id = ?",
        (component_id,),
    ).fetchone()["total"]
    return baseline["manual_baseline_mileage"] + rides + adjustments

