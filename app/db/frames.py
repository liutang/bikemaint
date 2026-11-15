"""One clock for comparing rides with install periods (specs/015 FR-013).

Strava rides are stored as UTC instants. Times the rider types are wall-clock times in the saved
zone, stored as typed (whole minutes). A time the app recorded itself ("now") carries seconds or
microseconds and is a UTC instant. These SQL functions turn either kind into saved-zone wall-clock
text so the two can be compared. Registered on every connection by `connection.get_connection`.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime
from zoneinfo import ZoneInfo

from app.models.sync_rules import ride_matches

_OUT = "%Y-%m-%dT%H:%M:%S"


def _zone_of(conn: sqlite3.Connection) -> ZoneInfo:
    try:
        row = conn.execute("SELECT timezone FROM account LIMIT 1").fetchone()
        return ZoneInfo(row[0]) if row and row[0] else ZoneInfo("UTC")
    except Exception:  # no account table yet (migrations), or an unknown zone name
        return ZoneInfo("UTC")


def _parse(value: str) -> datetime | None:
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def register(conn: sqlite3.Connection) -> None:
    cached: list[ZoneInfo] = []

    def zone_now() -> ZoneInfo:
        # Looked up on first use, not on connect, so a zone saved earlier on this connection counts.
        if not cached:
            cached.append(_zone_of(conn))
        return cached[0]

    def ride_wall(value: str | None, source: str | None) -> str | None:
        """A ride's start as wall-clock text: Strava rides are UTC, manual rides are as typed."""
        if value is None:
            return None
        moment = _parse(value)
        if moment is None:
            return value
        if source == "strava":
            return moment.astimezone(zone_now()).strftime(_OUT)
        return moment.replace(tzinfo=None).strftime(_OUT)

    def period_wall(value: str | None) -> str | None:
        """A period boundary as wall-clock text: typed whole minutes as typed, recorded instants converted."""
        if value is None:
            return None
        moment = _parse(value)
        if moment is None:
            return value
        if moment.second or moment.microsecond:
            return moment.astimezone(zone_now()).strftime(_OUT)
        return moment.replace(tzinfo=None).strftime(_OUT)

    def part_ride_ok(component_id: int | None, user_modified, sport_type, ride_type, name) -> int:
        """1 unless the part's sync rule leaves this ride out (specs/060). Read per call, never stale."""
        row = conn.execute(
            "SELECT sports, ride_types, keywords FROM sync_rule WHERE component_id = ?", (component_id,)
        ).fetchone()
        if row is None or user_modified:  # edited rides are never left out
            return 1
        return 1 if ride_matches(row[0], row[1], row[2], sport_type, ride_type, name) else 0

    conn.create_function("part_ride_ok", 5, part_ride_ok)
    conn.create_function("ride_wall", 2, ride_wall, deterministic=True)
    conn.create_function("period_wall", 1, period_wall, deterministic=True)
