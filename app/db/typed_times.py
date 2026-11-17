"""The one-time conversion of typed times to UTC (specs/075 US3, research §8).

Before 075, times the rider typed (manual rides, install and removal moments, maintenance times,
and schedule starting points taken from them) were stored as typed, in the saved zone's wall
clock. This rewrites them as UTC instants. It runs once, as the data step `0019_typed_times_utc`
of `connection.run_migrations`, and again only for a format-1 backup being restored.

Recognising each stored form (the US3 table):
- manual rides are typed;
- an install or removal moment in whole minutes is typed; one with seconds was recorded "now";
- a schedule starting point is NULL, the 1970 "since tracking began" marker, the last moment of a
  day (from an untimed entry), whole minutes (typed), or anything else (recorded "now").
"""

from __future__ import annotations

import sqlite3
from datetime import datetime
from zoneinfo import ZoneInfo

from app.db import frames

TRACKING_BEGAN = "1970-01-01T00:00:00.000000Z"
_END_OF_DAY = "T23:59:59.999999Z"


def _parse(value: str) -> datetime | None:
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _typed(value: str, zone: str) -> str:
    """A typed wall-clock value (`YYYY-MM-DDTHH:MM...`) as UTC."""
    return frames.to_utc(value[:10], value[11:16], zone)


def _is_whole_minute(value: str) -> bool:
    moment = _parse(value)
    return moment is not None and moment.second == 0 and moment.microsecond == 0


def _period_moment(value: str | None, zone: str) -> str | None:
    if value is None or not _is_whole_minute(value):
        return value
    return _typed(value, zone)


def _starting_point(value: str | None, zone: str) -> str | None:
    if value is None or value == TRACKING_BEGAN or _parse(value) is None:
        return value
    if value.endswith(_END_OF_DAY):
        return frames.end_of_day_utc(value[:10], zone)
    if _is_whole_minute(value):
        return _typed(value, zone)
    return value


def convert(conn: sqlite3.Connection, zone: str) -> dict[str, int]:
    """Rewrite every typed time as UTC, reading it in `zone`; returns rows changed per table."""
    counts = {"ride_activity": 0, "component_installation_period": 0, "maintenance_log_entry": 0, "maintenance_schedule": 0}
    for ride_id, occurred_at in conn.execute(
        "SELECT id, occurred_at FROM ride_activity WHERE source = 'manual'"
    ).fetchall():
        if _parse(occurred_at) is None:
            continue
        conn.execute("UPDATE ride_activity SET occurred_at = ? WHERE id = ?", (_typed(occurred_at, zone), ride_id))
        counts["ride_activity"] += 1
    for period_id, installed_at, removed_at in conn.execute(
        "SELECT id, installed_at, removed_at FROM component_installation_period"
    ).fetchall():
        new = (_period_moment(installed_at, zone), _period_moment(removed_at, zone))
        if new != (installed_at, removed_at):
            conn.execute(
                "UPDATE component_installation_period SET installed_at = ?, removed_at = ? WHERE id = ?",
                (*new, period_id),
            )
            counts["component_installation_period"] += 1
    for entry_id, performed_at, performed_time in conn.execute(
        "SELECT id, performed_at, performed_time FROM maintenance_log_entry WHERE performed_instant IS NULL"
    ).fetchall():
        instant = (
            frames.to_utc(performed_at, performed_time, zone)
            if performed_time
            else frames.end_of_day_utc(performed_at, zone)
        )
        conn.execute("UPDATE maintenance_log_entry SET performed_instant = ? WHERE id = ?", (instant, entry_id))
        counts["maintenance_log_entry"] += 1
    for schedule_id, baseline_at in conn.execute("SELECT id, baseline_at FROM maintenance_schedule").fetchall():
        new = _starting_point(baseline_at, zone)
        if new != baseline_at:
            conn.execute("UPDATE maintenance_schedule SET baseline_at = ? WHERE id = ?", (new, schedule_id))
            counts["maintenance_schedule"] += 1
    return counts


def saved_zone(conn: sqlite3.Connection) -> str:
    """The account's zone, or UTC when none is saved or it is not a known zone."""
    row = conn.execute("SELECT timezone FROM account LIMIT 1").fetchone()
    name = row[0] if row and row[0] else "UTC"
    try:
        ZoneInfo(name)
    except Exception:
        return "UTC"
    return name


def has_rows(conn: sqlite3.Connection) -> bool:
    """Whether there is anything the conversion could change (else no copy is needed)."""
    return any(
        conn.execute(sql).fetchone()
        for sql in (
            "SELECT 1 FROM ride_activity WHERE source = 'manual' LIMIT 1",
            "SELECT 1 FROM component_installation_period LIMIT 1",
            "SELECT 1 FROM maintenance_log_entry LIMIT 1",
            "SELECT 1 FROM maintenance_schedule WHERE baseline_at IS NOT NULL LIMIT 1",
        )
    )


def convert_database(conn: sqlite3.Connection) -> dict[str, int]:
    """The data step: convert with the zone saved in the database itself."""
    return convert(conn, saved_zone(conn))
