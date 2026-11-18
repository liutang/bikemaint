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

import logging
import re
import sqlite3
from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo

from app.db import frames

logger = logging.getLogger(__name__)

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


# ------------------------------------------------ specs/076 US3: repair stored short years

# A stored value whose year has fewer than four digits, or four digits below 100 (`21-…`, `0021-…`).
_SHORT_INSTANT = re.compile(r"^(\d{1,4})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):(\d{2})(?:\.(\d{1,6}))?Z$")
_SHORT_DATE = re.compile(r"^(\d{1,4})-(\d{2})-(\d{2})$")

# (table, column, rows): the columns the rider types into (076 data-model.md). Strava rides are never touched.
_INSTANT_COLUMNS = (
    ("ride_activity", "occurred_at", "source = 'manual'"),
    ("component_installation_period", "installed_at", "1 = 1"),
    ("component_installation_period", "removed_at", "1 = 1"),
    ("maintenance_log_entry", "performed_instant", "1 = 1"),
    ("maintenance_schedule", "baseline_at", "1 = 1"),
)
_DATE_COLUMNS = (
    ("maintenance_log_entry", "performed_at"),
    ("maintenance_schedule", "baseline_date"),
)


class _Unrepairable(ValueError):
    pass


def _is_short(match: re.Match | None) -> bool:
    return match is not None and int(match.group(1)) < 100


def _repair_instant(value: str, zone: str) -> str:
    """Read the value back as the local moment it was typed as, make the year 20yy, store it again (FR-008)."""
    parts = _SHORT_INSTANT.match(value)
    year, month, day, hour, minute, second = (int(g) for g in parts.groups()[:6])
    micro = int((parts.group(7) or "0").ljust(6, "0"))
    try:
        utc = datetime(year, month, day, hour, minute, second, micro, tzinfo=timezone.utc)
        local = utc.astimezone(ZoneInfo(zone))
        typed = local.replace(year=local.year + 2000, tzinfo=None)
    except (ValueError, OverflowError) as exc:
        raise _Unrepairable(str(exc)) from exc
    return frames.stored(typed.replace(tzinfo=ZoneInfo(zone)).astimezone(timezone.utc))


def _repair_date(value: str) -> str:
    year, month, day = (int(g) for g in _SHORT_DATE.match(value).groups())
    try:
        return date(year + 2000, month, day).isoformat()
    except ValueError as exc:
        raise _Unrepairable(str(exc)) from exc


def repair_short_years(conn: sqlite3.Connection, zone: str) -> dict[str, int]:
    """Rewrite every stored year below 100 as 20yy, as if it had been typed that way (specs/076 US3).

    Returns the values changed per table. A value that can't be repaired is left as it is and
    logged as a warning with its table and id (FR-010).
    """
    counts = {"ride_activity": 0, "component_installation_period": 0, "maintenance_log_entry": 0, "maintenance_schedule": 0}

    def fix(table, column, row_id, value, repair):
        try:
            new = repair(value)
        except _Unrepairable:
            logger.warning("short year left unrepaired table=%s column=%s id=%s", table, column, row_id)
            return
        conn.execute(f"UPDATE {table} SET {column} = ? WHERE id = ?", (new, row_id))
        counts[table] += 1

    for table, column, rows in _INSTANT_COLUMNS:
        for row_id, value in conn.execute(f"SELECT id, {column} FROM {table} WHERE {rows} AND {column} IS NOT NULL").fetchall():
            if _is_short(_SHORT_INSTANT.match(value)):
                fix(table, column, row_id, value, lambda v: _repair_instant(v, zone))
    for table, column in _DATE_COLUMNS:
        for row_id, value in conn.execute(f"SELECT id, {column} FROM {table} WHERE {column} IS NOT NULL").fetchall():
            if _is_short(_SHORT_DATE.match(value)):
                fix(table, column, row_id, value, _repair_date)
    return counts


def repair_database(conn: sqlite3.Connection) -> dict[str, int]:
    """The data step `0020_four_digit_years`: repair with the zone saved in the database itself."""
    return repair_short_years(conn, saved_zone(conn))
