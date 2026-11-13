"""The rider's time zone, for display (specs/023-settings-sync-and-timezone).

Times the app records in UTC (Strava rides, completed-task times, connected-since) are shown in
the zone saved in Settings. Display only: no stored time is converted, and typed times are shown
as typed. Callable without FastAPI or request objects.
"""

from __future__ import annotations

import os
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from app.db import accounts as accounts_db
from app.db.connection import get_connection

_STORED_FORMAT = "%Y-%m-%dT%H:%M:%S.%fZ"

# Zone name per database file, so a lookup is not a query every time a time is rendered.
_cache: dict[str, str] = {}


def _key() -> str:
    return os.environ.get("DATABASE_PATH", "")


def zone_name() -> str:
    """The saved zone name (`UTC` until the rider chooses one)."""
    key = _key()
    if key not in _cache:
        try:
            with get_connection() as conn:
                account = accounts_db.get_singleton(conn)
        except Exception:
            return "UTC"
        _cache[key] = account.timezone if account is not None else "UTC"
    return _cache[key]


def remember_zone(name: str) -> None:
    """Called when the rider saves a zone, so the next page already uses it."""
    _cache[_key()] = name


def _zone() -> ZoneInfo:
    try:
        return ZoneInfo(zone_name())
    except Exception:
        return ZoneInfo("UTC")


def format_utc(value: str | None) -> str:
    """A stored UTC time as `YYYY-MM-DD HH:MM ABBR` in the saved zone; other text is returned as is."""
    if not value:
        return ""
    try:
        moment = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return value
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    local = moment.astimezone(_zone())
    return f"{local:%Y-%m-%d %H:%M} {local:%Z}"


def now_in_zone_moment() -> str:
    """The current wall-clock time in the saved zone, in the stored text format.

    For comparing with times the rider typed, which are wall-clock times (never for values that
    are stored, which stay in UTC).
    """
    return datetime.now(_zone()).replace(tzinfo=None).strftime(_STORED_FORMAT)
