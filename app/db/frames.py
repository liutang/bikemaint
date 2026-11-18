"""One clock for every stored time (specs/075, which replaced 015 FR-013 and 051).

Every instant is stored as UTC text in `STORED_FORMAT`: Strava rides, times the app records, and
times the rider types, which are read in the saved zone first (`to_utc`). Comparisons are plain
text comparisons. `register` adds the one SQL function queries still need (`part_ride_ok`),
on every connection opened by `connection.get_connection`.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

from app.models.sync_rules import ride_matches

# Every stored instant is UTC text in this one format, so plain text comparisons are in time order
# (specs/075 research §3).
STORED_FORMAT = "%Y-%m-%dT%H:%M:%S.%fZ"


def stored(moment: datetime) -> str:
    """A UTC moment as stored text, with a four-digit year on every platform (specs/076 FR-004).

    glibc's `strftime("%Y")` writes year 21 as `21`, which sorts after every real date.
    """
    return f"{moment.year:04d}-" + moment.strftime("%m-%dT%H:%M:%S.%fZ")


def to_utc(day: str, hhmm: str, zone: str) -> str:
    """A local date and minute in `zone` as stored UTC text (specs/075 FR-001).

    `fold=0` reads a nonexistent time with the offset before the change and a repeated time as
    the first one (specs/075 Edge Cases).
    """
    hour, minute = (int(part) for part in hhmm.split(":")[:2])
    local = datetime.combine(datetime.fromisoformat(day[:10]).date(), time(hour, minute), tzinfo=ZoneInfo(zone))
    return stored(local.astimezone(timezone.utc))


def from_utc(value: str, zone: str) -> datetime:
    """Stored UTC text as an aware moment in `zone`."""
    moment = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    return moment.astimezone(ZoneInfo(zone))


def end_of_day_utc(day: str, zone: str) -> str:
    """The last microsecond of a local day in `zone`, as stored UTC text (a whole-day maintenance entry)."""
    start = datetime.combine(datetime.fromisoformat(day[:10]).date(), time(0, 0), tzinfo=ZoneInfo(zone))
    next_day = datetime.combine(start.date() + timedelta(days=1), time(0, 0), tzinfo=ZoneInfo(zone))
    return stored(next_day.astimezone(timezone.utc) - timedelta(microseconds=1))


def register(conn: sqlite3.Connection) -> None:
    def part_ride_ok(component_id: int | None, user_modified, sport_type, ride_type, name) -> int:
        """1 unless the part's sync rule leaves this ride out (specs/060). Read per call, never stale."""
        row = conn.execute(
            "SELECT sports, ride_types, keywords FROM sync_rule WHERE component_id = ?", (component_id,)
        ).fetchone()
        if row is None or user_modified:  # edited rides are never left out
            return 1
        return 1 if ride_matches(row[0], row[1], row[2], sport_type, ride_type, name) else 0

    conn.create_function("part_ride_ok", 5, part_ride_ok)
